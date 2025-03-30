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

- Download all of the files in the folder  
- Copy `dynamic.yaml` file to `FOLDER_FOR_DATA/traefik`  
- Copy `traefik.yaml` file to `FOLDER_FOR_DATA/traefik`  
- Create empty file called `FOLDER_FOR_DATA/traefik/letsencrypt/acme.json`  
- Change permissions to `600` on `acme.json` file  
- Update the `.env` file with all your settings / values from your existing `docker-compose.env` file - if you have an earlier version of MediaStack running  
- Replace `YOUR_DOMAIN_NAME` with your Internet domain (i.e. example.com) in the `dynamic.yaml` and `traefik.yaml` files

Start:     `sudo docker compose up -d`  
Stop:      `sudo docker compose down`  

The upgrade all running containers:  

- `sudo docker compose pull`  
- `sudo docker compose up -d --force-recreate`  

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
