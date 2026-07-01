# SESSÃO - LEITURA OBRIGATÓRIA (P0)
Modo Token-Saver ativo. Respostas técnicas, diretas e econômicas.

## REGRAS DE CONTEXTO & CÓDIGO
1. Contexto cirúrgico: Não leia arquivos inteiros. Se precisar, peça o trecho/assinatura.
2. Lean Code: Envie apenas linhas alteradas (Git Diff) ou trechos isolados. Use `// ... (código existente)`. Nunca reescreva funções intactas.
3. Gatilhos: Padrão = Apenas código, sem texto. Explicação = usar `-e` ou `/explain`. Documentação = usar `-d` ou `/doc`.
4. Overspending: Se resposta >30 linhas, PARE, resuma em 1 linha e pergunte: "Confirma geração longa?".

## INFRAESTRUTURA (PRODUÇÃO)
- GCP: `jp-saas-producao` | GCS: `janio-pontes-saas-docs-us`
- Cloud Run: `jp-saas-app` (us-east1, port 8080, 2 workers, max 10 inst)
- Cloud SQL: `jp-saas-producao:us-east1:jpsaas-db-us` (PostgreSQL, user: `app_user`, db: `postgres`, via unix socket)
- Domínio: `app.janiopontes.com.br` (Firebase Hosting -> Cloud Run) | Chatwoot: `chat.janiopontes.com.br`
- SA: `jpsaas-backend@jp-saas-producao.iam.gserviceaccount.com`
- Secrets: `JPSAAS_DB_PASSWORD`, `JPSAAS_SECRET_KEY`, `JPSAAS_GOOGLE_CLIENT_SECRET`, `JPSAAS_GCP_CREDENTIALS`
- Email: Gmail delegated (`janiopontes@janiopontes.com.br`, EMAIL_MODE=production)

## CRONJOBS (Cloud Scheduler - southamerica-east1)
- `job-check-overdue` (`1 0 * * *`) -> `/scheduler/check-overdue`
- `job-daily-report` (`0 18 * * 1-5`) -> `/scheduler/daily-report`
- `job-whatsapp-reminders` (`0 9 * * *`) -> `/scheduler/whatsapp-reminders`
- `job-run-engine` (`0 1 1 * *`) -> `/scheduler/run-engine`

## TECH STACK & ESTRUTURA
- Stack: Python 3.12, FastAPI, SQLAlchemy, Alembic, Jinja2, Tailwind v4, Uvicorn
- Ambiente: Entry point `app/main.py` (`app.main:app`), ENVIRONMENT=production
- Diretórios app/: Routers (18 arquivos), Models (11 arquivos), Core (9 arquivos, incl. task_engine e services)
*Nota: Use a indexação da IDE para buscar os nomes exatos de routers/models em app/.*

## DEPLOY
Fluxo: `deploy.ps1` -> testes locais -> git push -> `gcloud run deploy --source .`

## AMBIENTE

- **Entry point**: `app/main.py` → `app.main:app`
- **Este projeto é PRODUÇÃO**. DB via unix socket (`/cloudsql/...`), `EMAIL_MODE=production`, `ENVIRONMENT=production`.
