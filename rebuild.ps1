# ============================================================
#  rebuild.ps1 — Rebuild and restart the ELK lab
#
#  Options:
#    .\rebuild.ps1              # rebuild webapp only (fast)
#    .\rebuild.ps1 -All         # rebuild + re-pull ALL images
#    .\rebuild.ps1 -Clean       # stop, remove volumes, full rebuild
# ============================================================
param(
    [switch]$All,    # re-pull ELK images too
    [switch]$Clean   # wipe volumes (DESTROYS all data)
)

$ROOT     = $PSScriptRoot
$ENV_FILE = "$ROOT\.env"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  ELK Lab — Rebuild" -ForegroundColor Cyan
if ($Clean) { Write-Host "  Mode: CLEAN (volumes will be wiped)" -ForegroundColor Red }
elseif ($All) { Write-Host "  Mode: Full (re-pull all images)" -ForegroundColor Yellow }
else  { Write-Host "  Mode: Webapp only (fast)" -ForegroundColor Yellow }
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

if ($Clean) {
    Write-Host "[!] Stopping and removing ALL containers and volumes..." -ForegroundColor Red
    Push-Location "$ROOT\docker\webapp"
    docker compose --env-file $ENV_FILE down -v 2>&1 | Out-Null
    Pop-Location
    Push-Location "$ROOT\docker\elk"
    docker compose --env-file $ENV_FILE down -v 2>&1 | Out-Null
    Pop-Location
    Write-Host "    Done. All data wiped." -ForegroundColor Red
    Write-Host ""
}

if ($All -or $Clean) {
    Write-Host "[1/3] Pulling latest ELK images..." -ForegroundColor Yellow
    Push-Location "$ROOT\docker\elk"
    docker compose --env-file $ENV_FILE pull 2>&1 | Where-Object { $_ -match "Pulling|Pulled|up to date" }
    Pop-Location
    Write-Host ""
}

Write-Host "[2/3] Rebuilding webapp image..." -ForegroundColor Yellow
Push-Location "$ROOT\docker\webapp"
docker compose --env-file $ENV_FILE build --no-cache webapp
Pop-Location
Write-Host ""

Write-Host "[3/3] Restarting all services..." -ForegroundColor Yellow
& "$ROOT\run.ps1"
