#!/bin/bash
set -e

ENV_FILE="/home/janiopontes/.env"

# Fix RAILS_ENV to production
sed -i 's|^RAILS_ENV=development|RAILS_ENV=production|' "$ENV_FILE"

# Add FRONTEND_URL if missing
if ! grep -q "^FRONTEND_URL=" "$ENV_FILE"; then
  echo "FRONTEND_URL=https://chat.janiopontes.com.br" >> "$ENV_FILE"
fi

# Add POSTGRES_DATABASE if missing
if ! grep -q "^POSTGRES_DATABASE=" "$ENV_FILE"; then
  sed -i 's|^# POSTGRES_DATABASE=.*|POSTGRES_DATABASE=chatwoot_production|' "$ENV_FILE"
fi

# Create the database and run migrations
cd /home/janiopontes
docker-compose run --rm rails bundle exec rails db:create
docker-compose run --rm rails bundle exec rails db:migrate
docker-compose run --rm rails bundle exec rails db:seed

# Restart everything
docker-compose down
docker-compose up -d

echo "CHATWOOT SETUP COMPLETE"
