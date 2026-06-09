#!/bin/bash
# 1. Adicionar FRAME_ANCESTORS no .env do Chatwoot
echo 'FRAME_ANCESTORS="https://app.janiopontes.com.br https://jp-saas-app-471313311249.southamerica-east1.run.app"' >> /home/janiopontes/.env

# 2. Configurar Nginx para remover X-Frame-Options e adicionar CSP
cat > /etc/nginx/sites-enabled/chatwoot << 'NGINX'
server {
  server_name chat.janiopontes.com.br;
  client_max_body_size 50M;

  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Remover X-Frame-Options do Rails e substituir por CSP
    proxy_hide_header X-Frame-Options;
    add_header Content-Security-Policy "frame-ancestors 'self' https://app.janiopontes.com.br https://jp-saas-app-471313311249.southamerica-east1.run.app" always;
  }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/chat.janiopontes.com.br/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/chat.janiopontes.com.br/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}
server {
    if ($host = chat.janiopontes.com.br) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

  server_name chat.janiopontes.com.br;
    listen 80;
    return 404; # managed by Certbot
}
NGINX

# 3. Testar e recarregar Nginx
nginx -t && systemctl reload nginx

# 4. Reiniciar containers do Chatwoot para pegar a nova env
cd /home/janiopontes
docker compose restart
