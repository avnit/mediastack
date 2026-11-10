# Configure the Synology DSM (nas) OIDC provider in Authentik. Idempotent - safe to re-run.
#
# Run with:
#   docker cp /root/.nas-oidc-secret authentik-worker:/tmp/nas-secret
#   docker exec -u 0 authentik-worker chmod 644 /tmp/nas-secret
#   docker exec -i authentik-worker ak shell < fix-nas-oidc.py
#   docker exec -u 0 authentik-worker rm -f /tmp/nas-secret
#
# The NAS is a Synology at 192.168.0.87 (DSM on https 5001), not in this stack.
# This gives DSM NATIVE single sign-on: its login page gets an "authentik" button
# (Control Panel > Domain/LDAP > SSO Client). The same client secret is typed
# into DSM as the "Application Key"; the DSM fields are listed in README.md.
#
# DSM never creates accounts from an OIDC login. The preferred_username claim
# must equal the name of an account that already exists in DSM. When the two
# differ, set the attribute `synology_username` on the Authentik user; the
# profile mapping below returns it in place of the Authentik username.
#
# Four fields, each of which breaks the login when wrong:
#
#   1. signing_key   - must be an RSA key. Without one authentik signs HS256 and
#                      serves an empty JWKS; DSM also rejects ECDSA id_tokens.
#                      Either way DSM says "Your SSO is not properly configured".
#   2. grant_types   - defaults to [] -> "Invalid grant_type for provider".
#   3. redirect_uris - exactly ONE entry, the bare origin with no path and no
#                      "#/signin". DSM uses only the last entry it is given and
#                      answers "not privilege" on a mismatch.
#   4. profile scope - carries preferred_username, the claim DSM matches on.
import os

from authentik.core.models import Application
from authentik.crypto.models import CertificateKeyPair
from authentik.flows.models import Flow
from authentik.providers.oauth2.models import (
    GrantTypes, OAuth2Provider, RedirectURI, RedirectURIMatchingMode,
    RedirectURIType, ScopeMapping,
)

SECRET_PATH = os.environ.get("NAS_OIDC_SECRET", "/tmp/nas-secret")
HOST = "https://nas.asbblog.com"
APP_SLUG = "nas"   # the existing launcher tile; issuer path /application/o/nas/

secret = open(SECRET_PATH).read().strip()
assert secret, f"empty client secret at {SECRET_PATH}"

profile_scope, _ = ScopeMapping.objects.update_or_create(                        # (4)
    name="synology: profile (DSM username)",
    defaults=dict(
        scope_name="profile",
        description="Profile with preferred_username taken from the "
                    "synology_username attribute when it is set",
        expression=(
            'return {\n'
            '    "name": request.user.name,\n'
            '    "preferred_username": request.user.attributes.get(\n'
            '        "synology_username", request.user.username),\n'
            '}'
        ),
    ),
)

provider, created = OAuth2Provider.objects.update_or_create(
    name="synology-dsm",
    defaults=dict(
        client_id="synology-dsm",
        client_secret=secret,
        client_type="confidential",
        sub_mode="hashed_user_id",
        include_claims_in_id_token=True,
        encryption_key=None,   # DSM cannot read an encrypted id_token (JWE)
        grant_types=[GrantTypes.AUTHORIZATION_CODE],                             # (2)
        signing_key=CertificateKeyPair.objects.get(                              # (1)
            name="authentik Self-signed Certificate"),
        authorization_flow=Flow.objects.get(
            slug="default-provider-authorization-implicit-consent"),
        authentication_flow=Flow.objects.get(slug="default-authentication-flow"),
        invalidation_flow=Flow.objects.get(slug="default-provider-invalidation-flow"),
    ),
)
provider.redirect_uris = [                                                       # (3)
    RedirectURI(RedirectURIMatchingMode.STRICT, HOST, RedirectURIType.AUTHORIZATION),
]
stock = ScopeMapping.objects.filter(managed__in=[
    "goauthentik.io/providers/oauth2/scope-openid",
    "goauthentik.io/providers/oauth2/scope-email",
])
assert stock.count() == 2, "stock openid/email scope mappings missing"
provider.property_mappings.set([*stock, profile_scope])
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

# The "NAS (Synology)" tile already exists (set-authentik-icons.py gives it its
# icon), so only the provider is attached; name, group and icon stay as they are.
app, created = Application.objects.get_or_create(
    slug=APP_SLUG,
    defaults=dict(name="NAS (Synology)", group="Storage", meta_launch_url=HOST,
                  policy_engine_mode="any"),
)
app.provider = provider
app.save()
print(f"APPLICATION: {app.slug} ({'created' if created else 'provider attached'})")

assert provider.signing_key, "no signing key -> empty JWKS -> DSM cannot verify the token"
assert type(provider.signing_key.private_key).__name__.startswith("RSA"), \
    "signing key must be RSA, DSM rejects ECDSA id_tokens"
assert not provider.encryption_key, "encryption key set -> JWE -> DSM cannot parse the token"
assert "authorization_code" in [str(g) for g in provider.grant_types]
assert len(provider.redirect_uris) == 1, "DSM only honours one redirect URI"
assert provider.property_mappings.count() == 3, "openid+email+profile required"
print(f"OK         : Well Known URL  https://auth.asbblog.com/application/o/{app.slug}/"
      ".well-known/openid-configuration")
print(f"OK         : Application ID  {provider.client_id}")
print(f"OK         : Redirect URL    {HOST}")
