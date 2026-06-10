$cmd = "cd /home/janiopontes && docker-compose exec -T rails bundle exec rails runner `"app = PlatformApp.find_or_create_by(name: 'JanioPontes SaaS'); puts 'PLATFORM_TOKEN=' + app.access_token`""
$bytes = [System.Text.Encoding]::UTF8.GetBytes($cmd)
$b64 = [Convert]::ToBase64String($bytes)
gcloud compute ssh chatwoot-server --project=jp-saas-producao --zone=southamerica-east1-a --command="sudo bash -c `"echo $b64 | base64 -d | bash`""
