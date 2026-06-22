#!/bin/bash

cd /opt/typebot

cat > docker-compose.yml <<'EOF'
services:
  typebot-db:
    image: postgres:13
    restart: always
    environment:
      - POSTGRES_DB=typebot
      - POSTGRES_PASSWORD=typebot_strong_password
    volumes:
      - typebot_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  typebot-builder:
    image: baptistearno/typebot-builder:latest
    restart: always
    depends_on:
      typebot-db:
        condition: service_healthy
    ports:
      - "8080:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:typebot_strong_password@typebot-db:5432/typebot
      - NEXTAUTH_URL=https://app.bot.janiopontes.com.br
      - NEXT_PUBLIC_VIEWER_URL=https://bot.janiopontes.com.br
      - ENCRYPTION_SECRET=K9mP2vL8xQ4wN7jR3yT6uA1cF5hB0dEg
      - ADMIN_EMAIL=janiopontes@janiopontes.com.br
      - GOOGLE_CLIENT_ID=471313311249-sda2g2e9m40l6ui02m1vut9i3glgu40m.apps.googleusercontent.com
      - GOOGLE_CLIENT_SECRET=GOCSPX-XXXXX_XXXXX

  typebot-viewer:
    image: baptistearno/typebot-viewer:latest
    restart: always
    depends_on:
      typebot-db:
        condition: service_healthy
    ports:
      - "8081:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:typebot_strong_password@typebot-db:5432/typebot
      - NEXT_PUBLIC_VIEWER_URL=https://bot.janiopontes.com.br

volumes:
  typebot_db_data:
EOF

docker-compose down
docker-compose up -d
echo "Typebot atualizado com Google OAuth!"
