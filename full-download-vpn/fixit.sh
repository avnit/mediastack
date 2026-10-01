#!/usr/bin/env bash
set -euo pipefail
cd ~/mediastack/full-download-vpn
cp -n .env .env.bak.$(date +%F) || true

: "${NORD_TOKEN:?export NORD_TOKEN first}"
[ ${#NORD_TOKEN} -eq 64 ] || { echo "NORD_TOKEN wrong length (${#NORD_TOKEN}) — need 64-hex access token"; exit 1; }

KEY=$(curl -sf -u "token:$NORD_TOKEN" https://api.nordvpn.com/v1/users/services/credentials | jq -r '.nordlynx_private_key // empty')
[ ${#KEY} -eq 44 ] || { echo "bad key (len ${#KEY}) — token rejected or no active plan; not writing"; exit 1; }

sed -i -E \
  -e 's|^VPN_TYPE=.*|VPN_TYPE=wireguard|' \
  -e "s|^WIREGUARD_PRIVATE_KEY=.*|WIREGUARD_PRIVATE_KEY=${KEY}|" \
  -e 's|^SERVER_REGIONS=.*|SERVER_REGIONS=|' \
  -e 's|^SERVER_CITIES=.*|SERVER_CITIES=Los Angeles|' \
  .env
unset KEY
echo "env updated:"; grep -E '^(VPN_TYPE|SERVER_CITIES|WIREGUARD_PRIVATE_KEY)=' .env | sed -E 's/(KEY=).{40}/\1…/'

docker compose up -d --force-recreate gluetun
sleep 25
docker logs gluetun --tail 40 2>&1 | grep -E 'ERROR|Wireguard setup is complete|Public IP' || true
echo "health: $(docker inspect gluetun --format '{{.State.Health.Status}}')"
