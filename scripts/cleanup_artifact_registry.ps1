param (
    [Parameter(Mandatory=$true)][string]$Project,
    [Parameter(Mandatory=$true)][string]$Region,
    [string]$Repository = "cloud-run-source-deploy",
    [string]$Service = "jp-saas-app",
    [int]$Keep = 3
)

$ErrorActionPreference = "Continue"

Write-Host "`n[Limpeza Artifact Registry] Iniciando..." -ForegroundColor Cyan

$imagePath = "$Region-docker.pkg.dev/$Project/$Repository/$Service"
Write-Host "Repositório: $imagePath" -ForegroundColor Yellow
Write-Host "Mantendo as $Keep imagens mais recentes..." -ForegroundColor Yellow

# Obter digests ordenados por CREATE_TIME descendente (mais recentes primeiro)
$output = gcloud artifacts docker images list $imagePath --sort-by="~CREATE_TIME" --format="value(version)" 2>$null

# Filtra apenas as linhas que começam com sha256:
$digests = @($output -split "`n" | Where-Object { $_.Trim() -match "^sha256:" } | ForEach-Object { $_.Trim() })

if ($null -eq $digests) {
    Write-Host "Nenhuma imagem encontrada em $imagePath ou erro ao consultar." -ForegroundColor Yellow
    exit 0
}

# Converte para array se não for
if ($digests -isnot [array]) {
    $digests = @($digests -split "`n" | Where-Object { $_.Trim() -ne "" })
}

$totalImages = $digests.Count
Write-Host "Total de imagens encontradas: $totalImages"

if ($totalImages -le $Keep) {
    Write-Host "Quantidade de imagens ($totalImages) é menor ou igual ao limite ($Keep). Nenhuma limpeza necessária." -ForegroundColor Green
    exit 0
}

$digestsToDelete = $digests | Select-Object -Skip $Keep

$deleteCount = $digestsToDelete.Count
Write-Host "Imagens a deletar: $deleteCount" -ForegroundColor Yellow

foreach ($digest in $digestsToDelete) {
    $fullImagePath = "${imagePath}@${digest}"
    Write-Host "Deletando $digest ..."
    gcloud artifacts docker images delete $fullImagePath --delete-tags --quiet 2>$null
}

Write-Host "[Limpeza Artifact Registry] Concluído com sucesso!" -ForegroundColor Green
