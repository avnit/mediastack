#!/usr/bin/env bash
# crowdsec-allowlist.sh — (re)apply the CrowdSec allowlist. Idempotent.
#
# CrowdSec allowlists live in its SQLite DB (/var/lib/crowdsec/data), NOT in a config
# file, so they are not captured by this repo and are lost if that volume is rebuilt.
# Run this after any crowdsec data reset.
#
#   ./crowdsec-allowlist.sh
#
# An allowlisted source can never receive a decision, so keep this list tight.
set -euo pipefail

NAME=mediastack-trusted
DESC="LAN + Docker + Headscale tailnet + our own external IPs"

# RFC1918 LAN + Docker bridge
RANGES=(192.168.0.0/16 172.16.0.0/12 10.0.0.0/8)
# Headscale tailnet — must track prefixes.v4 / prefixes.v6 in headscale-config.yaml
RANGES+=(100.64.0.0/10 fd7a:115c:a1e0::/48)
# Our own external IPs, so an upstream NAT/CGNAT address can never lock us out.
# Add each as a bare IP or CIDR:
#   EXTERNAL_IPS=(203.0.113.45 198.51.100.0/29)
EXTERNAL_IPS=()

docker exec crowdsec cscli allowlists list 2>/dev/null | grep -qE "^ $NAME " \
  || docker exec crowdsec cscli allowlists create "$NAME" -d "$DESC"

# "add" is additive and errors on values already present, so filter to what's missing.
have=$(docker exec crowdsec cscli allowlists inspect "$NAME" 2>/dev/null | awk '{print $1}')
missing=()
for r in "${RANGES[@]}" ${EXTERNAL_IPS[@]+"${EXTERNAL_IPS[@]}"}; do
  grep -qxF "$r" <<<"$have" || missing+=("$r")
done

if [ ${#missing[@]} -eq 0 ]; then
  echo "[+] allowlist '$NAME' already complete (${#RANGES[@]} ranges, ${#EXTERNAL_IPS[@]} external)"
else
  docker exec crowdsec cscli allowlists add "$NAME" "${missing[@]}" -d "applied by crowdsec-allowlist.sh"
  echo "[+] added ${#missing[@]}: ${missing[*]}"
fi

docker exec crowdsec cscli allowlists inspect "$NAME"
