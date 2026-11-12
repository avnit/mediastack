"""Add plain launcher tiles to Authentik. Idempotent - safe to re-run.

Run with:  docker exec -i authentik-worker ak shell < add-authentik-tiles.py

These tiles are links only. They have no provider, so Authentik shows them in
the library and nothing else. Whether the target sits behind the Authentik login
depends on the URL: a *.asbblog.com name goes through Traefik and forward-auth,
a bare LAN address goes straight to the application.

  dockhand  container dockhand-dockhand-1 on 192.168.0.17:3081, routed by
            lan-dockhand in traefik-internal.yaml (forward-auth).
  tdarr     container tdarr on 192.168.0.17:8265, routed by its own Traefik
            labels in docker-compose.yaml (forward-auth).
"""
from authentik.core.models import Application

ICONS = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/"

# slug, name, group, launch URL, icon file, description
TILES = [
    ("dockhand", "Dockhand", "Infrastructure", "https://dockhand.asbblog.com",
     "dockhand.png", "Docker management"),
    ("tdarr", "Tdarr", "Media", "https://tdarr.asbblog.com",
     "tdarr.png", "Media transcoding"),
]

for slug, name, group, url, icon, description in TILES:
    app, created = Application.objects.update_or_create(
        slug=slug,
        defaults=dict(
            name=name,
            group=group,
            meta_launch_url=url,
            meta_icon=ICONS + icon,
            meta_description=description,
            open_in_new_tab=True,
            policy_engine_mode="any",
        ),
    )
    assert app.provider is None, f"{slug} is a plain link and must not carry a provider"
    assert app.meta_launch_url == url
    print("OK  ", slug, "created" if created else "updated", "->", app.meta_launch_url,
          "| group:", app.group)
print("TOTAL:", Application.objects.count(), "applications")
