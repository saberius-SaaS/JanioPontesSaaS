sudo sed -i 's|add_header X-Frame-Options "SAMEORIGIN" always;|add_header Content-Security-Policy "frame-ancestors https://app.janiopontes.com.br http://localhost:8000";|g' /etc/nginx/sites-enabled/chatwoot
sudo systemctl reload nginx
