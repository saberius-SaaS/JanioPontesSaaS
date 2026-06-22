$Project = "jp-saas-producao"
$Zone = "southamerica-east1-a"
$Instance = "chatwoot-server"

Write-Host "1. Preparando arquivos temporarios e copiando..."
# Enviando para a pasta /tmp que sempre tem permissão e evita bugs do Windows/pscp com o sinal ~
gcloud compute scp "g:\Meu Drive\JanioPontesSaas\typebot\docker-compose.yml" ${Instance}:/tmp/docker-compose.yml --project=$Project --zone=$Zone

Write-Host "2. Configurando servidor remoto..."
$SetupScript = @"
# Criando pasta definitiva no servidor
sudo mkdir -p /opt/typebot
sudo mv /tmp/docker-compose.yml /opt/typebot/docker-compose.yml
cd /opt/typebot

# Iniciando Typebot
sudo docker-compose up -d

# Configurando Nginx para app.bot
sudo bash -c 'cat > /etc/nginx/sites-available/app.bot.janiopontes.com.br <<EOF
server {
    server_name app.bot.janiopontes.com.br;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade `$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF'

# Configurando Nginx para bot
sudo bash -c 'cat > /etc/nginx/sites-available/bot.janiopontes.com.br <<EOF
server {
    server_name bot.janiopontes.com.br;
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade `$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF'

# Habilitando sites e reiniciando Nginx
sudo ln -sf /etc/nginx/sites-available/app.bot.janiopontes.com.br /etc/nginx/sites-enabled/
sudo ln -sf /etc/nginx/sites-available/bot.janiopontes.com.br /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# Gerando Certificados SSL
sudo certbot --nginx -d app.bot.janiopontes.com.br -d bot.janiopontes.com.br --non-interactive --agree-tos -m janiopontes@janiopontes.com.br
"@

# Salvando script localmente para executar remotamente
$SetupScript | Out-File -FilePath "setup_remote.sh" -Encoding ascii
gcloud compute scp "setup_remote.sh" ${Instance}:/tmp/setup_typebot.sh --project=$Project --zone=$Zone

Write-Host "3. Executando instalação no servidor..."
gcloud compute ssh $Instance --project=$Project --zone=$Zone --command="sudo bash /tmp/setup_typebot.sh"

Remove-Item "setup_remote.sh"
Write-Host "🚀 Typebot instalado e configurado com sucesso!"
