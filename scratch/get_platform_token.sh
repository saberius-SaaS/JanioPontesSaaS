#!/bin/bash
cd /home/janiopontes
docker-compose exec -T rails bundle exec rails runner "app = PlatformApp.find_or_create_by(name: 'JanioPontes SaaS'); puts '==TOKEN_START=='; puts app.access_token; puts '==TOKEN_END=='"
