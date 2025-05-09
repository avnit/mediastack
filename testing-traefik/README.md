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
- Copy `headscale-config.yaml` file to `FOLDER_FOR_DATA/headscale` and rename it to `config.yaml`  
- Copy `headplane-config.yaml` file to `FOLDER_FOR_DATA/headplane` and rename it to `config.yaml`  
- Copy `dynamic.yaml` file to `FOLDER_FOR_DATA/traefik`  
- Copy `internal.yaml` file to `FOLDER_FOR_DATA/traefik`  
- Copy `traefik.yaml` file to `FOLDER_FOR_DATA/traefik`  
- Create empty file called `FOLDER_FOR_DATA/traefik/letsencrypt/acme.json`  
- Change permissions to `600` on `acme.json` file  
- Update the `.env` file with all your settings / values from your existing `docker-compose.env` file - if you have an earlier version of MediaStack running  
- Replace `example.com` with your Internet domain in the `headscale/config.yaml`, `headplane/config.yaml`, `traefik/dynamic.yaml`, `traefik/dynamic.yaml` and `traefik/traefik.yaml` files
- Set cookie_secret in `headplane/config.yaml` using 32 random characters

Start:     `sudo docker compose up -d`  
Stop:      `sudo docker compose down`  

To upgrade all running containers:  

- `sudo docker compose pull`  
- `sudo docker compose up -d --force-recreate`  

## Configure Headscale / Tailscale / Headplane

Replace all instances of `example.com` in the configuration files with your own domain name.

> NOTE: Tailscale Authkey can't be set in `.env` file until the Headscale container has been deployed

### Register Tailscale Exit Node with Headscale

Execute these commands once Headscale has been deployed:

``` bash
sudo docker exec -it headscale headscale users create exit-node
sudo docker exec -it headscale headscale --user exit-node preauthkeys create
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
sudo docker exec -it headscale headscale routes list
```

The Headscale routing table will look like this:

``` bash
ID | Node      | Prefix         | Advertised | Enabled | Primary
1  | exit-node | 0.0.0.0/0      | true       | false   | -      
2  | exit-node | ::/0           | true       | false   | -      
3  | exit-node | 192.168.1.0/24 | true       | false   | false  
4  | exit-node | 172.28.10.0/24 | true       | false   | false  
```

Enable IP routing out of the Tailscale exit node with the following command

``` bash
sudo docker exec -it headscale headscale routes enable -r 1 
sudo docker exec -it headscale headscale routes enable -r 2 
sudo docker exec -it headscale headscale routes enable -r 3 
sudo docker exec -it headscale headscale routes enable -r 4 
sudo docker exec -it headscale headscale routes list
```

The IP routes will now be enabled and look like this:

``` bash
ID | Node      | Prefix         | Advertised | Enabled | Primary
1  | exit-node | 0.0.0.0/0      | true       | true    | -      
2  | exit-node | ::/0           | true       | true    | -      
3  | exit-node | 192.168.1.0/24 | true       | true    | true   
4  | exit-node | 172.28.10.0/24 | true       | true    | true   
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
sudo docker exec -it headscale headscale routes list
```

You can now go to the Tailscale application on your phone, and select `Exit Node` --> `exit-node` and turn on `Allow Local Network Access`.

You can also go into the Tailscale application settings on your phone, and turn on `VPN On Demand`, so you always have remote access when away from home.

### WebUI Managed with Headplane

Headplane is a WebUI control for Headscale and is accessible at [https://headplane.example.com/admin/](https://headplane.example.com/admin/)    NOTE: "/" is needed at the end.

You can generate an API key to connect Headplane to Headscale with:

``` bash
sudo docker exec -it headscale headscale apikeys create --expiration 999d
```

### Additional Support for Headscale / Tailscale / Headplane

You can head over to any of the websites for futher configuration details, or connect to the Discord server and discuss issues with other users:

- Headscale: [https://headscale.net/stable](https://headscale.net/stable)  
- Tailscale: [https://tailscale.com](https://tailscale.com)  
- Headplane: [https://github.com/tale/headplane](https://github.com/tale/headplane)  

- Support Discord: [https://discord.gg/c84AZQhmpx](https://discord.gg/c84AZQhmpx)  

## Internal Container Access (From Home)  

Use the "Import Bookmarks - MediaStackGuide Applications (Internal URLs).html" method, and find / replace all of the `localhost` entries with the IP address running Docker in your home network.  

Then import the Bookmarks into your web browser.  

## External Container Access (From Internet)  

Use the "Import Bookmarks - MediaStackGuide Applications (External URLs).html" method, and find / replace all of the `YOUR_DOMAIN_NAME` entries with your Internet domain name.  

All of the Docker images / containers in the Docker Compose file, have already been labelled for Traefik, and they will be automatically detected and assigned the correct routing based on the incoming Internet URL using yoru domain name.

Port forward your incoming connections on your home Internet gateway / router, to the IP Address of your computer running Docker, using Ports 80 and 443 - If these are taken, you can use alternate ports using the REVERSE_PROXY_PORT_HTTP(S) settings in the .ENV variable file.

## Basic User Authentication  

Basic user authentication credentials are set in the .ENV file with the `BASIC_WEB_AUTH=` variable.

To create the password configuration, execute the following command - "username" and "password" values can be updated as you need:

``` bash
echo $(htpasswd -nb username password) | sed -e s/\\$/\\$\\$/g
```

Add the output of the command to the end of the `BASIC_WEB_AUTH` variable:

``` yaml
BASIC_WEB_AUTH=username:$$apr1$$JZIddfg47kO46PfZ$$Z1pqZ1QejEL1xMWSW5yW0
```

Multiple usernames and passwords can be added together by adding them to the end of the other values, see Alice and Bob:

``` yaml
BASIC_WEB_AUTH=alice:$$apr1$$JZIddfg47kO46PfZ$$Z1pqZ1QejEL1xMWSW5yW0:bob:$$apr1$$JZIddfg47kO46PfZ$$Z1pqZ1QejEL1xMWSW5yW0
```

> NOTE: The Basic Web Auth is just that, a simple way to add username / password credentials to your web services; however you will need to log into each service with the same credentials - we will look at introducing SSO authentication soon, so you only need to log into one of your services remotely, then SSO will handle the continued authentication across all other services. But this is a good start.

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
sudo vi $FOLDER_FOR_DATA/traefik/dynamic.yaml
```

``` yaml
          crowdsecLapiKey: 8andilX0JKYIu8z+R4imPkIgG+TMdCttAuMaHrsV7ZU
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

## Configure Authentik  

Adjust Authentik brand:  
    Admin Interface --> System --> Brands --> Edit "authentik-default"  
    Title: MediaStack - Authentik  
    Select "Update"  

Force MFA for all users:  
    Admin Interface --> Flows and Stages --> Stages --> Edit "default-authentication-mfa-validation"  
    Not configured action: Force the user to configure an authenticator  
    Select "Update"  

## Add Application in Authentik  

Create Authentik Application:  
    Admin Interface --> Applications --> Create with Provider  
    Name: Authentik  
    Slug: authentik  
    Select "Next"  
    Choose A Provider: Proxy Provider  
    Select "Next"  
    Name: Provider for Authentik  
    Authorization flow: default-provider-authorization-explicit-consent (Authorize Application)  
    Select "Forward auth (domain level)"  
    Authentication URL: <https://auth.example.com>    <-- change to your domain  
    Cookie domain: example.com                      <-- change to your domain  
    Advanced flow settings:  
    Authentication flow: default-authentication-flow (Welcome to authentik!)  
    Select "Next"  
    Configure Bindings - skip this step  
    Select "Next"  
    Select "Submit"  

Add application to outposts:  
    Admin Interface --> Applications --> Outposts  
    Edit: "authentik Embedded Outpost"  
    Update Outpost:  
    Select "Authentik" application in "Available Applications" and move across to "Selected Applications"  
    Advanced settings:  
        Under "Configuration", ensure authentik_host is <http://authentik:6080>  
    Select "Update"  

Edit `docker-compose.yaml` and make the following adjustments:  

``` yaml
#      - traefik.http.routers.headplane.middlewares=headplane-basicauth@docker,security-headers@file
      - traefik.http.routers.headplane.middlewares=authentik-forwardauth@file,security-headers@file
      # SERVICES
      - traefik.http.services.headplane.loadbalancer.server.scheme=http
      - traefik.http.services.headplane.loadbalancer.server.port=3000
      # MIDDLEWARES
#      - traefik.http.middlewares.headplane-basicauth.basicauth.users=${BASIC_WEB_AUTH:?err}
```

Restart docker stack:  

``` bash
sudo docker compose down
sudo docker compose up -d
```

Goto: [https://auth.example.com](https://auth.example.com) <-- change to your domain

</br>

---

See you on [Reddit for MediaStack](https://www.reddit.com/r/MediaStack/)

---
