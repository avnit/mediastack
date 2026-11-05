#!/usr/bin/bash
set -e

# ==============================================================================
# Configuration
# ==============================================================================
FOLDER_FOR_YAMLS="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/"
ENV_FILE=".env"

# ==============================================================================
# Functions
# ==============================================================================

check_env() {
    cd "$FOLDER_FOR_YAMLS"
    if [ ! -f "$ENV_FILE" ]; then
        echo "❌ Error: .env file not found in $(pwd)"
        echo "Please update the FOLDER_FOR_YAMLS=/docker location inside the restart.sh script"
        exit 1
    fi
}

load_vars() {
    # Read values from .env and clean them
    FOLDER_FOR_MEDIA=$(grep -E '^FOLDER_FOR_MEDIA=' "$ENV_FILE" | cut -d '=' -f2- | xargs | tr -d '\r')
    FOLDER_FOR_DATA=$(grep  -E '^FOLDER_FOR_DATA='  "$ENV_FILE" | cut -d '=' -f2- | xargs | tr -d '\r')
    PUID=$(grep -E '^PUID=' "$ENV_FILE" | cut -d '=' -f2- | xargs | tr -d '\r')
    PGID=$(grep -E '^PGID=' "$ENV_FILE" | cut -d '=' -f2- | xargs | tr -d '\r')

    echo && echo "✅ Found the following variables / values in your $ENV_FILE file:"
    echo "   - FOLDER_FOR_MEDIA=$FOLDER_FOR_MEDIA"
    echo "   - FOLDER_FOR_DATA=$FOLDER_FOR_DATA"
    echo "   - PUID=$PUID"
    echo "   - PGID=$PGID"

    # Validate required vars
    MISSING_VARS=()
    [ -z "$FOLDER_FOR_MEDIA" ] && MISSING_VARS+=("FOLDER_FOR_MEDIA")
    [ -z "$FOLDER_FOR_DATA" ]  && MISSING_VARS+=("FOLDER_FOR_DATA")
    [ -z "$PUID" ] && MISSING_VARS+=("PUID")
    [ -z "$PGID" ] && MISSING_VARS+=("PGID")

    if [ ${#MISSING_VARS[@]} -ne 0 ]; then
        echo "❌ Error: The following required variables are missing or empty in $ENV_FILE:"
        for var in "${MISSING_VARS[@]}"; do
            echo "   - $var"
        done
        exit 1
    fi
}

read_env_value() {
    # Print the value of a variable from .env, without inline comments or whitespace
    grep -E "^$1=" "$ENV_FILE" | head -n1 | cut -d '=' -f2- | sed -E 's/[[:space:]]+#.*$//' | xargs | tr -d '\r'
}

check_secrets() {
    # Secrets are kept in .env only and injected into the deployed config copies
    # by copy_configs, so they never need to be stored in the tracked YAML files.
    MISSING_SECRETS=()
    [ -z "$(read_env_value CROWDSEC_BOUNCER_API_KEY)" ]     && MISSING_SECRETS+=("CROWDSEC_BOUNCER_API_KEY")
    [ -z "$(read_env_value HEADPLANE_OIDC_CLIENT_SECRET)" ] && MISSING_SECRETS+=("HEADPLANE_OIDC_CLIENT_SECRET")

    if [ ${#MISSING_SECRETS[@]} -ne 0 ]; then
        echo "❌ Error: The following secrets are missing or empty in $ENV_FILE:"
        for var in "${MISSING_SECRETS[@]}"; do
            echo "   - $var"
        done
        echo "   See .env.template for how to generate them. Nothing has been changed."
        exit 1
    fi

    if [ -z "$(read_env_value HEADPLANE_COOKIE_SECRET)" ]; then
        echo "⚠️  HEADPLANE_COOKIE_SECRET is not set in $ENV_FILE - Headplane will use the public default cookie secret."
    fi
}

inject_secret() {
    # $1 = variable name in .env, $2 = placeholder text, $3 = deployed config file
    local value escaped
    value=$(read_env_value "$1")
    [ -z "$value" ] && return 0
    escaped=$(printf '%s' "$value" | sed -e 's/[\\&|]/\\&/g')
    sudo sed -i "s|$2|$escaped|g" "$3"
}

create_directories() {
    echo 
    echo "Creating folders and setting permissions..."
    echo 
    cd "$FOLDER_FOR_YAMLS"
    
    # Data Directories
    sudo -E mkdir -p "$FOLDER_FOR_DATA"/{authentik/{certs,media,templates},bazarr,chromium,crowdsec/data,ddns-updater,filebot,gluetun,grafana,headplane/data,headscale/data,heimdall,homarr/{configs,data,icons},homepage,huntarr,jellyfin,jellyseerr,lidarr,logs/{unpackerr,traefik},mylar,plex,portainer,postgresql,prometheus,prowlarr,qbittorrent,radarr,readarr,sabnzbd,sonarr,tailscale,tdarr/{server,configs,logs},tdarr-node,traefik/letsencrypt,traefik-certs-dumper,unpackerr,valkey,whisparr}
    
    # Media Directories
    sudo -E mkdir -p "$FOLDER_FOR_MEDIA"/media/{anime,audio,books,comics,movies,music,photos,tv,xxx}
    sudo -E mkdir -p "$FOLDER_FOR_MEDIA"/usenet/{anime,audio,books,comics,complete,console,incomplete,movies,music,prowlarr,software,tv,xxx}
    sudo -E mkdir -p "$FOLDER_FOR_MEDIA"/torrents/{anime,audio,books,comics,complete,console,incomplete,movies,music,prowlarr,software,tv,xxx}
    sudo -E mkdir -p "$FOLDER_FOR_MEDIA"/watch
    sudo -E mkdir -p "$FOLDER_FOR_MEDIA"/filebot/{input,output}
    
    # Permissions
    sudo -E chmod -R 2775 "$FOLDER_FOR_MEDIA" "$FOLDER_FOR_DATA"
    sudo -E chown -R $PUID:$PGID "$FOLDER_FOR_MEDIA" "$FOLDER_FOR_DATA"
}

validate_docker_compose() {
    echo 
    echo "Validating Docker Compose configuration..."
    echo 
    if ! docker compose config > /dev/null; then
        echo 
        echo "Docker Compose configuration is invalid or missing required variables..."
        echo 
        exit 1
    fi
}

copy_configs() {
    echo 
    echo "Moving configuration files into application folders..."
    echo 
    sudo chmod 664                *yaml
    sudo chmod 640                .env                # Contains credentials - not world-readable
    sudo chown $PUID:$PGID        .env *yaml *sh
    
    # Create acme.json if missing and set strict permissions
    sudo touch                    "$FOLDER_FOR_DATA"/traefik/letsencrypt/acme.json
    sudo chmod 600                "$FOLDER_FOR_DATA"/traefik/letsencrypt/acme.json 

    # Copy config files
    sudo cp headplane-config.yaml "$FOLDER_FOR_DATA"/headplane/config.yaml
    sudo cp headscale-config.yaml "$FOLDER_FOR_DATA"/headscale/config.yaml
    sudo cp traefik-static.yaml   "$FOLDER_FOR_DATA"/traefik/traefik.yaml
    sudo cp traefik-dynamic.yaml  "$FOLDER_FOR_DATA"/traefik/dynamic.yaml
    sudo cp traefik-internal.yaml "$FOLDER_FOR_DATA"/traefik/internal.yaml
    sudo cp crowdsec-acquis.yaml  "$FOLDER_FOR_DATA"/crowdsec/acquis.yaml

    # Inject secrets from .env into the deployed copies (tracked files only hold placeholders)
    inject_secret CROWDSEC_BOUNCER_API_KEY     "CROWDSEC_BOUNCER_API_KEY_PLACEHOLDER"     "$FOLDER_FOR_DATA"/traefik/dynamic.yaml
    inject_secret HEADPLANE_OIDC_CLIENT_SECRET "HEADPLANE_OIDC_CLIENT_SECRET_PLACEHOLDER" "$FOLDER_FOR_DATA"/headplane/config.yaml
    # The tracked Headplane config ships the public default cookie secret; replace it when one is set
    inject_secret HEADPLANE_COOKIE_SECRET      "1234567890abcdef1234567890abcdef"         "$FOLDER_FOR_DATA"/headplane/config.yaml
}

cleanup_containers() {
    echo 
    echo "Removing all non-persistent Docker containers, volumes, and networks..."
    echo 
    # Use standard stop/rm for all containers on system (matching original behavior safely)
    containers=$(sudo docker ps -aq)
    if [ -n "$containers" ]; then
      sudo docker stop $containers || true
      sudo docker rm   $containers || true
    fi
    sudo docker container prune -f
}

start_stack() {
    echo 
    echo "Recreating all Docker containers, volumes, and networks..."
    echo 
    if ! docker compose up -d; then
        echo "Command 'docker compose up -d' failed..."
        exit 1
    fi
}

verify_stack() {
    EXPECTED_SERVICES=$(docker compose config --services)
    FAILED=0
    for SERVICE in $EXPECTED_SERVICES; do
        STATUS=$(docker inspect --format='{{.State.Running}}' "$(docker compose ps -q $SERVICE)" 2>/dev/null || echo "false")
        if [[ "$STATUS" != "true" ]]; then
            echo "Docker container $SERVICE is not running..."
            FAILED=1
        fi
    done

    if [[ $FAILED -eq 0 ]]; then
        echo 
        echo "✅ All Docker containers are running... Pruning unused images..."
        echo 
        sudo docker image prune -a -f
    else
        echo 
        echo "❌ One or more Docker services failed to start."
        echo 
        exit 1
    fi
}

# ==============================================================================
# Execution Flow
# ==============================================================================

check_env
load_vars
check_secrets
validate_docker_compose

# ------------------------------------------------------------------------------
# PARALLEL EXECUTION START
# ------------------------------------------------------------------------------
echo 
echo "⬇️  Pulling new / updated Docker images in BACKGROUND..."
echo "    (File operations will continue concurrently)"
echo 

# Start pull in background and capture PID
# Redirect output to a temp file to keep the console clean
PULL_LOG=$(mktemp)
echo "    Logs will be saved to: $PULL_LOG"
sudo docker compose pull > "$PULL_LOG" 2>&1 &
PULL_PID=$!

# Run local file operations while network pull happens
create_directories
copy_configs

echo 
echo "⏳ Waiting for Docker Pull (PID $PULL_PID) to complete..."
# Wait for pull to finish
wait $PULL_PID
PULL_EXIT_CODE=$?

if [ $PULL_EXIT_CODE -ne 0 ]; then
    echo "❌ Error: Docker pull failed! Here is the error output:"
    echo "-----------------------------------------------------"
    cat "$PULL_LOG"
    echo "-----------------------------------------------------"
    echo "Checking network connectivity..."
    if ping -c 1 google.com &> /dev/null; then
        echo "✅ Internet connection seems UP."
    else
        echo "❌ Internet connection seems DOWN. Please check your network."
    fi
    echo "⚠️  Proceeding with restart anyway (existing images will be used)..."
else
    echo "✅ Docker pull completed successfully."
    rm -f "$PULL_LOG"
fi

# ------------------------------------------------------------------------------
# PARALLEL EXECUTION END
# ------------------------------------------------------------------------------

# Now restart the stack
cleanup_containers
start_stack
verify_stack
