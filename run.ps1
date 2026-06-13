# ============================================================
#  run.ps1 — Start the entire ELK lab (ELK + Webapp)
#  Run from the ELK\ root directory:
#    .\run.ps1
# ============================================================
param([switch]$Logs)   # pass -Logs to tail logs after start

$ROOT = $PSScriptRoot
$ENV_FILE = "$ROOT\.env"

function Load-Env {
    $h = @{}
    Get-Content $ENV_FILE | Where-Object { $_ -match '^\s*[^#]\S+=\S' } | ForEach-Object {
        $k,$v = ($_ -split '=',2)
        $h[$k.Trim()] = ($v -split '#')[0].Trim()
    }
    return $h
}

$env_vars = Load-Env
$ELK_VERSION = $env_vars['ELK_VERSION']
$SIEM_HOST   = $env_vars['SIEM_HOST']

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  ELK Lab — Starting all services" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Ensure Docker networks exist ──────────────────
Write-Host "[1/5] Checking Docker networks..." -ForegroundColor Yellow
$elkNet = docker network ls --filter name=elk-net --format "{{.Name}}" 2>$null
if ($elkNet -notmatch "elk-net") {
    docker network create --subnet=172.30.0.0/24 elk-net | Out-Null
    Write-Host "      Created: elk-net" -ForegroundColor Green
} else { Write-Host "      OK: elk-net exists" }

$webNet = docker network ls --filter name=webapp-net --format "{{.Name}}" 2>$null
if ($webNet -notmatch "webapp-net") {
    docker network create --subnet=172.31.0.0/24 webapp-net | Out-Null
    Write-Host "      Created: webapp-net" -ForegroundColor Green
} else { Write-Host "      OK: webapp-net exists" }

# ── Step 2: Start ELK stack ───────────────────────────────
Write-Host ""
Write-Host "[2/5] Starting ELK stack (Elasticsearch, Logstash, Kibana)..." -ForegroundColor Yellow
Push-Location "$ROOT\docker\elk"
docker compose --env-file $ENV_FILE up -d 2>&1 | Where-Object { $_ -match "Container|Error|error" }
Pop-Location

# ── Step 3: Wait for Elasticsearch ───────────────────────
Write-Host ""
Write-Host "[3/5] Waiting for Elasticsearch to be healthy..." -ForegroundColor Yellow
$tries = 0
do {
    Start-Sleep -Seconds 5
    $tries++
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" `
             -Headers @{ Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("elastic:$($env_vars['ELASTIC_PASSWORD'])")) } `
             -ErrorAction Stop
        if ($r.status -in "green","yellow") { break }
    } catch {}
    Write-Host "      Waiting... ($tries)" -ForegroundColor DarkGray
} while ($tries -lt 24)

if ($tries -ge 24) {
    Write-Host "      ERROR: Elasticsearch did not start in time." -ForegroundColor Red
    exit 1
}
Write-Host "      Elasticsearch is $($r.status)" -ForegroundColor Green

# ── Step 4: Seed users (idempotent) ──────────────────────
Write-Host ""
Write-Host "[4/5] Seeding Elasticsearch users..." -ForegroundColor Yellow
$cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("elastic:$($env_vars['ELASTIC_PASSWORD'])"))
$h = @{ Authorization="Basic $cred"; "Content-Type"="application/json" }
$base = "http://localhost:9201"

try {
    Invoke-RestMethod -Method POST -Uri "$base/_security/user/kibana_system/_password" -Headers $h `
        -Body "{`"password`":`"$($env_vars['KIBANA_SYSTEM_PASSWORD'])`"}" | Out-Null
    Invoke-RestMethod -Method PUT -Uri "$base/_security/role/logstash_writer" -Headers $h `
        -Body '{"cluster":["manage_index_templates","monitor"],"indices":[{"names":["webapp-logs-*","windows-logs-*","syslog-*","docker-logs-*","misc-logs-*"],"privileges":["write","create_index","create"]}]}' | Out-Null
    Invoke-RestMethod -Method PUT -Uri "$base/_security/user/logstash_internal" -Headers $h `
        -Body "{`"password`":`"$($env_vars['LOGSTASH_INTERNAL_PASSWORD'])`",`"roles`":[`"logstash_writer`"],`"full_name`":`"Logstash Internal`"}" | Out-Null
    Write-Host "      Users OK" -ForegroundColor Green
} catch {
    Write-Host "      Seed warning (may already exist): $_" -ForegroundColor DarkYellow
}

# ── Step 5: Start webapp ──────────────────────────────────
Write-Host ""
Write-Host "[5/5] Starting webapp (Flask + PostgreSQL + Filebeat sidecar)..." -ForegroundColor Yellow
Push-Location "$ROOT\docker\webapp"
docker compose --env-file $ENV_FILE up -d 2>&1 | Where-Object { $_ -match "Container|Error|error" }
Pop-Location

# ── Summary ───────────────────────────────────────────────
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Kibana       : http://localhost:5602      (elastic / $($env_vars['ELASTIC_PASSWORD']))" -ForegroundColor Cyan
Write-Host "  Web App      : http://localhost:8080      (admin / Admin@2024!)" -ForegroundColor Cyan
Write-Host "  Elasticsearch: http://localhost:9201" -ForegroundColor Cyan
Write-Host "  Logstash     : $($SIEM_HOST):5044  (Beats input from LAN)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Container status:" -ForegroundColor White
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "elasticsearch|logstash|kibana|webapp|db|filebeat"

if ($Logs) {
    Write-Host ""
    Write-Host "Tailing logs (Ctrl+C to stop)..." -ForegroundColor DarkGray
    docker compose --env-file "$ROOT\docker\elk\.env" -f "$ROOT\docker\elk\docker-compose.yml" logs -f
}
