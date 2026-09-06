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

create_directories() {
    echo 
    echo "Creating folders and setting permissions..."
    echo 
    cd "$FOLDER_FOR_YAMLS"
    
    # Data Directories
    sudo -E mkdir -p "$FOLDER_FOR_DATA"/{authentik/{certs,media,templates},bazarr,chromium,crowdsec/data,ddns-updater,filebot,gluetun,grafana,headplane/data,headscale/data,heimdall,homarr/{configs,data,icons},homepage,huntarr,jellyfin,jellyseerr,lidarr,logs/{unpackerr,traefik},mylar,plex,portainer,postgresql,prometheus,prometheus-config,prowlarr,qbittorrent,radarr,readarr,sabnzbd,sonarr,tailscale,tdarr/{server,configs,logs},tdarr-node,traefik/letsencrypt,traefik-certs-dumper,unpackerr,valkey,whisparr}
    
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

ensure_generated_secrets() {
    # Variables the compose file requires that have no sensible default and must
    # never be committed. Generated once and written into .env, so a fresh clone
    # or a "git pull" that introduces a new secret does not hard-fail
    # "docker compose config" on an unset ${VAR:?err}.
    echo
    echo "Checking generated secrets in $ENV_FILE..."

    local var placeholder="GENERATE_YOUR_OWN_SECRET_KEY_HERE" generated=0 current

    for var in HOMARR_NEXTAUTH_SECRET; do
        current=$(grep -E "^${var}=" "$ENV_FILE" | cut -d '=' -f2- | xargs | tr -d '\r')

        if [ -z "$current" ] || [ "$current" = "$placeholder" ]; then
            # Drop any empty or placeholder line so we never end up with duplicates.
            sudo sed -i "/^${var}=$/d;/^${var}=${placeholder}\$/d" "$ENV_FILE"
            printf '%s=%s\n' "$var" "$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)" \
                | sudo tee -a "$ENV_FILE" > /dev/null
            echo "   - $var: generated"
            generated=1
        else
            echo "   - $var: present"
        fi
    done

    if [ "$generated" -eq 1 ]; then
        echo
        echo "   New secrets were written. Homarr will require a fresh login."
    fi
}

migrate_legacy_layout() {
    # prometheus.yml used to be mounted from inside the TSDB data directory, which
    # meant clearing a corrupt write-ahead log also deleted the configuration.
    # Move it out once; safe to re-run.
    if [ -f "$FOLDER_FOR_DATA/prometheus/prometheus.yml" ] && \
       [ ! -e "$FOLDER_FOR_DATA/prometheus-config/prometheus.yml" ]; then
        echo
        echo "Migrating prometheus.yml out of the TSDB data directory..."
        sudo mkdir -p "$FOLDER_FOR_DATA"/prometheus-config
        sudo mv "$FOLDER_FOR_DATA"/prometheus/prometheus.yml "$FOLDER_FOR_DATA"/prometheus-config/prometheus.yml
        sudo chown "$PUID:$PGID" "$FOLDER_FOR_DATA"/prometheus-config/prometheus.yml
        echo "   - moved to $FOLDER_FOR_DATA/prometheus-config/prometheus.yml"
    fi

    # Docker silently creates a DIRECTORY when a bind-mount source file is missing.
    # Prometheus then fails to start with an unhelpful parse error, so name it here.
    if [ -d "$FOLDER_FOR_DATA/prometheus-config/prometheus.yml" ]; then
        echo
        echo "❌ Error: $FOLDER_FOR_DATA/prometheus-config/prometheus.yml is a DIRECTORY."
        echo "   Docker created it because the config file was missing when a container started."
        echo "   Remove it and restore the real prometheus.yml before continuing:"
        echo "     sudo rmdir '$FOLDER_FOR_DATA/prometheus-config/prometheus.yml'"
        echo
        exit 1
    fi
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
    sudo chmod 664                .env *yaml
    sudo chown $PUID:$PGID        .env *yaml *sh
    
    # Create acme.json if missing and set strict permissions.
    # MUST run after create_directories() - the recursive "chmod -R 2775" there
    # would otherwise leave this world-readable. Traefik refuses to load an
    # acme.json looser than 600 and silently drops the letsencrypt resolver
    # ("ACME resolve is skipped"), so every route falls back to the self-signed
    # certificate. The traefik-init service in docker-compose.yaml re-asserts
    # this on every container start; this is the belt to that pair of braces.
    sudo touch                    "$FOLDER_FOR_DATA"/traefik/letsencrypt/acme.json
    sudo chmod 600                "$FOLDER_FOR_DATA"/traefik/letsencrypt/acme.json
    echo "   - acme.json permissions: $(stat -c '%a' "$FOLDER_FOR_DATA"/traefik/letsencrypt/acme.json) (must be 600)"

    # Copy config files
    sudo cp headplane-config.yaml "$FOLDER_FOR_DATA"/headplane/config.yaml
    sudo cp headscale-config.yaml "$FOLDER_FOR_DATA"/headscale/config.yaml
    sudo cp traefik-static.yaml   "$FOLDER_FOR_DATA"/traefik/traefik.yaml
    sudo cp traefik-dynamic.yaml  "$FOLDER_FOR_DATA"/traefik/dynamic.yaml
    sudo cp traefik-internal.yaml "$FOLDER_FOR_DATA"/traefik/internal.yaml
    sudo cp crowdsec-acquis.yaml  "$FOLDER_FOR_DATA"/crowdsec/acquis.yaml
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

check_port_conflicts() {
    echo
    echo "Checking for host port conflicts before starting the stack..."
    echo

    local ports conflicts=0 holder
    ports=$(docker compose config 2>/dev/null | sed -n 's/.*published: "\([0-9]\{1,5\}\)".*/\1/p' | sort -un)

    if [ -z "$ports" ]; then
        echo "WARNING: could not read published ports from 'docker compose config' - skipping check."
        return 0
    fi

    for port in $ports; do
        # Runs after cleanup_containers(), so any listener found here is foreign to this stack.
        holder=$(ss -tulpn 2>/dev/null | awk -v p=":${port}$" '$5 ~ p' | grep -v 'docker-proxy' | head -n1 || true)
        if [ -n "$holder" ]; then
            echo "Host port $port is already in use:"
            echo "     $holder"
            conflicts=1
        fi
    done

    if [ "$conflicts" -ne 0 ]; then
        echo
        echo "Free the ports listed above before starting."
        echo
        echo "   A conflict makes Docker fail with 'failed to bind host port', and gluetun"
        echo "   then reports the misleading 'default route not found: in N route(s)'"
        echo "   because its endpoint is torn down after the failed bind. Every container"
        echo "   using 'network_mode: service:gluetun' goes down with it."
        echo
        echo "   Common culprit: a natively-installed service competing with its own"
        echo "   container, e.g. 'systemctl disable --now plexmediaserver' for port 32400."
        echo
        exit 1
    fi

    echo "No host port conflicts detected."
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
ensure_generated_secrets
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
migrate_legacy_layout
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
check_port_conflicts
start_stack
verify_stack
