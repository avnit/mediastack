# Configure the Homarr (192.168.0.21:7575 / homepage.asbblog.com) OIDC provider
# in Authentik. Idempotent - safe to re-run. Same pattern as fix-openwebui-oidc.py.
#
# Run with:
#   docker cp /root/.homarr-oidc-secret authentik-worker:/tmp/homarr-secret
#   docker exec -u 0 authentik-worker chmod 644 /tmp/homarr-secret
#   docker exec -i authentik-worker ak shell < fix-homarr-oidc.py
#   docker exec -u 0 authentik-worker rm -f /tmp/homarr-secret
#
# The same client secret goes into the homarr container on 192.168.0.21 as
# AUTH_OIDC_CLIENT_SECRET (see ~ubuntu/homarr.env there).
# Homarr calls back on /api/auth/callback/oidc. Groups reach Homarr through the
# "groups" claim that authentik puts in the profile scope.
import os

from authentik.core.models import Application
from authentik.crypto.models import CertificateKeyPair
from authentik.flows.models import Flow
from authentik.providers.oauth2.models import (
    GrantTypes, OAuth2Provider, RedirectURI, RedirectURIMatchingMode,
    RedirectURIType, ScopeMapping,
)

SECRET_PATH = os.environ.get("HOMARR_OIDC_SECRET", "/tmp/homarr-secret")
HOSTS = ["http://192.168.0.21:7575", "https://homepage.asbblog.com", "https://homarr3.asbblog.com"]
APP_SLUG = "homarr"   # issuer path: /application/o/homarr/

secret = open(SECRET_PATH).read().strip()
assert secret, f"empty client secret at {SECRET_PATH}"

provider, created = OAuth2Provider.objects.update_or_create(
    name="homarr",
    defaults=dict(
        client_id="homarr",
        client_secret=secret,
        client_type="confidential",
        sub_mode="hashed_user_id",
        include_claims_in_id_token=True,
        grant_types=[GrantTypes.AUTHORIZATION_CODE, GrantTypes.REFRESH_TOKEN],
        signing_key=CertificateKeyPair.objects.get(
            name="authentik Self-signed Certificate"),
        authorization_flow=Flow.objects.get(
            slug="default-provider-authorization-implicit-consent"),
        authentication_flow=Flow.objects.get(slug="default-authentication-flow"),
        invalidation_flow=Flow.objects.get(slug="default-provider-invalidation-flow"),
    ),
)
provider.redirect_uris = [
    RedirectURI(RedirectURIMatchingMode.STRICT, f"{h}/api/auth/callback/oidc",
                RedirectURIType.AUTHORIZATION)
    for h in HOSTS
]
provider.property_mappings.set(ScopeMapping.objects.filter(managed__in=[
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

# blank://blank hides the tile: the existing "homepage" application is the tile.
app, created = Application.objects.update_or_create(
    slug=APP_SLUG,
    defaults=dict(name="Homarr (OIDC login)", provider=provider, group="Dashboards",
                  meta_launch_url="blank://blank", policy_engine_mode="any"),
)
print(f"APPLICATION: {app.slug} ({'created' if created else 'updated'})")

assert provider.signing_key, "no signing key -> empty JWKS -> token verification fails"
assert "authorization_code" in [str(g) for g in provider.grant_types]
assert len(provider.redirect_uris) == len(HOSTS)
assert provider.property_mappings.count() == 3, "openid+email+profile scopes required"
print(f"OK         : issuer https://auth.asbblog.com/application/o/{app.slug}/")
