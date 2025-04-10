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
- Copy `traefik.yaml` file to `FOLDER_FOR_DATA/traefik`  
- Create empty file called `FOLDER_FOR_DATA/traefik/letsencrypt/acme.json`  
- Change permissions to `600` on `acme.json` file  
- Update the `.env` file with all your settings / values from your existing `docker-compose.env` file - if you have an earlier version of MediaStack running  
- Replace `example.com` with your Internet domain in the `dynamic.yaml` and `traefik.yaml` files
- Set cookie_secret in `headplane.yaml` using 32 random characters

Start:     `sudo docker compose up -d`  
Stop:      `sudo docker compose down`  

The upgrade all running containers:  

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

Enter your home Headscale URL: https://headscale.example.com

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

Headplane is a WebUI control for Headscale and is accessible at https://headscale.example.com

You can generate an API key to connect Headplane to Headscale with:

``` bash
sudo docker exec -it headscale headscale apikeys list
```

### Additional Support for Headscale / Tailscale / Headplane

You can head over to any of the websites for futher configuration details, or connect to the Discord server and discuss issues with other users:

Headscale: [https://headscale.net/stable](https://headscale.net/stable)
Tailscale: [https://tailscale.com](https://tailscale.com)
Headplane: [https://github.com/tale/headplane](https://github.com/tale/headplane)

Support Discord: [https://discord.gg/c84AZQhmpx](https://discord.gg/c84AZQhmpx)

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

---

See you on [Reddit for MediaStack](https://www.reddit.com/r/MediaStack/)

---
