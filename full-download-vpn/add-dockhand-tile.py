"""Add the Dockhand launcher tile to Authentik. Idempotent - safe to re-run.

Run with:  docker exec -i authentik-worker ak shell < add-dockhand-tile.py

Dockhand (container dockhand-dockhand-1 on 192.168.0.17, host port 3081) has no
Traefik route, so the tile is a plain link to the LAN address. It has no
provider: Authentik only shows the tile, Dockhand does its own login, and the
link works on the LAN only.
"""
from authentik.core.models import Application

SLUG = "dockhand"
URL = "http://192.168.0.17:3081/"

app, created = Application.objects.update_or_create(
    slug=SLUG,
    defaults=dict(
        name="Dockhand",
        group="Infrastructure",
        meta_launch_url=URL,
        meta_icon="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/dockhand.png",
        meta_description="Docker management",
        open_in_new_tab=True,
        policy_engine_mode="any",
    ),
)
assert app.provider is None, "the Dockhand tile is a plain link and must not carry a provider"
assert app.meta_launch_url == URL
print("OK  ", SLUG, "created" if created else "updated", "->", app.meta_launch_url,
      "| group:", app.group)
print("TOTAL:", Application.objects.count(), "applications")
