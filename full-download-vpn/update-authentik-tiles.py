"""Drop the Pi-hole launcher tiles and add the three Home Assistant instances.

Run with:  docker exec -i authentik ak shell < update-authentik-tiles.py
"""
from authentik.core.models import Application
from authentik.policies.models import PolicyBinding

ICON = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/home-assistant.png"

REMOVE = ["pi", "pi3"]

ADD = [
    ("home-assistant-154", "Home Assistant (.154)", "http://192.168.0.154:8123"),
    ("home-assistant-155", "Home Assistant (.155)", "http://192.168.0.155:8123"),
    ("home-assistant-168", "Home Assistant (.168)", "http://192.168.0.168:8123"),
]

for slug in REMOVE:
    app = Application.objects.filter(slug=slug).first()
    if app is None:
        print("REMOVE  :", slug, "(already gone)")
        continue
    # these tiles are plain links; refuse to cascade into a real provider
    assert app.provider is None, f"{slug} has provider {app.provider} - not deleting"
    bindings = PolicyBinding.objects.filter(target=app).count()
    app.delete()
    print("REMOVE  :", slug, f"(deleted, {bindings} policy binding(s))")

for slug, name, url in ADD:
    app, created = Application.objects.update_or_create(
        slug=slug,
        defaults=dict(
            name=name,
            group="Automation",
            meta_launch_url=url,
            meta_icon=ICON,
            meta_description="Home automation",
        ),
    )
    print("ADD     :", slug, "created" if created else "updated", "->", app.meta_launch_url)

print("TOTAL   :", Application.objects.count(), "applications")
print("PIHOLE  :", Application.objects.filter(slug__in=REMOVE).count(), "remaining (want 0)")
print("HASS    :", Application.objects.filter(slug__startswith="home-assistant").count(), "tiles (want 3)")
