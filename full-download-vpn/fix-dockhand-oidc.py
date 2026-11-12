# Configure the Dockhand OIDC provider in Authentik. Idempotent - safe to re-run.
#
# Run with:
#   docker cp /root/.dockhand-oidc-secret authentik-worker:/tmp/dockhand-secret
#   docker exec -u 0 authentik-worker chmod 644 /tmp/dockhand-secret
#   docker exec -i authentik-worker ak shell < fix-dockhand-oidc.py
#   docker exec -u 0 authentik-worker rm -f /tmp/dockhand-secret
#
# Dockhand (container dockhand-dockhand-1, fnsys/dockhand, 192.168.0.17:3081) is
# a separate compose project. It keeps its OIDC settings in its own database, so
# the other half is typed into Dockhand: Settings > Authentication > SSO / OIDC >
# Add OIDC provider. The fields are listed in README.md. The same client secret
# goes into its "Client secret" field.
#
# What Dockhand 1.0.49 does with the login (read from its server code):
#
#   - authorization code with PKCE S256, the client secret sent in the POST body;
#   - the redirect URI is whatever is typed into its form, so it must be exactly
#     https://dockhand.asbblog.com/api/auth/oidc/callback;
#   - it fetches the discovery document, the token and userinfo from inside the
#     container, so the container must reach https://auth.asbblog.com;
#   - the user is matched on the username claim (preferred_username). A matching
#     Dockhand user is reused, otherwise a new one is CREATED on first login;
#   - in the free edition every signed-in user is an administrator. Roles and
#     the "Admin claim" only take effect with an Enterprise licence.
#
# Because of the last two points this script binds the application to one
# Authentik group. Only its members can complete the Dockhand login; everyone
# else is refused by Authentik before Dockhand ever creates an account.
import os

from authentik.core.models import Application, Group
from authentik.crypto.models import CertificateKeyPair
from authentik.flows.models import Flow
from authentik.policies.models import PolicyBinding
from authentik.providers.oauth2.models import (
    GrantTypes, OAuth2Provider, RedirectURI, RedirectURIMatchingMode,
    RedirectURIType, ScopeMapping,
)

SECRET_PATH = os.environ.get("DOCKHAND_OIDC_SECRET", "/tmp/dockhand-secret")
HOST = "https://dockhand.asbblog.com"
CALLBACK = HOST + "/api/auth/oidc/callback"
APP_SLUG = "dockhand"   # the existing launcher tile; issuer path /application/o/dockhand/
ALLOWED_GROUP = "authentik Admins"   # full Docker control: keep this narrow

secret = open(SECRET_PATH).read().strip()
assert secret, f"empty client secret at {SECRET_PATH}"

provider, created = OAuth2Provider.objects.update_or_create(
    name="dockhand",
    defaults=dict(
        client_id="dockhand",
        client_secret=secret,
        client_type="confidential",
        sub_mode="hashed_user_id",
        include_claims_in_id_token=True,
        encryption_key=None,   # Dockhand reads the id_token payload as plain JWT
        grant_types=[GrantTypes.AUTHORIZATION_CODE],   # defaults to [] otherwise
        signing_key=CertificateKeyPair.objects.get(
            name="authentik Self-signed Certificate"),
        authorization_flow=Flow.objects.get(
            slug="default-provider-authorization-implicit-consent"),
        authentication_flow=Flow.objects.get(slug="default-authentication-flow"),
        invalidation_flow=Flow.objects.get(slug="default-provider-invalidation-flow"),
    ),
)
provider.redirect_uris = [
    RedirectURI(RedirectURIMatchingMode.STRICT, CALLBACK, RedirectURIType.AUTHORIZATION),
]
stock = ScopeMapping.objects.filter(managed__in=[
    "goauthentik.io/providers/oauth2/scope-openid",
    "goauthentik.io/providers/oauth2/scope-email",
    "goauthentik.io/providers/oauth2/scope-profile",
])
assert stock.count() == 3, "stock openid/email/profile scope mappings missing"
provider.property_mappings.set(stock)
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

# The "Dockhand" tile already exists (add-authentik-tiles.py), so only the
# provider is attached; name, group, icon and launch URL stay as they are.
app, created = Application.objects.get_or_create(
    slug=APP_SLUG,
    defaults=dict(name="Dockhand", group="Infrastructure", meta_launch_url=HOST,
                  policy_engine_mode="any"),
)
app.provider = provider
app.save()
print(f"APPLICATION: {app.slug} ({'created' if created else 'provider attached'})")

group = Group.objects.get(name=ALLOWED_GROUP)
binding, created = PolicyBinding.objects.update_or_create(
    target=app, group=group, defaults=dict(order=0, enabled=True, negate=False),
)
members = sorted(group.users.exclude(username__startswith="ak-outpost-")
                 .values_list("username", flat=True))
print(f"ACCESS     : group '{group.name}' ({'bound' if created else 'already bound'}) "
      f"members={members}")

assert provider.signing_key, "no signing key -> empty JWKS"
assert not provider.encryption_key, "encryption key set -> JWE -> Dockhand cannot read the token"
assert "authorization_code" in [str(g) for g in provider.grant_types]
assert [r.url for r in provider.redirect_uris] == [CALLBACK]
assert provider.property_mappings.count() == 3, "openid+email+profile required"
assert PolicyBinding.objects.filter(target=app, enabled=True).count() == 1, \
    "exactly one binding expected: the allowed group"
print(f"OK         : Issuer URL     https://auth.asbblog.com/application/o/{app.slug}/")
print(f"OK         : Client ID      {provider.client_id}")
print(f"OK         : Redirect URI   {CALLBACK}")
