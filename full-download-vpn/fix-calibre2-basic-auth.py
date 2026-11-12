# Let Authentik sign in to Calibre's own HTTP Basic login. Idempotent - safe to re-run.
#
# Run with:
#   docker exec -i authentik-worker ak shell < fix-calibre2-basic-auth.py
#
# Calibre is the linuxserver/calibre container on Unraid (192.168.0.95:19003).
# Its web desktop has one built-in login, HTTP Basic, set by the container's
# CUSTOM_USER / PASSWORD variables. Behind forward-auth that meant two logins:
# Authentik, then the browser's Basic prompt.
#
# This turns on "Send HTTP-Basic Authentication" on the domain-level forward-auth
# provider. After a successful check the outpost answers Traefik with
#   Authorization: Basic base64(<calibre_username>:<calibre_password>)
# built from two attributes of the signed-in user (group attributes count too).
#
# The script stores no secret. The two attributes are typed by the user in
# Authentik: Directory > Users > the user > Edit > Attributes
#   calibre_username: <CUSTOM_USER of the container>
#   calibre_password: <PASSWORD of the container>
#
# Three things that are easy to miss:
#
#   1. Traefik only forwards the header on routes that use the middleware
#      authentik-forwardauth-basic (traefik-dynamic.yaml). The shared
#      authentik-forwardauth middleware does not list Authorization, so no
#      other application is logged in to with these credentials.
#   2. On such a route Traefik REPLACES the request's Authorization header with
#      the outpost's. A user without the attributes gets a 401 from Calibre and
#      cannot type the password by hand. Set the attributes first.
#   3. The outpost reads attributes at login. After adding or changing them,
#      sign out of Authentik and in again.
#
# Side effect worth knowing: user attributes travel inside the id_token, and the
# shared middleware forwards that token as X-authentik-jwt. Applications behind
# forward-auth can therefore read calibre_password out of that header.
from authentik.core.models import User
from authentik.providers.proxy.models import ProxyProvider

PROVIDER = "asbblog forward-auth"
USER_ATTR = "calibre_username"
PASS_ATTR = "calibre_password"

prov = ProxyProvider.objects.get(name=PROVIDER)
prov.basic_auth_enabled = True
prov.basic_auth_user_attribute = USER_ATTR
prov.basic_auth_password_attribute = PASS_ATTR
prov.save()

prov.refresh_from_db()
assert prov.basic_auth_enabled, "basic auth did not stick"
assert prov.basic_auth_user_attribute == USER_ATTR
assert prov.basic_auth_password_attribute == PASS_ATTR
print(f"OK   provider '{prov.name}' pk={prov.pk}: basic auth on, "
      f"user attribute '{USER_ATTR}', password attribute '{PASS_ATTR}'")

# Names only. The values are never printed.
ready = []
for user in User.objects.filter(is_active=True).exclude(username__startswith="ak-outpost"):
    attrs = user.group_attributes()
    if attrs.get(USER_ATTR) and attrs.get(PASS_ATTR):
        ready.append(user.username)
if ready:
    print(f"OK   users with both attributes: {', '.join(sorted(ready))}")
else:
    print(f"WARN no user has both '{USER_ATTR}' and '{PASS_ATTR}'. "
          "Set them before the calibre2 route switches to authentik-forwardauth-basic.")
