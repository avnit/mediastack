# Configure Authentik domain-level forward-auth for *.asbblog.com and bind it to
# the embedded outpost. Idempotent - safe to re-run.
#
# Run with:  docker exec -i authentik-worker ak shell < fix-authentik-outpost.py
#
# Why: the embedded outpost is RUNNING (/outpost.goauthentik.io/ping -> 204) but has
# 0 providers and Authentik has 0 applications, so /outpost.goauthentik.io/auth/traefik
# returns 404 for every X-Forwarded-Host. That 404 is what made every router carrying
# authentik-forwardauth@file fail - the outpost was never broken, just unconfigured.
from authentik.providers.proxy.models import ProxyProvider, ProxyMode
from authentik.core.models import Application
from authentik.outposts.models import Outpost
from authentik.flows.models import Flow

DOMAIN = "asbblog.com"
AUTH_HOST = f"https://auth.{DOMAIN}"

defaults = dict(
    # forward_domain = ONE provider covers every *.asbblog.com host.
    mode=ProxyMode.FORWARD_DOMAIN,
    external_host=AUTH_HOST,
    cookie_domain=DOMAIN,
    authorization_flow=Flow.objects.get(slug="default-provider-authorization-implicit-consent"),
    authentication_flow=Flow.objects.get(slug="default-authentication-flow"),
    invalidation_flow=Flow.objects.get(slug="default-provider-invalidation-flow"),
)

prov, created = ProxyProvider.objects.update_or_create(
    name="asbblog forward-auth", defaults=defaults
)
print(f"PROVIDER   : {prov.name} ({'created' if created else 'updated'}) "
      f"mode={prov.mode} external_host={prov.external_host} cookie_domain={prov.cookie_domain}")

app, created = Application.objects.update_or_create(
    slug="asbblog", defaults=dict(name="asbblog Services", provider=prov)
)
print(f"APPLICATION: {app.slug} ({'created' if created else 'updated'})")

outpost = Outpost.objects.get(managed="goauthentik.io/outposts/embedded")
outpost.providers.add(prov)
outpost.save()
print(f"OUTPOST    : {outpost.name} now has {outpost.providers.count()} provider(s)")
