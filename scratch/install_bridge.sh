#!/bin/bash

echo "Movendo script para /opt..."
sudo mv /tmp/typebot_bridge.py /opt/typebot_bridge.py

echo "Instalando dependências do Python..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv
python3 -m venv /opt/typebot_venv
/opt/typebot_venv/bin/pip install fastapi uvicorn httpx

echo "Criando serviço do sistema..."
cat << 'EOF' | sudo tee /etc/systemd/system/typebot-bridge.service
[Unit]
Description=Typebot Chatwoot Bridge
After=network.target

[Service]
User=root
WorkingDirectory=/opt
ExecStart=/opt/typebot_venv/bin/python3 /opt/typebot_bridge.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable typebot-bridge
sudo systemctl restart typebot-bridge

echo "Configurando AgentBot no Chatwoot..."
# Verificando se Chatwoot está via docker ou linux nativo para usar o Rails console
if docker ps | grep -q chatwoot; then
    docker exec chatwoot bundle exec rails c << 'EOF'
    bot = AgentBot.find_by(name: "Typebot") || AgentBot.create!(name: "Typebot", outgoing_url: "http://127.0.0.1:8002/webhook")
    bot.update!(outgoing_url: "http://127.0.0.1:8002/webhook")
    inbox = Inbox.find_by(id: 1)
    bot.inboxes << inbox if inbox && !bot.inboxes.include?(inbox)
EOF
else
    # Se for instalação linux (cwctl)
    cwctl --console << 'EOF'
    bot = AgentBot.find_by(name: "Typebot") || AgentBot.create!(name: "Typebot", outgoing_url: "http://127.0.0.1:8002/webhook")
    bot.update!(outgoing_url: "http://127.0.0.1:8002/webhook")
    inbox = Inbox.find_by(id: 1)
    bot.inboxes << inbox if inbox && !bot.inboxes.include?(inbox)
EOF
fi

echo "Deploy finalizado!"
