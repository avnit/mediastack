#!/usr/bin/bash
#
# sync-jackett-to-whisparr.sh — wrapper around jackett_to_whisparr.py
#
# Loads JACKETT_URL / JACKETT_API_KEY / WHISPARR_URL / WHISPARR_API_KEY from
# .env and passes every argument straight through to the Python script, so the
# API keys never appear in a committed file or in your shell history.
#
#     ./sync-jackett-to-whisparr.sh --dry-run      # list what would be added
#     ./sync-jackett-to-whisparr.sh --xxx-only     # recommended
#     ./sync-jackett-to-whisparr.sh                # every indexer Jackett has
#
# Also invoked by "./restart.sh --sync-indexers" after the stack verifies.
#
set -euo pipefail

ENV_FILE=".env"
SCRIPT="jackett_to_whisparr.py"

cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE not found in $(pwd)" >&2; exit 1; }
[ -f "$SCRIPT" ]   || { echo "ERROR: $SCRIPT not found in $(pwd)"   >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 not in PATH" >&2; exit 1; }

# Read one value from .env without sourcing it: .env holds passwords containing
# characters a shell would try to interpret.
#
# Must never return non-zero -- under "set -e" a failing command substitution
# aborts the whole script, so a simply-absent variable would exit silently
# instead of producing the missing-variable report below.
read_env() {
    local line val
    line=$(grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -n1 || true)
    if [ -z "$line" ]; then
        printf ''
        return 0
    fi
    val=${line#*=}
    val=${val%%[[:space:]]#*}                          # drop a trailing "  # comment"
    val=${val%$'\r'}                                   # drop CR from CRLF files
    val="${val#"${val%%[![:space:]]*}"}"               # trim leading whitespace
    val="${val%"${val##*[![:space:]]}"}"               # trim trailing whitespace
    printf '%s' "$val"
}

MISSING=()
for var in JACKETT_URL JACKETT_API_KEY WHISPARR_URL WHISPARR_API_KEY; do
    val=$(read_env "$var")
    if [ -z "$val" ] || [[ "$val" == *YOUR_* || "$val" == *GENERATE_* ]]; then
        MISSING+=("$var")
    else
        export "$var=$val"
    fi
done

# Optional: Jackett's URL as reachable from inside Whisparr's network namespace.
# Written as an "if" rather than "[ -n ... ] && ..." because the latter returns
# non-zero when empty, which "set -e" treats as a fatal error.
JU=$(read_env JACKETT_URL_FOR_WHISPARR)
if [ -n "$JU" ]; then
    export JACKETT_URL_FOR_WHISPARR="$JU"
fi

if [ ${#MISSING[@]} -ne 0 ]; then
    echo
    echo "ERROR: the following are unset or still placeholders in $ENV_FILE:" >&2
    printf '   - %s\n' "${MISSING[@]}" >&2
    echo
    echo "  JACKETT_API_KEY   Jackett dashboard, top right, \"API Key\"" >&2
    echo "  WHISPARR_API_KEY  Whisparr -> Settings -> General -> Security" >&2
    echo
    echo "Put them in $ENV_FILE (gitignored). Do not add them to any file that" >&2
    echo "is committed -- this repository is public." >&2
    echo
    exit 1
fi

echo "Jackett:  $JACKETT_URL"
echo "Whisparr: $WHISPARR_URL"
echo

exec python3 "$SCRIPT" "$@"
