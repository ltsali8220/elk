# ============================================================
#  Install Winlogbeat on THIS Windows PC
#  Run as Administrator in PowerShell
# ============================================================
param(
    [string]$SiemIp    = "127.0.0.1",
    [string]$KibanaPort = "5602",
    [string]$ElasticPass = "ElkLab@2024",
    [string]$Version    = "8.13.4"
)

$InstallDir = "C:\Program Files\Winlogbeat"

Write-Host "[1/4] Downloading Winlogbeat $Version..." -ForegroundColor Cyan
$zip = "$env:TEMP\winlogbeat.zip"
Invoke-WebRequest -Uri "https://artifacts.elastic.co/downloads/beats/winlogbeat/winlogbeat-$Version-windows-x86_64.zip" -OutFile $zip

Write-Host "[2/4] Extracting..." -ForegroundColor Cyan
Expand-Archive -Path $zip -DestinationPath $env:TEMP -Force
$src = "$env:TEMP\winlogbeat-$Version-windows-x86_64"
Copy-Item -Path "$src\*" -Destination $InstallDir -Recurse -Force

Write-Host "[3/4] Writing config..." -ForegroundColor Cyan
$cfg = @"
winlogbeat.event_logs:
  - name: Application
    ignore_older: 72h
  - name: System
    ignore_older: 72h
  - name: Security
    ignore_older: 72h
    event_id: 4624,4625,4634,4647,4648,4672,4688,4689,4720,4722,4725,4726,4776
  - name: Microsoft-Windows-PowerShell/Operational
    ignore_older: 72h
    event_id: 400,403,600,800,4103,4104,4105,4106
  - name: Microsoft-Windows-Windows Defender/Operational
    ignore_older: 72h

processors:
  - add_host_metadata: ~

output.logstash:
  hosts: ["${SiemIp}:5044"]

setup.kibana:
  host: "${SiemIp}:${KibanaPort}"
  username: "elastic"
  password: "${ElasticPass}"

logging.level: info
logging.to_files: true
logging.files:
  path: C:\ProgramData\winlogbeat\logs
  name: winlogbeat
  keepfiles: 7
"@
$cfg | Set-Content -Encoding utf8 "$InstallDir\winlogbeat.yml"

Write-Host "[4/4] Installing and starting service..." -ForegroundColor Cyan
Push-Location $InstallDir
& ".\install-service-winlogbeat.ps1"
Start-Service winlogbeat
Pop-Location

Write-Host "Done! Windows logs flowing to Logstash at ${SiemIp}:5044" -ForegroundColor Green
Write-Host "Kibana: http://localhost:${KibanaPort}  ->  create index pattern: windows-logs-*"
