# Create your certificate appart from kobo
This procedure is useful when you want to generate your own certificates for support api

The idea is to generate the cert files validated by letsencrypt, then you should copy those files to nginx-certbot folder.

This procedure assumes you want to have a separate certificates folder. Otherwise use init-letsencrypt.sh.tpl file and add your support domain there (you wouldn't have a separate certificates folder that way)

## Instructions
- stop container nginxcertbot_nginx_1 (if running) because it holds port 80
- cd ./support-install/nginx-certbot-support/
- Locate file: support.conf on this same directory
- Replace value: "YOUR-PRIVATE-IP" for the value of your current private IP
- Place this file under: support-install/nginx-certbot-support/data/nginx/
- bash init-letsencrypt.sh
- process might ask you to overwrite files, say "y"
- you should have successfully generated files at:
sudo mkdir -p ./YOUR-PATH/nginx-certbot/data/certbot/conf/archive/support.nexion-dev.tk
./support-install/nginx-certbot-support/data/certbot/conf

## Copy your resulting files to Kobo
With above files generated do the following:
- Create folders
`sudo mkdir -p ./YOUR-PATH/nginx-certbot/data/certbot/conf/archive/support.nexion-dev.tk`
`sudo mkdir -p ./YOUR-PATH/nginx-certbot/data/certbot/conf/live/support.nexion-dev.tk`
- Copy files to nginx-certbot
`sudo cp -R ./YOUR-PATH/support-install/nginx-certbot-support/data/certbot/conf/archive/support.nexion-dev.tk/*  ./YOUR-PATH/nginx-certbot/data/certbot/conf/archive/support.nexion-dev.tk`
`sudo cp -R ./YOUR-PATH/support-install/nginx-certbot-support/data/certbot/conf/live/support.nexion-dev.tk/* ./YOUR-PATH/nginx-certbot/data/certbot/conf/live/support.nexion-dev.tk`
- Copy support.conf file to nginx-certbot
`./YOUR-PATH/nginx-certbot/data/nginx`