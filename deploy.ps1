$ErrorActionPreference = "Stop"

$ADMIN_ACCOUNT = "janiopontes@janiopontes.com.br"
$GCP_PROJECT   = "jp-saas-producao"
$CLOUDRUN_SVC  = "jp-saas-app"
$CLOUDRUN_REGION = "southamerica-east1"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "INICIANDO DEPLOY - Janio Pontes SaaS"      -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# ─────────────────────────────────────────
# [1/5] Ambiente Python
# ─────────────────────────────────────────
Write-Host "`n[1/5] Verificando ambiente Python..." -ForegroundColor Yellow
if (Test-Path ".\venv\Scripts\activate.ps1") {
    . .\venv\Scripts\activate.ps1
} else {
    Write-Host "Ambiente virtual nao encontrado. Execute 'python -m venv venv' primeiro." -ForegroundColor Red
    exit 1
}

# ─────────────────────────────────────────
# [2/5] Testes automatizados
# ─────────────────────────────────────────
Write-Host "`n[2/5] Rodando bateria de testes..." -ForegroundColor Yellow
Remove-Item test.db -ErrorAction SilentlyContinue
pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nTESTES FALHARAM! Deploy cancelado para proteger producao." -ForegroundColor Red
    Write-Host "Corrija os erros acima antes de tentar novamente." -ForegroundColor Red
    exit 1
}
Write-Host "Todos os testes passaram!" -ForegroundColor Green

# ─────────────────────────────────────────
# [3/5] Git commit e push
# ─────────────────────────────────────────
Write-Host "`n[3/5] Salvando alteracoes no Git..." -ForegroundColor Yellow
$commitMessage = "update: Deploy automatico via script - $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')"
git add .
$gitStatus = git status --porcelain
if ($gitStatus) {
    git commit -m "$commitMessage"
    git push origin main
    Write-Host "Codigo enviado ao GitHub!" -ForegroundColor Green
} else {
    Write-Host "Nenhuma alteracao para commitar. Continuando..." -ForegroundColor Yellow
}

# ─────────────────────────────────────────
# [4/5] Autenticacao no GCP
# ─────────────────────────────────────────
Write-Host "`n[4/5] Verificando autenticacao no Google Cloud..." -ForegroundColor Yellow

$currentAccount = (gcloud config get-value account 2>$null).Trim()
$tokenValid = $false

if ($currentAccount -eq $ADMIN_ACCOUNT) {
    # Testa se o token atual ainda é válido
    gcloud auth print-access-token 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $tokenValid = $true
        Write-Host "Autenticacao ativa confirmada para $ADMIN_ACCOUNT" -ForegroundColor Green
    } else {
        Write-Host "Token expirado para $ADMIN_ACCOUNT. Sera necessario logar novamente." -ForegroundColor Yellow
    }
}

if (-not $tokenValid) {
    Write-Host "O browser sera aberto para login. Faca login com $ADMIN_ACCOUNT" -ForegroundColor Cyan
    gcloud auth login $ADMIN_ACCOUNT --update-adc
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Falha na autenticacao. Abortando deploy." -ForegroundColor Red
        exit 1
    }
}

# Garantir projeto correto
gcloud config set project $GCP_PROJECT --quiet
Write-Host "Projeto GCP configurado: $GCP_PROJECT" -ForegroundColor Green

# ─────────────────────────────────────────
# [5/5] Deploy no Cloud Run
# ─────────────────────────────────────────
Write-Host "`n[5/5] Publicando no Google Cloud Run..." -ForegroundColor Yellow

gcloud run deploy $CLOUDRUN_SVC `
    --source . `
    --region $CLOUDRUN_REGION `
    --allow-unauthenticated `
    --set-env-vars="ENVIRONMENT=production,DB_USER=app_user,DB_NAME=postgres,DB_HOST=/cloudsql/jp-saas-producao:southamerica-east1:jpsaas-db,GOOGLE_CLIENT_ID=471313311249-sda2g2e9m40l6ui02m1vut9i3glgu40m.apps.googleusercontent.com,EMAIL_MODE=intercept,EMAIL_INTERCEPT_ADDRESS=janiopontes@janiopontes.com.br,DRIVE_MODE=production,GCS_BUCKET_NAME=janio-pontes-saas-docs" `
    --set-secrets="DB_PASSWORD=JPSAAS_DB_PASSWORD:latest,SECRET_KEY=JPSAAS_SECRET_KEY:latest,GOOGLE_CLIENT_SECRET=JPSAAS_GOOGLE_CLIENT_SECRET:latest,/secrets/credentials.json=JPSAAS_GCP_CREDENTIALS:latest" `
    --add-cloudsql-instances="jp-saas-producao:southamerica-east1:jpsaas-db" `
    --quiet

if ($LASTEXITCODE -eq 0) {
    $url = (gcloud run services describe $CLOUDRUN_SVC --region $CLOUDRUN_REGION --format="value(status.url)" 2>$null)
    Write-Host "`n==========================================" -ForegroundColor Green
    Write-Host "DEPLOY CONCLUIDO COM SUCESSO!"             -ForegroundColor Green
    Write-Host "URL: $url"                                 -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Host "`nErro durante o deploy no Cloud Run." -ForegroundColor Red
    exit 1
}
