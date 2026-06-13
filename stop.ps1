# ============================================================
#  stop.ps1 — Stop all ELK lab containers (data is preserved)
#  .\stop.ps1
# ============================================================
$ROOT     = $PSScriptRoot
$ENV_FILE = "$ROOT\.env"

Write-Host ""
Write-Host "Stopping webapp..." -ForegroundColor Yellow
Push-Location "$ROOT\docker\webapp"
docker compose --env-file $ENV_FILE stop 2>&1 | Out-Null
Pop-Location

Write-Host "Stopping ELK stack..." -ForegroundColor Yellow
Push-Location "$ROOT\docker\elk"
docker compose --env-file $ENV_FILE stop 2>&1 | Out-Null
Pop-Location

Write-Host ""
Write-Host "All containers stopped. Data volumes are preserved." -ForegroundColor Green
Write-Host "Run .\run.ps1 to start again." -ForegroundColor Cyan
