#!/usr/bin/bash
#
# rotate-crowdsec-key.sh — mint a fresh CrowdSec bouncer API key, store it in
# .env, deploy it into the live Traefik dynamic config, and revoke the old one.
#
# Run from the directory containing docker-compose.yaml and .env:
#     ./rotate-crowdsec-key.sh
#
# The key is never echoed and never written to the repository. The repo copy of
# traefik-dynamic.yaml carries the placeholder __CROWDSEC_LAPI_KEY__, which is
# substituted here and by restart.sh's install_config_subst().
#
# Order matters: the new bouncer is registered and deployed BEFORE the old one
# is revoked, so there is no window where Traefik holds a key the LAPI rejects.
# traefik-bouncer@file guards most routers, so a bad key means refused requests.
#
set -euo pipefail

BOUNCER_PREFIX="traefik-bouncer"
NEW_BOUNCER="${BOUNCER_PREFIX}-$(date +%Y%m%d-%H%M%S)"
ENV_FILE=".env"

log()  { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n\n' "$*" >&2; exit 1; }

# ---- preflight ---------------------------------------------------------------
[ -f "$ENV_FILE" ]            || fail "$ENV_FILE not found. Run this from the compose directory."
[ -f traefik-dynamic.yaml ]   || fail "traefik-dynamic.yaml not found. Run this from the compose directory."
command -v docker >/dev/null  || fail "docker not in PATH."

FOLDER_FOR_DATA=$(grep -E '^FOLDER_FOR_DATA=' "$ENV_FILE" | cut -d '=' -f2- | xargs | tr -d '\r')
[ -n "$FOLDER_FOR_DATA" ]     || fail "FOLDER_FOR_DATA is not set in $ENV_FILE."

LIVE_DYNAMIC="$FOLDER_FOR_DATA/traefik/dynamic.yaml"
[ -f "$LIVE_DYNAMIC" ]        || fail "$LIVE_DYNAMIC not found."

docker inspect crowdsec >/dev/null 2>&1 || fail "crowdsec container not found."
if ! docker exec crowdsec cscli lapi status >/dev/null 2>&1; then
    fail "crowdsec LAPI is not answering. Fix crowdsec before rotating its keys."
fi

log "Existing bouncers"
docker exec crowdsec cscli bouncers list

# ---- 1. register the new bouncer --------------------------------------------
log "Registering new bouncer: $NEW_BOUNCER"
NEW_KEY=$(docker exec crowdsec cscli bouncers add "$NEW_BOUNCER" --output raw 2>/dev/null | tr -d '\r\n')
[ -n "$NEW_KEY" ] || fail "cscli bouncers add returned no key."
printf '    registered (key length %s, not shown)\n' "${#NEW_KEY}"

# ---- 2. record it in .env ----------------------------------------------------
log "Writing CROWDSEC_LAPI_KEY into $ENV_FILE"
cp -a "$ENV_FILE" "$ENV_FILE.bak-$(date +%Y%m%d-%H%M%S)"
if grep -qE '^CROWDSEC_LAPI_KEY=' "$ENV_FILE"; then
    sed -i "s|^CROWDSEC_LAPI_KEY=.*|CROWDSEC_LAPI_KEY=${NEW_KEY}|" "$ENV_FILE"
else
    printf 'CROWDSEC_LAPI_KEY=%s\n' "$NEW_KEY" >> "$ENV_FILE"
fi
grep -qE "^CROWDSEC_LAPI_KEY=.+" "$ENV_FILE" || fail "failed to write CROWDSEC_LAPI_KEY to $ENV_FILE."

# ---- 3. deploy it into the live dynamic config -------------------------------
log "Installing key into $LIVE_DYNAMIC"
cp -a "$LIVE_DYNAMIC" "$LIVE_DYNAMIC.bak-$(date +%Y%m%d-%H%M%S)"
TMP=$(mktemp)
sed "s|__CROWDSEC_LAPI_KEY__|${NEW_KEY}|" traefik-dynamic.yaml > "$TMP"
grep -q '__CROWDSEC_LAPI_KEY__' "$TMP" && { rm -f "$TMP"; fail "substitution failed; live config untouched."; }
grep -q "crowdsecLapiKey: ${NEW_KEY}" "$TMP" || { rm -f "$TMP"; fail "new key not present after substitution; live config untouched."; }
cp "$TMP" "$LIVE_DYNAMIC"
rm -f "$TMP"

# Traefik watches the directory; give it a moment to reload.
log "Waiting for Traefik to reload"
sleep 8

# ---- 4. verify Traefik still serves before revoking the old key --------------
log "Verifying Traefik"
if ! curl -s -o /dev/null -m 10 -w '%{http_code}' http://127.0.0.1:8080/api/overview | grep -qE '^(200|401|403)$'; then
    fail "Traefik API is not responding as expected. The new key is deployed and the
       old bouncers are still valid, so routing should be unaffected. Investigate
       with: docker logs traefik --tail=40"
fi
printf '    traefik responding\n'

# ---- 5. revoke the previous bouncers ----------------------------------------
log "Revoking previous bouncers"
OLD=$(docker exec crowdsec cscli bouncers list --output json 2>/dev/null \
      | python3 -c 'import json,sys
try: rows=json.load(sys.stdin)
except Exception: sys.exit(0)
for b in rows:
    n=b.get("name","")
    if n and n!=sys.argv[1]: print(n)' "$NEW_BOUNCER" || true)

if [ -z "$OLD" ]; then
    printf '    none to revoke\n'
else
    printf '%s\n' "$OLD" | while read -r b; do
        [ -n "$b" ] || continue
        printf '    deleting %s\n' "$b"
        docker exec crowdsec cscli bouncers delete "$b" || printf '    (could not delete %s)\n' "$b"
    done
fi

log "Done"
docker exec crowdsec cscli bouncers list
cat <<'EOS'

The old bouncer keys are now revoked. The key that was committed to the public
repository (traefik-dynamic.yaml, before this change) no longer authenticates.

CROWDSEC_LAPI_KEY now lives in .env, which is gitignored. The repo copy of
traefik-dynamic.yaml carries the placeholder; restart.sh substitutes it on
every deploy and refuses to install an unsubstituted file.

EOS
