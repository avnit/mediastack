# MediaStack Project (Docker) - Testing Traefik Reverse Proxy  

Go to: [https://github.com/geekau/mediastack](https://github.com/geekau/mediastack)  

Download the full **mediastack** repository to your computer by selecting **Code** --> **Download Zip**  

Extract the downloaded zip file, then go to the directory which suits your deployment method  

Full deployment and configuration instructions are located at: [https://MediaStack.Guide](https://MediaStack.Guide)  

</br>

## What is the Traefik testing?  

> NOTE: This configuration will provide FULL outbound VPN for all media and download applications, and FULL inbound TLS1.2/1.3 encryption to web services provided by Traefik.  

We've been hearing back that SWAG has been difficult to configure and access containers which are hidden behind the Gluetun VPN container.  

So we've removed the SWAG and Authelia containers, and added the Traefik container to handle reverse proxy, as it works entirely different with the inbound requests, and how they're labelled and rounted to the relevant Docker containers.  

In order to deploy / test Traefik:  

- Download all of the files in the this GitHub folder  
- Update the `.env` file with all your settings / values from your existing `docker-compose.env` file - if you have an earlier version of MediaStack running  
- Replace `example.com` with your Internet domain in the `headscale-config.yaml`, `headplane-config.yaml`, `traefik-dynamic.yaml`, `traefik-internal.yaml` and `traefik-static.yaml` files  
- Update cookie_secret in `headplane-config.yaml` using 32 random characters  
- Update `restart.sh` script with your values for:  
  - export FOLDER_FOR_YAMLS=/docker             # <-- Folder where the yaml and .env files are located  
  - export FOLDER_FOR_MEDIA=/docker/media       # <-- Folder where your media is locate  
  - export FOLDER_FOR_DATA=/docker/appdata      # <-- Folder where MediaStack stores persistent data and configurations  
  - export PUID=1000  
  - export PGID=1000  
- Enable execution of shell scripts with `sudo chmod 775 *sh`  

Start the MediaStack after changes with `./restart.sh`  

> NOTE: The variable values in `.env` and `restart.sh` should be identical, otherwise you will have configuration errors  

The Postgresql server still needs some minor configuration to complete the MediaStack deployment:  

- Set permissions on Authentik Postgresql database with `./secure_authentik_database.sh` script  
- Set up Guacamole Postgresql database and access permissions with `./create_guacamole_database.sh` script  

Restart the MediaStack after changes with `./restart.sh`  

## Configure Headscale / Tailscale / Headplane

Replace all instances of `example.com` in the configuration files with your own domain name  

> NOTE: Tailscale Authkey can't be set in `.env` file until the Headscale container has been deployed  

### Register Tailscale Exit Node with Headscale

Execute these commands once Headscale has been deployed:  

``` bash
sudo docker exec -it headscale headscale users create exit-node
sudo docker exec -it headscale headscale users list
```

List of users will be displayed showing their "ID" number:  

``` bash
ID | Name | Username  | Email | Created            
1  |      | exit-node |       | 2025-05-17 23:30:33
```

Create a PreAuthKey for "exit-node" with following command:  

``` bash
sudo docker exec -it headscale headscale --user 1 preauthkeys create
```

Output will display as:

``` bash
2025-05-18T09:46:34+10:00 TRC expiration has been set expiration=3600000
4f9e5c04a019273ef6356b3f4c173b2a896749e7364993f5
```

Add the authkey to `TAILSCALE_AUTHKEY` in the `.env` file.  

Restart the Tailscale container:  

``` bash
sudo docker compose restart tailscale
```

Check Tailscale exit node has connected and registered with Headscale:  

``` bash
sudo docker exec -it headscale headscale nodes list
```

Check to see if the Tailscale exit node has registered the local / home subnet addresses with the Headscale server:  

``` bash
sudo docker exec -it headscale headscale nodes list-routes
```

List of routes for each host will be displayed showing their "ID" number:  

``` bash
ID | Hostname  | Approved | Available                                       | Serving (Primary)
1  | exit-node |          | 0.0.0.0/0, 192.168.1.0/24, 172.28.10.0/24, ::/0 |  
```

Enable IP routing out of the Tailscale exit node with the following command:  

``` bash
sudo docker exec -it headscale headscale nodes approve-routes --identifier 1 --routes "0.0.0.0/0,192.168.1.0/24,172.28.10.0/24,::/0"
sudo docker exec -it headscale headscale nodes list-routes
```

The IP routes will now be enabled and look like this:  

``` bash
ID | Hostname  | Approved                                        | Available                                       | Serving (Primary)  
1  | exit-node | 0.0.0.0/0, 192.168.1.0/24, 172.28.10.0/24, ::/0 | 0.0.0.0/0, 192.168.1.0/24, 172.28.10.0/24, ::/0 | 192.168.1.0/24, 172.28.10.0/24, 0.0.0.0/0, ::/0
```

### Register Mobile Tailscale Application with Headscale

You can now download the official Tailscale application, and when prompted to login, select a custom URL.  

Enter your home Headscale URL: [https://headscale.example.com](https://headscale.example.com)  

When you select connect, it will ask if you want to go to the URL, select Yes, then it will show a connection string like  

``` bash
headscale nodes register --user USERNAME --key 64LErdY2YcnMdNLNYc6wJJzE
```

We need to first create a user account, then register the Tailscale node against that account:  

``` bash
sudo docker exec -it headscale headscale users create alice
sudo docker exec -it headscale headscale nodes register --user alice --key 64LErdY2YcnMdNLNYc6wJJzE
```

The Tailscale will now automatically connect with the Headscale server, which can be checked with commands:  

``` bash
sudo docker exec -it headscale headscale users list
sudo docker exec -it headscale headscale nodes list
sudo docker exec -it headscale headscale nodes list-routes
```

You can now go to the Tailscale application on your phone, and select `Exit Node` --> `exit-node` and turn on `Allow Local Network Access`.  

You can also go into the Tailscale application settings on your phone, and turn on `VPN On Demand`, so you always have remote access when away from home.  

### WebUI Managed with Headplane

Headplane is a WebUI control for Headscale and is accessible at [https://headplane.example.com/admin/](https://headplane.example.com/admin/)    NOTE: "/" is needed at the end.  

You can generate an API key to connect Headplane to Headscale with:  

``` bash
sudo docker exec -it headscale headscale apikeys create --expiration 999d
```

The API Key can now be used in the Headplane portal:  

``` bash
xRYtN-G.frqhgHAC3jqLMbBqVTTRwAs2lWxSTeHr
```

The API Key can be stored in the Headplane configuration so its always used without prompting:

``` bash
vi headscale-config.yaml
```

Update this section:  

``` bash
  headscale_api_key: "xRYtN-G.frqhgHAC3jqLMbBqVTTRwAs2lWxSTeHr"
```

Restart the MediaStack so the configuration file is copied to the correct locaton:  

``` bash
./restart.sh
```

</br>

### Additional Support for Headscale / Tailscale / Headplane

You can head over to any of the websites for futher configuration details, or connect to the Discord server and discuss issues with other users:  

- Headscale: [https://headscale.net/stable](https://headscale.net/stable)  
- Tailscale: [https://tailscale.com](https://tailscale.com)  
- Headplane: [https://github.com/tale/headplane](https://github.com/tale/headplane)  
</br>
- Support Discord: [https://discord.gg/c84AZQhmpx](https://discord.gg/c84AZQhmpx)  

## Internal Container Access (From Home)

Use the "Import Bookmarks - MediaStackGuide Applications (Internal URLs).html" method, and find / replace all of the `localhost` entries with the IP address running Docker in your home network.  

Then import the Bookmarks into your web browser.  

## External Container Access (From Internet)

Use the "Import Bookmarks - MediaStackGuide Applications (External URLs).html" method, and find / replace all of the `YOUR_DOMAIN_NAME` entries with your Internet domain name.  

All of the Docker images / containers in the Docker Compose file, have already been labelled for Traefik, and they will be automatically detected and assigned the correct routing based on the incoming Internet URL, using your domain name.  

Port forward your incoming connections on your home Internet gateway / router, to the IP Address of your computer running Docker, using Ports 80 and 443 - If these are taken, you can use alternate ports using the REVERSE_PROXY_PORT_HTTP(S) settings in the .ENV variable file.  

## Configure Authentik

Adjust Authentik brand:  

- Admin Interface --> System --> Brands --> Edit "authentik-default"  
- Title: MediaStack - Authentik  
- Select "Update"  

Force MFA for all users:  

- Admin Interface --> Flows and Stages --> Stages --> Edit "default-authentication-mfa-validation"  
- Not configured action: Force the user to configure an authenticator  
- Selected Stages: default-authentication-login (User Login Stage)  
- Select "Update"  

## Add Application in Authentik

Create Authentik Application:  

- Admin Interface --> Applications --> Create with Provider  
- Name: Authentik  
- Slug: authentik  
- Launch URL: <https://auth.example.com>  
  - Open in New Tab: No  
- Select "Next"  
- Choose A Provider: Proxy Provider  
- Select "Next"  
- Name: Provider for Authentik  
- Authorization flow: default-provider-authorization-explicit-consent (Authorize Application)  
- Select "Forward auth (domain level)"  
- Authentication URL: <https://auth.example.com>    <-- change to your domain  
- Cookie domain: example.com                        <-- change to your domain  
- Advanced flow settings:  
- Authentication flow: default-authentication-flow (Welcome to authentik!)  
- Select "Next"  
- Configure Bindings - skip this step  
- Select "Next"  
- Select "Submit"  

Add application to outposts:  

- Admin Interface --> Applications --> Outposts  
- Edit: "authentik Embedded Outpost"  
- Update Outpost:  
- Select "Authentik" application in "Available Applications" and move across to "Selected Applications"  
- Select "Update"  

Restart docker stack:  

``` bash
sudo docker compose down
sudo docker compose up -d
```

or  

``` bash
./restart.sh
```

Goto: [https://auth.example.com](https://auth.example.com) <-- change to your domain  

</br>

## Configure CrowdSec

Create a Crowdsec account, and obtain your Crowdsec security engine enrolement key from:  

- [https://app.crowdsec.net/security-engines](https://app.crowdsec.net/security-engines)  

``` bash
sudo docker exec crowdsec cscli console enroll cm1yipaufk0021g1u01fq27s3
sudo docker exec crowdsec cscli collections install crowdsecurity/base-http-scenarios crowdsecurity/http-cve crowdsecurity/linux crowdsecurity/iptables crowdsecurity/sshd crowdsecurity/traefik crowdsecurity/plex
sudo docker exec crowdsec cscli parsers install crowdsecurity/syslog-logs crowdsecurity/iptables-logs crowdsecurity/sshd-logs crowdsecurity/traefik-logs
sudo docker exec crowdsec cscli appsec-configs install crowdsecurity/appsec-default crowdsecurity/generic-rules
sudo docker exec crowdsec cscli appsec-rules install crowdsecurity/base-config
sudo docker exec crowdsec cscli console enable console_management
sudo docker exec crowdsec cscli capi register
sudo docker exec crowdsec cscli bouncers add traefik-bouncer
```

Crowdsec will output the Local API Key (crowdsecLapiKey) for the bouncer:  

``` bash
API key for 'traefik-bouncer':

   8andilX0JKYIu8z+R4imPkIgG+TMdCttAuMaHrsV7ZU

Please keep this key since you will not be able to retrieve it!
```

The CrowdSec Local API Key (crowdsecLapiKey) needs to be added to the Traefik `dynamic.yaml` file  

``` bash
sudo vi traefik-dynamic.yaml
```

``` yaml
          crowdsecLapiKey: 8andilX0JKYIu8z+R4imPkIgG+TMdCttAuMaHrsV7ZU
```

``` bash
./restart
```

You must go back to [https://app.crowdsec.net/security-engines](https://app.crowdsec.net/security-engines) and approve registration of the new CrowdSec docker engine into the online portal.  

Check the status of Crowdsec components:  

``` bash
sudo docker exec crowdsec cscli console status
sudo docker exec crowdsec cscli collections list
sudo docker exec crowdsec cscli parsers list
sudo docker exec crowdsec cscli bouncers list
sudo docker exec crowdsec cscli alerts list

sudo docker exec crowdsec cscli appsec-configs list
sudo docker exec crowdsec cscli appsec-rules list
```

Crowdsec will display the following output:  

``` bash
+--------------------+-----------+------------------------------------------------------+
| Option Name        | Activated | Description                                          |
+--------------------+-----------+------------------------------------------------------+
| custom             | ✅        | Forward alerts from custom scenarios to the console  |
| manual             | ✅        | Forward manual decisions to the console              |
| tainted            | ✅        | Forward alerts from tainted scenarios to the console |
| context            | ✅        | Forward context with alerts to the console           |
| console_management | ✅        | Receive decisions from console                       |
+--------------------+-----------+------------------------------------------------------+
-------------------------------------------------------------------------------------------------------------
 COLLECTIONS                                                                                                 
-------------------------------------------------------------------------------------------------------------
 Name                               📦 Status    Version  Local Path                                         
-------------------------------------------------------------------------------------------------------------
 crowdsecurity/base-http-scenarios  ✔️  enabled  1.0      /etc/crowdsec/collections/base-http-scenarios.yaml 
 crowdsecurity/http-cve             ✔️  enabled  2.9      /etc/crowdsec/collections/http-cve.yaml            
 crowdsecurity/iptables             ✔️  enabled  0.2      /etc/crowdsec/collections/iptables.yaml            
 crowdsecurity/linux                ✔️  enabled  0.2      /etc/crowdsec/collections/linux.yaml               
 crowdsecurity/plex                 ✔️  enabled  0.1      /etc/crowdsec/collections/plex.yaml                
 crowdsecurity/sshd                 ✔️  enabled  0.5      /etc/crowdsec/collections/sshd.yaml                
 crowdsecurity/traefik              ✔️  enabled  0.1      /etc/crowdsec/collections/traefik.yaml             
-------------------------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------------------------
 PARSERS                                                                                                      
--------------------------------------------------------------------------------------------------------------
 Name                            📦 Status    Version  Local Path                                             
--------------------------------------------------------------------------------------------------------------
 crowdsecurity/cri-logs          ✔️  enabled  0.1      /etc/crowdsec/parsers/s00-raw/cri-logs.yaml            
 crowdsecurity/dateparse-enrich  ✔️  enabled  0.2      /etc/crowdsec/parsers/s02-enrich/dateparse-enrich.yaml 
 crowdsecurity/docker-logs       ✔️  enabled  0.1      /etc/crowdsec/parsers/s00-raw/docker-logs.yaml         
 crowdsecurity/geoip-enrich      ✔️  enabled  0.5      /etc/crowdsec/parsers/s02-enrich/geoip-enrich.yaml     
 crowdsecurity/http-logs         ✔️  enabled  1.3      /etc/crowdsec/parsers/s02-enrich/http-logs.yaml        
 crowdsecurity/iptables-logs     ✔️  enabled  0.5      /etc/crowdsec/parsers/s01-parse/iptables-logs.yaml     
 crowdsecurity/plex-allowlist    ✔️  enabled  0.2      /etc/crowdsec/parsers/s02-enrich/plex-allowlist.yaml   
 crowdsecurity/sshd-logs         ✔️  enabled  2.9      /etc/crowdsec/parsers/s01-parse/sshd-logs.yaml         
 crowdsecurity/syslog-logs       ✔️  enabled  0.8      /etc/crowdsec/parsers/s00-raw/syslog-logs.yaml         
 crowdsecurity/traefik-logs      ✔️  enabled  0.9      /etc/crowdsec/parsers/s01-parse/traefik-logs.yaml      
 crowdsecurity/whitelists        ✔️  enabled  0.3      /etc/crowdsec/parsers/s02-enrich/whitelists.yaml       
--------------------------------------------------------------------------------------------------------------
-----------------------------------------------------------------------------
 Name             IP Address  Valid  Last API pull  Type  Version  Auth Type 
-----------------------------------------------------------------------------
 traefik-bouncer              ✔️                                   api-key   
-----------------------------------------------------------------------------
No active alerts
------------------------------------------------------------------------------------------------------
 APPSEC-CONFIGS                                                                                       
------------------------------------------------------------------------------------------------------
 Name                          📦 Status    Version  Local Path                                       
------------------------------------------------------------------------------------------------------
 crowdsecurity/appsec-default  ✔️  enabled  0.2      /etc/crowdsec/appsec-configs/appsec-default.yaml 
 crowdsecurity/generic-rules   ✔️  enabled  0.3      /etc/crowdsec/appsec-configs/generic-rules.yaml  
------------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------
 APPSEC-RULES                                                                                 
----------------------------------------------------------------------------------------------
 Name                       📦 Status    Version  Local Path                                  
----------------------------------------------------------------------------------------------
 crowdsecurity/base-config  ✔️  enabled  0.1      /etc/crowdsec/appsec-rules/base-config.yaml 
----------------------------------------------------------------------------------------------
```

---

See you on [Reddit for MediaStack](https://www.reddit.com/r/MediaStack/)  

---
