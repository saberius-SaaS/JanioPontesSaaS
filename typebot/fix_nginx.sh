#!/bin/bash

# Configurando Nginx para app.bot.janiopontes.com.br
cat > /etc/nginx/sites-available/app.bot.janiopontes.com.br <<'EOF'
server {
    server_name app.bot.janiopontes.com.br;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Configurando Nginx para bot.janiopontes.com.br
cat > /etc/nginx/sites-available/bot.janiopontes.com.br <<'EOF'
server {
    server_name bot.janiopontes.com.br;
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Habilitando sites
ln -sf /etc/nginx/sites-available/app.bot.janiopontes.com.br /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/bot.janiopontes.com.br /etc/nginx/sites-enabled/

# Testando e reiniciando
nginx -t && systemctl restart nginx && echo "Nginx OK!"

# Gerando certificados SSL
certbot --nginx -d app.bot.janiopontes.com.br -d bot.janiopontes.com.br --non-interactive --agree-tos -m janiopontes@janiopontes.com.br
