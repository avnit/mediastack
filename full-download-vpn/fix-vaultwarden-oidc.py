# Configure the Vaultwarden (vault1) OIDC provider in Authentik. Idempotent - safe to re-run.
#
# Run with:
#   docker cp /root/.vaultwarden-oidc-secret authentik-worker:/tmp/vaultwarden-secret
#   docker exec -u 0 authentik-worker chmod 644 /tmp/vaultwarden-secret
#   docker exec -i authentik-worker ak shell < fix-vaultwarden-oidc.py
#   docker exec -u 0 authentik-worker rm -f /tmp/vaultwarden-secret
#
# Vaultwarden runs on unraid (.95:4743), not in this stack. It is given NATIVE
# SSO (its "Use single sign-on" button) rather than traefik forward-auth, because
# the browser extension, the desktop app and the mobile app send a Vaultwarden
# bearer token and never hold an Authentik cookie, so forward-auth 302'd every
# /api and /identity call. The same client secret goes into the unraid container
# as SSO_CLIENT_SECRET; the rest of the container settings are in README.md.
#
# SSO replaces only the LOGIN step. The master password is still asked for,
# because it is what decrypts the vault; Vaultwarden has no way around that.
#
# Six fields, each of which silently breaks login when missing:
#
#   1. signing_key      - without it authentik signs id_tokens HS256 and serves an
#                         EMPTY JWKS -> "Failed to discover OpenID provider".
#   2. grant_types      - defaults to [] -> "Invalid grant_type for provider".
#   3. redirect_uris    - Vaultwarden calls back on /identity/connect/oidc-signin,
#                         built from its DOMAIN, which therefore must be https.
#   4. email_verified   - authentik's stock email scope returns email_verified
#                         False since 2025.10, and Vaultwarden refuses the first
#                         login ("Email is not verified by the SSO provider"). A
#                         dedicated mapping reports True: the addresses here are
#                         set by the Authentik admin, not self-registered.
#   5. offline_access   - no refresh token without it, so the session dies when
#                         the access token does.
#   6. access validity  - Bitwarden clients refresh 5 minutes before expiry, so a
#                         5 minute access token would refresh in a loop.
import os

from authentik.core.models import Application
from authentik.crypto.models import CertificateKeyPair
from authentik.flows.models import Flow
from authentik.providers.oauth2.models import (
    GrantTypes, OAuth2Provider, RedirectURI, RedirectURIMatchingMode,
    RedirectURIType, ScopeMapping,
)

SECRET_PATH = os.environ.get("VAULTWARDEN_OIDC_SECRET", "/tmp/vaultwarden-secret")
HOST = "https://vault1.asbblog.com"
APP_SLUG = "vault1"   # the existing launcher tile; issuer path /application/o/vault1/

secret = open(SECRET_PATH).read().strip()
assert secret, f"empty client secret at {SECRET_PATH}"

email_scope, _ = ScopeMapping.objects.update_or_create(                          # (4)
    name="vaultwarden: email (verified)",
    defaults=dict(
        scope_name="email",
        description="Email address, reported as verified for Vaultwarden",
        expression='return {\n    "email": request.user.email,\n    "email_verified": True,\n}',
    ),
)

provider, created = OAuth2Provider.objects.update_or_create(
    name="vaultwarden",
    defaults=dict(
        client_id="vaultwarden",
        client_secret=secret,
        client_type="confidential",
        sub_mode="hashed_user_id",
        include_claims_in_id_token=True,
        access_token_validity="hours=1",                                         # (6)
        refresh_token_validity="days=30",
        encryption_key=None,   # an encrypted id_token (JWE) fails "found 5 parts"
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
    RedirectURI(RedirectURIMatchingMode.STRICT, f"{HOST}/identity/connect/oidc-signin",
                RedirectURIType.AUTHORIZATION),
]
stock = ScopeMapping.objects.filter(managed__in=[
    "goauthentik.io/providers/oauth2/scope-openid",
    "goauthentik.io/providers/oauth2/scope-profile",
    "goauthentik.io/providers/oauth2/scope-offline_access",                      # (5)
])
assert stock.count() == 3, "stock openid/profile/offline_access scope mappings missing"
provider.property_mappings.set([*stock, email_scope])
provider.save()
provider.refresh_from_db()

print(f"PROVIDER   : {provider.name} ({'created' if created else 'updated'}) "
      f"signing_key={provider.signing_key.name} grants={provider.grant_types}")
for r in provider.redirect_uris:
    print(f"REDIRECT   : {r.matching_mode.value}  {r.url}")
# property_mappings yields base PropertyMapping rows, which have no scope_name.
scopes = ScopeMapping.objects.filter(
    pk__in=provider.property_mappings.values_list("pk", flat=True))
print(f"SCOPES     : {sorted(scopes.values_list('scope_name', flat=True))}")

# The "Vault" tile already exists (set-authentik-icons.py gives it its icon), so
# only the provider is attached; name, group and icon are left as they are.
app, created = Application.objects.get_or_create(
    slug=APP_SLUG,
    defaults=dict(name="Vault", group="Security", meta_launch_url=HOST,
                  policy_engine_mode="any"),
)
app.provider = provider
app.save()
print(f"APPLICATION: {app.slug} ({'created' if created else 'provider attached'})")

assert provider.signing_key, "no signing key -> empty JWKS -> token verification fails"
assert not provider.encryption_key, "encryption key set -> JWE -> Vaultwarden cannot parse the token"
assert "authorization_code" in [str(g) for g in provider.grant_types]
assert len(provider.redirect_uris) == 1
assert provider.property_mappings.count() == 4, "openid+email+profile+offline_access required"
print(f"OK         : SSO_AUTHORITY=https://auth.asbblog.com/application/o/{app.slug}/")
print(f"OK         : SSO_CLIENT_ID={provider.client_id}")
