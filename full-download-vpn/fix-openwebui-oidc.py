# Configure the Open WebUI OIDC provider in Authentik. Idempotent - safe to re-run.
#
# Run with:
#   docker cp /root/.openwebui-oidc-secret authentik-worker:/tmp/openwebui-secret
#   docker exec -u 0 authentik-worker chmod 644 /tmp/openwebui-secret
#   docker exec -i authentik-worker ak shell < fix-openwebui-oidc.py
#   docker exec -u 0 authentik-worker rm -f /tmp/openwebui-secret
#
# Open WebUI is given NATIVE OIDC rather than being put behind traefik
# forward-auth, because its API clients (bearer-token callers, the OpenAI-
# compatible endpoint) and its websocket never hold an Authentik cookie. Edge
# auth broke them the same way it broke the Immich app and the Proxmox pollers.
# The same client secret goes into .env as OPENWEBUI_OIDC_SECRET; the open-webui
# service reads it as OAUTH_CLIENT_SECRET.
#
# Same four fields as fix-immich-oidc.py, each of which silently breaks login
# when missing:
#
#   1. signing_key      - without it authentik signs id_tokens HS256 and serves an
#                         EMPTY JWKS, so the client cannot verify the token.
#   2. grant_types      - defaults to [] -> "Invalid grant_type for provider".
#   3. redirect_uris    - Open WebUI calls back on /oauth/oidc/callback, and
#                         RedirectURI requires redirect_uri_type on 2026.x.
#   4. property_mappings- without email+profile the provider advertises only
#                         "openid" and Open WebUI has no email to merge on
#                         (OAUTH_MERGE_ACCOUNTS_BY_EMAIL).
import os

from authentik.core.models import Application
from authentik.crypto.models import CertificateKeyPair
from authentik.flows.models import Flow
from authentik.providers.oauth2.models import (
    GrantTypes, OAuth2Provider, RedirectURI, RedirectURIMatchingMode,
    RedirectURIType, ScopeMapping,
)

SECRET_PATH = os.environ.get("OPENWEBUI_OIDC_SECRET", "/tmp/openwebui-secret")
HOST = "https://openwebui.asbblog.com"
APP_SLUG = "openwebui"   # issuer path: /application/o/openwebui/ -> OPENID_PROVIDER_URL

secret = open(SECRET_PATH).read().strip()
assert secret, f"empty client secret at {SECRET_PATH}"

provider, created = OAuth2Provider.objects.update_or_create(
    name="open-webui",
    defaults=dict(
        client_id="open-webui",
        client_secret=secret,
        client_type="confidential",
        sub_mode="hashed_user_id",
        include_claims_in_id_token=True,
        grant_types=[GrantTypes.AUTHORIZATION_CODE, GrantTypes.REFRESH_TOKEN],   # (2)
        signing_key=CertificateKeyPair.objects.get(                              # (1)
            name="authentik Self-signed Certificate"),
        authorization_flow=Flow.objects.get(
            slug="default-provider-authorization-implicit-consent"),
        authentication_flow=Flow.objects.get(slug="default-authentication-flow"),
        invalidation_flow=Flow.objects.get(slug="default-provider-invalidation-flow"),
    ),
)
provider.redirect_uris = [                                                       # (3)
    RedirectURI(RedirectURIMatchingMode.STRICT, f"{HOST}/oauth/oidc/callback",
                RedirectURIType.AUTHORIZATION),
]
provider.property_mappings.set(ScopeMapping.objects.filter(managed__in=[         # (4)
    "goauthentik.io/providers/oauth2/scope-openid",
    "goauthentik.io/providers/oauth2/scope-email",
    "goauthentik.io/providers/oauth2/scope-profile",
]))
provider.save()
provider.refresh_from_db()

print(f"PROVIDER   : {provider.name} ({'created' if created else 'updated'}) "
      f"signing_key={provider.signing_key.name} grants={provider.grant_types}")
for r in provider.redirect_uris:
    print(f"REDIRECT   : {r.matching_mode.value}  {r.url}")

app, created = Application.objects.update_or_create(
    slug=APP_SLUG,
    defaults=dict(name="Open WebUI", provider=provider, group="AI",
                  meta_launch_url=HOST, policy_engine_mode="any"),
)
print(f"APPLICATION: {app.slug} ({'created' if created else 'updated'})")

assert provider.signing_key, "no signing key -> empty JWKS -> token verification fails"
assert "authorization_code" in [str(g) for g in provider.grant_types]
assert len(provider.redirect_uris) == 1
assert provider.property_mappings.count() == 3, "openid+email+profile scopes required"
print(f"OK         : issuer https://auth.asbblog.com/application/o/{app.slug}/")
print(f"OK         : OPENID_PROVIDER_URL=https://auth.asbblog.com/application/o/{app.slug}/.well-known/openid-configuration")
