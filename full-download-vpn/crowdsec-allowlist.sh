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
# Public DNS resolvers. Listed explicitly even though the crowdsecurity/public-dns-allowlist
# parser already covers both (plus Quad9, CleanBrowsing, AdGuard and others).
RANGES+=(1.1.1.1 8.8.8.8)
#
# There is deliberately no port-53 entry. cscli allowlists take IP/CIDR only -- "53",
# "0.0.0.0/0:53" and "port:53" are all rejected as invalid IPs -- and nothing in this
# stack would generate a port-53 event anyway: the sole acquisition datasource is
# /logs/traefik/access.log (HTTP), no DNS server runs here, and nothing is bound to :53
# on the host. To protect a DNS server later, add it as an acquisition datasource and
# whitelist with a parser expression on the destination port, not with an allowlist.
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
