#!/bin/bash
awk '/location \/ \{/ {
    print "    location /typebot-webhook {"
    print "        proxy_pass http://127.0.0.1:8002/webhook;"
    print "    }"
}
{ print }' /etc/nginx/sites-available/app.bot.janiopontes.com.br > /tmp/nginx_temp
sudo mv /tmp/nginx_temp /etc/nginx/sites-available/app.bot.janiopontes.com.br
sudo nginx -t && sudo systemctl reload nginx

docker exec janiopontes-rails-1 bundle exec rails c << 'EOF'
bot = AgentBot.find_by(name: 'Typebot')
bot.update!(outgoing_url: 'https://app.bot.janiopontes.com.br/typebot-webhook')
EOF
