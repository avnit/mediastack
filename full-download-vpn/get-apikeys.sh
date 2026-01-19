#!/usr/bin/bash

# This script will extract all of the API Keys configured in the *ARR Media Library Managers
# You need to install 'yq' and 'xmllint' packages to parse configuration files

export FOLDER_FOR_YAMLS=/root/mediastack/full-download-vpn/                # <-- Folder where the yaml and .env files are located
export FOLDER_FOR_MEDIA=/shared/media/md           # <-- Folder where your media is locate
export FOLDER_FOR_DATA=/shared/media/data          # <-- Folder where MediaStack stores persistent data and configurations

export PUID=1000
export PGID=1000

# Auto-detect Docker host IP address
export DOCKER_HOST_IP=$(ip a | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep '^192\.' | head -n1)
# Fallback to hostname method if grep fails
if [ -z "$DOCKER_HOST_IP" ]; then
    export DOCKER_HOST_IP=$(hostname -I | awk '{print $1}')
fi


# cd $FOLDER_FOR_YAMLS
echo 
echo Extracting all current API Keys...
echo 

echo "Bazarr   API Key: " `yq -r '.auth.apikey' $FOLDER_FOR_DATA/bazarr/config/config.yaml` "  located in $FOLDER_FOR_DATA/bazarr/config/config.yaml"
echo "Lidarr   API Key: " `xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/lidarr/config.xml` "  located in $FOLDER_FOR_DATA/lidarr/config.xml"
echo "Mylar    API Key: " `grep '^api_key' $FOLDER_FOR_DATA/mylar/mylar/config.ini | sed -E 's/.*=\s*//'` "  located in $FOLDER_FOR_DATA/mylar/mylar/config.ini"
echo "Prowlarr API Key: " `xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/prowlarr/config.xml` "  located in $FOLDER_FOR_DATA/prowlarr/config.xml"
echo "Radarr   API Key: " `xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/radarr/config.xml` "  located in $FOLDER_FOR_DATA/radarr/config.xml"
echo "Readarr  API Key: " `xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/readarr/config.xml` "  located in $FOLDER_FOR_DATA/readarr/config.xml"
echo "Sonarr   API Key: " `xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/sonarr/config.xml` "  located in $FOLDER_FOR_DATA/sonarr/config.xml"
echo "Whisparr API Key: " `xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/whisparr/config.xml` "  located in $FOLDER_FOR_DATA/whisparr/config.xml"

echo
echo "==================================================================="
echo "HOMEPAGE Environment Variable Format (Copy to Homepage .env):"
echo "==================================================================="
echo

echo "HOMEPAGE_VAR_BAZARR_API_KEY="`yq -r '.auth.apikey' $FOLDER_FOR_DATA/bazarr/config/config.yaml`
echo "HOMEPAGE_VAR_LIDARR_API_KEY="`xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/lidarr/config.xml`
echo "HOMEPAGE_VAR_MYLAR_API_KEY="`grep '^api_key' $FOLDER_FOR_DATA/mylar/mylar/config.ini | sed -E 's/.*=\s*//'`
echo "HOMEPAGE_VAR_PROWLARR_API_KEY="`xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/prowlarr/config.xml`
echo "HOMEPAGE_VAR_RADARR_API_KEY="`xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/radarr/config.xml`
echo "HOMEPAGE_VAR_READARR_API_KEY="`xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/readarr/config.xml`
echo "HOMEPAGE_VAR_SONARR_API_KEY="`xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/sonarr/config.xml`
echo "HOMEPAGE_VAR_WHISPARR_API_KEY="`xmllint --xpath "string(//Config/ApiKey)" $FOLDER_FOR_DATA/whisparr/config.xml`

echo
echo "# Service URLs (Auto-detected Docker host IP: $DOCKER_HOST_IP)"
echo "HOMEPAGE_VAR_BAZARR_URL=http://$DOCKER_HOST_IP:6767"
echo "HOMEPAGE_VAR_LIDARR_URL=http://$DOCKER_HOST_IP:8686"
echo "HOMEPAGE_VAR_MYLAR_URL=http://$DOCKER_HOST_IP:8090"
echo "HOMEPAGE_VAR_PROWLARR_URL=http://$DOCKER_HOST_IP:9696"
echo "HOMEPAGE_VAR_RADARR_URL=http://$DOCKER_HOST_IP:7878"
echo "HOMEPAGE_VAR_READARR_URL=http://$DOCKER_HOST_IP:8787"
echo "HOMEPAGE_VAR_SONARR_URL=http://$DOCKER_HOST_IP:8989"
echo "HOMEPAGE_VAR_WHISPARR_URL=http://$DOCKER_HOST_IP:6969"

echo
echo "==================================================================="
