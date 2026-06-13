# ============================================================
#  status.ps1 — Show health of all ELK lab services
# ============================================================
$ROOT     = $PSScriptRoot
$ENV_FILE = "$ROOT\.env"

function Load-Env {
    $h = @{}
    Get-Content $ENV_FILE | Where-Object { $_ -match '^\s*[^#]\S+=\S' } | ForEach-Object {
        $k,$v = ($_ -split '=',2)
        $h[$k.Trim()] = ($v -split '#')[0].Trim()
    }
    return $h
}
$e = Load-Env

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  ELK Lab — Status" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Container status
Write-Host ""
Write-Host "Containers:" -ForegroundColor White
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" |
    Select-String "elasticsearch|logstash|kibana|webapp|^db|filebeat"

# Elasticsearch health
Write-Host ""
Write-Host "Elasticsearch cluster health:" -ForegroundColor White
try {
    $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("elastic:$($e['ELASTIC_PASSWORD'])"))
    $r = Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" -Headers @{ Authorization="Basic $cred" }
    $color = if ($r.status -eq "green") { "Green" } elseif ($r.status -eq "yellow") { "Yellow" } else { "Red" }
    Write-Host "  Status : $($r.status)" -ForegroundColor $color
    Write-Host "  Shards : active=$($r.active_shards)  unassigned=$($r.unassigned_shards)"
} catch { Write-Host "  Cannot reach Elasticsearch (is it running?)" -ForegroundColor Red }

# Logstash pipeline stats
Write-Host ""
Write-Host "Logstash pipeline:" -ForegroundColor White
try {
    $ls = Invoke-RestMethod -Uri "http://localhost:9600/_node/stats"
    $ev = $ls.pipelines.main.events
    $lsColor = if ($ls.status -eq "green") { "Green" } else { "Yellow" }
    Write-Host "  Status    : $($ls.status)" -ForegroundColor $lsColor
    Write-Host "  Events in : $($ev.'in')"
    Write-Host "  Events out: $($ev.out)"
    Write-Host "  Filtered  : $($ev.filtered)"
} catch { Write-Host "  Cannot reach Logstash API (port 9600)" -ForegroundColor DarkYellow }

# Webapp health
Write-Host ""
Write-Host "Web application:" -ForegroundColor White
try {
    $wa = Invoke-RestMethod -Uri "http://localhost:8080/api/health"
    $color = if ($wa.status -eq "ok") { "Green" } else { "Yellow" }
    Write-Host "  Status: $($wa.status)  |  DB: $($wa.db)" -ForegroundColor $color
} catch { Write-Host "  Cannot reach webapp (is it running?)" -ForegroundColor Red }

# Index summary
Write-Host ""
Write-Host "Indices:" -ForegroundColor White
try {
    $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("elastic:$($e['ELASTIC_PASSWORD'])"))
    $indices = Invoke-RestMethod -Uri "http://localhost:9201/_cat/indices?h=index,docs.count,store.size&s=index" `
        -Headers @{ Authorization="Basic $cred" }
    ($indices -split "`n") | Where-Object { $_ -match "logs-|syslog-" } |
        ForEach-Object { Write-Host "  $_" }
} catch {}

Write-Host ""
Write-Host "Access:" -ForegroundColor White
Write-Host "  Kibana        : http://localhost:5602     (elastic / $($e['ELASTIC_PASSWORD']))"
Write-Host "  Web App       : http://localhost:8080     (admin / Admin@2024!)"
Write-Host "  Elasticsearch : http://localhost:9201"
Write-Host "  Logstash Beats: $($e['SIEM_HOST']):5044  (LAN agents)"
Write-Host ""
