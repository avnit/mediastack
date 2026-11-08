# Configure the Immich OIDC provider in Authentik. Idempotent - safe to re-run.
#
# Run with:
#   docker cp /root/.immich-oidc-secret authentik-worker:/tmp/immich-secret
#   docker exec -i authentik-worker ak shell < fix-immich-oidc.py
#   docker exec -u 0 authentik-worker rm -f /tmp/immich-secret
#
# Immich is given NATIVE OIDC rather than being put behind traefik forward-auth
# or Cloudflare Access, because the Immich mobile app can complete an OAuth login
# but cannot complete an interactive browser login. Edge auth breaks phones, the
# same way it broke jellyfin clients and the Proxmox API pollers.
#
# Four fields matter here. Each was missed at some point and each broke login in a
# different way, with everything upstream still looking healthy:
#
#   1. signing_key      - without it authentik signs id_tokens HS256 and serves an
#                         EMPTY JWKS. Immich fetches 0 keys, cannot verify the
#                         token, and reports "Failed to finish oauth" - AFTER a
#                         successful authorize and a 200 token exchange.
#   2. grant_types      - defaults to [] -> "Invalid grant_type for provider".
#   3. redirect_uris    - needs all three, including the MOBILE scheme, and
#                         RedirectURI requires redirect_uri_type on 2026.x.
#   4. property_mappings- without email+profile the provider advertises only
#                         "openid" and Immich has no email to match a user on.
import os

from authentik.core.models import Application
from authentik.crypto.models import CertificateKeyPair
from authentik.flows.models import Flow
from authentik.providers.oauth2.models import (
    GrantTypes, OAuth2Provider, RedirectURI, RedirectURIMatchingMode,
    RedirectURIType, ScopeMapping,
)

SECRET_PATH = os.environ.get("IMMICH_OIDC_SECRET", "/tmp/immich-secret")
HOST = "https://immich.asbblog.com"

secret = open(SECRET_PATH).read().strip()
assert secret, f"empty client secret at {SECRET_PATH}"

provider, created = OAuth2Provider.objects.update_or_create(
    name="immich",
    defaults=dict(
        client_id="immich",
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
    RedirectURI(RedirectURIMatchingMode.STRICT, f"{HOST}/auth/login",
                RedirectURIType.AUTHORIZATION),
    RedirectURI(RedirectURIMatchingMode.STRICT, f"{HOST}/user-settings",
                RedirectURIType.AUTHORIZATION),
    RedirectURI(RedirectURIMatchingMode.STRICT, "app.immich:///oauth-callback",
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
    slug="immich",
    defaults=dict(name="Immich", provider=provider, group="Storage",
                  meta_launch_url=HOST, policy_engine_mode="any"),
)
print(f"APPLICATION: {app.slug} ({'created' if created else 'updated'})")

assert provider.signing_key, "no signing key -> empty JWKS -> 'Failed to finish oauth'"
assert "authorization_code" in [str(g) for g in provider.grant_types]
assert len(provider.redirect_uris) == 3, "mobile callback missing breaks the phone app"
print(f"OK         : issuer https://auth.asbblog.com/application/o/{app.slug}/")
