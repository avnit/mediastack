# Configure the Proxmox VE OIDC provider in Authentik. Idempotent - safe to re-run.
#
# Run with:
#   docker exec -i authentik-worker ak shell < fix-proxmox-oidc.py
#
# The client secret is NOT stored here. It is read from CLIENT_SECRET_PATH inside
# the worker, so copy it in first, e.g.:
#   docker cp /root/.pve-oidc-secret authentik-worker:/tmp/pve-secret
#
# Three things the original 2024.10-era handoff blueprint got wrong against
# Authentik 2026.8.x, each of which broke login in a different way:
#
#   1. grant_types defaulted to []        -> "Invalid grant_type for provider",
#                                            every OIDC login rejected outright.
#   2. RedirectURI gained a third field   -> redirect_uri_type must be supplied.
#   3. redirect_uris listed only pve.*    -> pve4/pve6/pve7 failed with
#                                            "redirect_uri_no_match". Node URLs
#                                            not in the regex cannot log in.
import os

from authentik.core.models import Application, Group
from authentik.flows.models import Flow
from authentik.policies.models import PolicyBinding
from authentik.providers.oauth2.models import (
    GrantTypes, OAuth2Provider, RedirectURI, RedirectURIMatchingMode, RedirectURIType,
)

CLIENT_SECRET_PATH = os.environ.get("PVE_OIDC_SECRET", "/tmp/pve-secret")
ZONE = "asbblog.com"

secret = open(CLIENT_SECRET_PATH).read().strip()
assert secret, f"empty client secret at {CLIENT_SECRET_PATH}"

provider, created = OAuth2Provider.objects.update_or_create(
    name="proxmox",
    defaults=dict(
        client_id="proxmox",
        client_secret=secret,
        client_type="confidential",
        sub_mode="hashed_user_id",
        include_claims_in_id_token=True,
        # (1) without this, authentik rejects the authorization_code exchange
        grant_types=[GrantTypes.AUTHORIZATION_CODE, GrantTypes.REFRESH_TOKEN],
        authorization_flow=Flow.objects.get(
            slug="default-provider-authorization-implicit-consent"),
        authentication_flow=Flow.objects.get(slug="default-authentication-flow"),
        invalidation_flow=Flow.objects.get(slug="default-provider-invalidation-flow"),
    ),
)
# (2) redirect_uri_type is required on 2026.x
# (3) cover every cluster node hostname and IP, not just the primary
provider.redirect_uris = [
    RedirectURI(RedirectURIMatchingMode.REGEX,
                rf'^https://pve[0-9]*\.{ZONE.replace(".", chr(92) + ".")}/?$',
                RedirectURIType.AUTHORIZATION),
    RedirectURI(RedirectURIMatchingMode.REGEX,
                r'^https://192\.168\.0\.(11|45|88|160|192):8006/?$',
                RedirectURIType.AUTHORIZATION),
]
provider.save()
provider.refresh_from_db()

print(f"PROVIDER   : {provider.name} ({'created' if created else 'updated'}) "
      f"client_id={provider.client_id} grants={provider.grant_types}")
for r in provider.redirect_uris:
    print(f"REDIRECT   : {r.matching_mode.value}  {r.url}")

app, created = Application.objects.update_or_create(
    # slug is deliberately NOT "proxmox": that is taken by an existing RAC
    # (remote access) application and reusing it would detach its provider.
    slug="proxmox-oidc",
    defaults=dict(name="Proxmox VE", provider=provider, group="Proxmox",
                  meta_launch_url=f"https://pve.{ZONE}", policy_engine_mode="any"),
)
print(f"APPLICATION: {app.slug} ({'created' if created else 'updated'})")

group, _ = Group.objects.get_or_create(name="proxmox-admins")
PolicyBinding.objects.get_or_create(
    target=app, group=group, order=0,
    defaults=dict(enabled=True, negate=False, timeout=30),
)
print(f"GROUP      : {group.name} members={group.users.count()}")

assert "authorization_code" in [str(g) for g in provider.grant_types], \
    "authorization_code missing - OIDC login will fail"
assert provider.redirect_uris, "no redirect_uris - login fails with redirect_uri_no_match"
print("OK         : issuer https://auth.{0}/application/o/{1}/".format(ZONE, app.slug))
