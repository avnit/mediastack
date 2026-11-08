# Set launcher icons on every Authentik application. Idempotent - safe to re-run.
#
# Run with:  docker exec -i authentik-worker ak shell < set-authentik-icons.py
#
# Icons come from the homarr-labs/dashboard-icons CDN, the same naming convention
# the homepage.* labels in docker-compose.yaml already use. meta_icon is a
# FileField but accepts a plain URL string, which is how the Authentik UI stores
# "use an external URL" icons.
#
# Every URL below was verified to return HTTP 200 image/png before being applied.
# Entries marked GUESS were inferred from the hostname/port and may be wrong -
# correct them if the app is actually something else.
from authentik.core.models import Application

ICONS = {
    "asbblog": "authentik.png",
    "proxmox": "proxmox.png",
    "ollama": "ollama.png",
    "openwebui": "open-webui.png",
    "lidarr2": "lidarr.png",
    "lidarr3": "lidarr.png",
    "prowlarr2": "prowlarr.png",
    "prowlarr3": "prowlarr.png",
    "radarr2": "radarr.png",
    "radarr3": "radarr.png",
    "readarr3": "readarr.png",
    "sonarr2": "sonarr.png",
    "sonarr3": "sonarr.png",
    "n8n": "n8n.png",
    "calibre": "calibre-web.png",
    "calibre2": "calibre-web.png",
    "homarr3": "homarr.png",
    "homepage": "homepage.png",
    "homepage2": "homepage.png",
    "jacket": "jackett.png",
    "qb": "qbittorrent.png",
    "qb2": "qbittorrent.png",
    "qb3": "qbittorrent.png",
    "transmission": "transmission.png",
    "casaos": "casaos.png",
    "coolify": "coolify.png",
    "docker": "docker.png",
    "portainer": "portainer.png",
    "traefik": "traefik.png",
    "umbrel": "umbrel.png",
    "hdhome": "hdhomerun.png",
    "jelly": "jellyfin.png",
    "jellyfin": "jellyfin.png",
    "jellyfin3": "jellyfin.png",
    "jellyseerr": "jellyseerr.png",
    "music": "navidrome.png",
    "grafana": "grafana.png",
    "speedtest": "speedtest-tracker.png",
    "headscale": "headscale.png",
    "pi": "pi-hole.png",
    "pi3": "pi-hole.png",
    "hermes": "hermes.png",
    "hermes2": "hermes.png",
    "mindcraft": "minecraft.png",
    "proxmox-oidc": "proxmox.png",
    "pve2": "proxmox.png",
    "pve4": "proxmox.png",
    "pve6": "proxmox.png",
    "pve7": "proxmox.png",
    "idm": "authentik.png",
    "vault1": "vaultwarden.png",
    "file": "filebrowser.png",
    "immich": "immich.png",
    "immich2": "immich.png",
    "nas": "synology-dsm.png",
    "truenas1": "truenas.png",
    "unraid": "unraid.png",
    "tools": "it-tools.png",
    "asbsolutions-group": "wordpress.png",
    "asbsolutions-us": "wordpress.png",
}
GUESSES = {"music", "idm", "vault1", "speedtest", "tools", "file",
           "hermes", "hermes2", "mindcraft",
           "asbsolutions-group", "asbsolutions-us"}
BASE = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png"

updated = missing = 0
for slug, icon in ICONS.items():
    app = Application.objects.filter(slug=slug).first()
    if not app:
        print(f"SKIP       : no application with slug {slug}")
        missing += 1
        continue
    app.meta_icon = f"{BASE}/{icon}"
    app.save()
    updated += 1

print(f"UPDATED    : {updated} application(s), {missing} not found")
total = Application.objects.count()
print(f"WITH ICON  : {Application.objects.exclude(meta_icon='').count()}/{total}")
for app in Application.objects.filter(meta_icon="").order_by("slug"):
    print(f"NO ICON    : {app.slug} ({app.name})")
print(f"GUESSED    : {sorted(GUESSES)}")
