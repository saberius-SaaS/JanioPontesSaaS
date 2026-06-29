#!/bin/bash
# 
# Script de provisionamento do Google Cloud Scheduler (Etapa 7.3)
# Configura as automações e tarefas em segundo plano para chamar a API FastAPI.
# 
# Requisitos:
# - gcloud CLI instalada e autenticada
# - API do Cloud Scheduler ativada no projeto do GCP

PROJECT_ID="jp-saas-producao"
LOCATION="southamerica-east1"
SERVICE_URL="https://app.janiopontes.com.br"
SERVICE_ACCOUNT="jpsaas-backend@jp-saas-producao.iam.gserviceaccount.com"

# 1. Job Diário: Varredura de Atrasos (Roda todos os dias às 00:01)
gcloud scheduler jobs create http job-check-overdue \
    --schedule="1 0 * * *" \
    --uri="${SERVICE_URL}/scheduler/check-overdue" \
    --http-method=POST \
    --headers="X-Scheduler-Key=jp-saas-cron-key-8a7b6c5d4e3f" \
    --time-zone="America/Sao_Paulo" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --oidc-service-account-email="${SERVICE_ACCOUNT}" \
    --description="Varre os protocolos e marca tarefas vencidas como ATRASADO"

# 2. Job Diário: Relatório da Gerência (Roda todos os dias úteis (Seg-Sex) às 18:00)
gcloud scheduler jobs create http job-daily-report \
    --schedule="0 18 * * 1-5" \
    --uri="${SERVICE_URL}/scheduler/daily-report" \
    --http-method=POST \
    --headers="X-Scheduler-Key=jp-saas-cron-key-8a7b6c5d4e3f" \
    --time-zone="America/Sao_Paulo" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --oidc-service-account-email="${SERVICE_ACCOUNT}" \
    --description="Gera e envia o relatório diário de operações para a gerência"

# 3. Job Diário: Lembrete de Protocolos (Roda todos os dias às 09:00)
gcloud scheduler jobs create http job-whatsapp-reminders \
    --schedule="0 9 * * *" \
    --uri="${SERVICE_URL}/scheduler/whatsapp-reminders" \
    --http-method=POST \
    --headers="X-Scheduler-Key=jp-saas-cron-key-8a7b6c5d4e3f" \
    --time-zone="America/Sao_Paulo" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --oidc-service-account-email="${SERVICE_ACCOUNT}" \
    --description="Envia lembrete de protocolos pendentes via WhatsApp"

# 4. Job Mensal: Gerador de Tarefas Automáticas (Roda todo dia 1º do mês às 01:00)
gcloud scheduler jobs create http job-run-engine \
    --schedule="0 1 1 * *" \
    --uri="${SERVICE_URL}/scheduler/run-engine" \
    --http-method=POST \
    --headers="X-Scheduler-Key=jp-saas-cron-key-8a7b6c5d4e3f" \
    --time-zone="America/Sao_Paulo" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --oidc-service-account-email="${SERVICE_ACCOUNT}" \
    --description="Gera as tarefas mensais de todos os clientes baseadas no catálogo de regras"

echo "Jobs do Cloud Scheduler criados com sucesso."
