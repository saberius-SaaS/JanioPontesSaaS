$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "INICIANDO DEPLOY - Janio Pontes SaaS " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Ativar ambiente virtual
Write-Host "`n[1/4] Verificando ambiente Python..." -ForegroundColor Yellow
if (Test-Path ".\venv\Scripts\activate.ps1") {
    . .\venv\Scripts\activate.ps1
} else {
    Write-Host "Ambiente virtual nao encontrado. Execute 'python -m venv venv' primeiro." -ForegroundColor Red
    exit 1
}

# Rodar os testes
Write-Host "`n[2/4] Rodando bateria de testes..." -ForegroundColor Yellow
pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nTESTES FALHARAM! O deploy foi cancelado para proteger a producao." -ForegroundColor Red
    Write-Host "Verifique os erros acima e corrija o codigo antes de tentar novamente." -ForegroundColor Red
    exit 1
}
Write-Host "Todos os testes passaram com sucesso!" -ForegroundColor Green

# Commit do codigo
Write-Host "`n[3/4] Salvando alteracoes no Git..." -ForegroundColor Yellow
$commitMessage = Read-Host "Digite a mensagem do commit (ou deixe em branco para update)"
if ([string]::IsNullOrWhiteSpace($commitMessage)) {
    $commitMessage = "update: Deploy manual via script"
}

git add .
git commit -m "$commitMessage"
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nO codigo nao poude ser enviado ao GitHub (pode nao haver alteracoes). O deploy continuara..." -ForegroundColor Yellow
} else {
    Write-Host "Codigo enviado ao GitHub!" -ForegroundColor Green
}

# Fazer Deploy no GCP diretamente (opcional, para nao gastar tokens do GitHub Actions)
Write-Host "`n[4/4] Publicando no Google Cloud Run..." -ForegroundColor Yellow
Write-Host "Voce deseja enviar para o Cloud Run diretamente da sua maquina? (S/N)" -ForegroundColor Cyan
$gcloudDeploy = Read-Host
if ($gcloudDeploy -match "^[Ss]") {
    Write-Host "Iniciando deploy direto no GCP..." -ForegroundColor Yellow
    # Este comando requer o gcloud CLI instalado e autenticado
    gcloud run deploy jp-saas-app --source . --region southamerica-east1 --allow-unauthenticated --set-env-vars ENVIRONMENT=production
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nDEPLOY CONCLUIDO COM SUCESSO NO CLOUD RUN!" -ForegroundColor Green
    } else {
        Write-Host "`nErro durante o deploy no Cloud Run." -ForegroundColor Red
    }
} else {
    Write-Host "`nDEPLOY ENVIADO! O GitHub Actions assumira o processo a partir daqui." -ForegroundColor Green
}
