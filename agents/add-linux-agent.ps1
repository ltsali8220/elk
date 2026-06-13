# ============================================================
#  add-linux-agent.ps1
#  Generates a ready-to-run install command for your Linux machine.
#  Run this on your Windows PC, then paste the output into Linux.
# ============================================================
$ROOT     = Split-Path $PSScriptRoot -Parent
$ENV_FILE = "$ROOT\.env"

$e = @{}
Get-Content $ENV_FILE | Where-Object { $_ -match '^\s*[^#]\S+=\S' } | ForEach-Object {
    $k,$v = ($_ -split '=',2); $e[$k.Trim()] = ($v -split '#')[0].Trim()
}

$SIEM     = $e['SIEM_HOST']
$VER      = $e['ELK_VERSION']
$PASS     = $e['ELASTIC_PASSWORD']
$KPORT    = $e['KIBANA_HOST_PORT']

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Linux Agent Setup" -ForegroundColor Cyan
Write-Host "  SIEM (this PC): $SIEM" -ForegroundColor Cyan
Write-Host "  Logstash port : 5044" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "STEP 1 — Test connectivity from Linux first:" -ForegroundColor Yellow
Write-Host "  nc -zv $SIEM 5044" -ForegroundColor White
Write-Host ""
Write-Host "STEP 2 — Copy the config file to Linux:" -ForegroundColor Yellow
Write-Host "  From Linux run:" -ForegroundColor White
Write-Host "  scp user@$($env:COMPUTERNAME):""C:\Users\Salivan Veerasekaran\apps\ELK\agents\install-filebeat-linux.sh"" ." -ForegroundColor White
Write-Host "  OR copy it manually via USB and run:" -ForegroundColor DarkGray
Write-Host ""
Write-Host "STEP 3 — Run on Linux as root:" -ForegroundColor Yellow
Write-Host "  sudo bash install-filebeat-linux.sh $SIEM" -ForegroundColor Green
Write-Host ""
Write-Host "STEP 4 — Or run this one-liner directly on Linux (no file copy needed):" -ForegroundColor Yellow
Write-Host ""

$oneliner = @"
sudo bash -c '
set -e
curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elastic.gpg
echo "deb [signed-by=/usr/share/keyrings/elastic.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" > /etc/apt/sources.list.d/elastic-8.x.list
apt-get update -qq && apt-get install -y filebeat=${VER}
cat > /etc/filebeat/filebeat.yml << FBEOF
filebeat.inputs:
  - type: log
    enabled: true
    paths: [/var/log/syslog, /var/log/messages]
    fields: {log_type: syslog, host_type: linux-desktop}
    tags: ["syslog"]
  - type: log
    enabled: true
    paths: [/var/log/auth.log, /var/log/secure]
    fields: {log_type: auth, host_type: linux-desktop}
    tags: ["linux_auth"]
  - type: log
    enabled: true
    paths: [/var/log/kern.log]
    fields: {log_type: kernel, host_type: linux-desktop}
    tags: ["kernel"]
filebeat.modules:
  - module: system
    syslog: {enabled: true}
    auth: {enabled: true}
processors:
  - add_host_metadata: ~
output.logstash:
  hosts: ["${SIEM}:5044"]
setup.kibana:
  host: "${SIEM}:${KPORT}"
  username: elastic
  password: ${PASS}
logging.level: info
FBEOF
systemctl enable filebeat && systemctl restart filebeat
systemctl status filebeat --no-pager -l
'
"@

Write-Host $oneliner -ForegroundColor White
Write-Host ""
Write-Host "STEP 5 — In Kibana (http://localhost:$KPORT), create index patterns:" -ForegroundColor Yellow
Write-Host "  Stack Management -> Index Patterns -> Create" -ForegroundColor White
Write-Host "  * syslog-*        (time: @timestamp)" -ForegroundColor Green
Write-Host "  * windows-logs-*  (time: @timestamp)" -ForegroundColor Green
Write-Host "  * webapp-logs-*   (time: @timestamp)" -ForegroundColor Green
Write-Host ""
