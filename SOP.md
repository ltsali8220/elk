# Standard Operating Procedure
## ELK Stack SIEM Lab Environment
**Version:** 2.0  |  **Updated:** 2026-06-12  |  **Host:** blackperl (192.168.0.3)

---

## 1. Architecture Overview

```
┌─────────────────────── Windows PC — blackperl (192.168.0.3) ───────────────────────┐
│                                                                                      │
│  ┌──── Docker: elk-net (172.30.0.0/24) ────────┐  ┌── Docker: webapp-net ────────┐  │
│  │                                              │  │  (172.31.0.0/24)             │  │
│  │  elasticsearch  172.30.0.10  :9200→9201      │  │  webapp    172.31.0.10 :8080 │  │
│  │  logstash       172.30.0.11  :5044 :5514     │◄─┤  db        172.31.0.11 :5432 │  │
│  │  kibana         172.30.0.12  :5601→5602      │  │  filebeat  172.31.0.12       │  │
│  │                                              │  │                              │  │
│  └──────────────────────────────────────────────┘  └──────────────────────────────┘  │
│                                                                                      │
│  Winlogbeat (Windows service, native) ──────────────────────► logstash:5044          │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                                   ▲
                Linux Desktop (192.168.0.117)       │
                Filebeat (service) ─────────────────┘
```

### Why Docker on Windows — Not Vagrant

Vagrant + VirtualBox was the original plan. It was abandoned because:
- Docker Desktop uses Hyper-V / WSL2 which activates the Windows Hypervisor Platform
- VirtualBox cannot use hardware virtualization when Hyper-V is active
- The two hypervisors are mutually exclusive on the same machine

Result: ELK runs directly in Docker Compose on the Windows host.

### Index Strategy

| Index           | Contents                        | Source              |
|-----------------|---------------------------------|---------------------|
| `webapp-logs-*` | Flask JSON app logs             | Filebeat sidecar    |
| `windows-logs-*`| Windows Event Logs              | Winlogbeat          |
| `syslog-*`      | Linux syslog, auth.log, kern.log| Filebeat (Linux)    |
| `docker-logs-*` | Docker container stdout/stderr  | Filebeat sidecar    |
| `misc-logs-*`   | Anything untagged               | Fallthrough         |

Daily index rotation: `webapp-logs-2026.06.12`, `windows-logs-2026.06.12`, etc.

---

## 2. IP and Port Reference

| Component         | Container IP  | Host Port | Notes                         |
|-------------------|---------------|-----------|-------------------------------|
| Elasticsearch     | 172.30.0.10   | **9201**  | Default 9200 taken by other project |
| Logstash (Beats)  | 172.30.0.11   | **5044**  | All Beats agents connect here |
| Logstash (TCP)    | 172.30.0.11   | 5000      | Docker JSON logs              |
| Logstash (Syslog) | 172.30.0.11   | 5514      | UDP + TCP syslog              |
| Kibana            | 172.30.0.12   | **5602**  | Default 5601 taken by other project |
| Flask Webapp      | 172.31.0.10   | 8080      |                               |
| PostgreSQL        | 172.31.0.11   | —         | Internal only                 |
| Filebeat sidecar  | 172.31.0.12   | —         | Internal only                 |
| SIEM host LAN     | —             | —         | 192.168.0.3 (Wi-Fi 2 adapter) |
| Linux Desktop LAN | —             | —         | 192.168.0.117                 |

> **Port conflicts:** Another project (`papertrade_local`) already uses 5601 and 9200.
> ELK lab uses 5602 and 9201 to avoid collision.

---

## 3. Prerequisites

| Software         | Notes                                          |
|------------------|------------------------------------------------|
| Docker Desktop   | WSL2 backend. Hyper-V must be enabled.        |
| PowerShell 5+    | Scripts use .NET classes directly              |
| Winlogbeat 8.13.4| Installed natively on Windows host             |
| Filebeat 8.13.4  | Installed on Linux desktop                     |

Minimum host RAM: 16 GB (ELK uses ~6 GB, rest for Windows + other containers)

### Docker Networks

Two custom networks must exist before the containers start. `run.ps1` creates them automatically:

```
elk-net    172.30.0.0/24    — Elasticsearch, Logstash, Kibana
webapp-net 172.31.0.0/24    — Flask app, PostgreSQL, Filebeat sidecar
```

> **Why not 172.20/172.21?** Those subnets were already in use by other Docker Compose
> projects on this machine. Docker refuses to create a conflicting network. Changed to
> 172.30/172.31.

---

## 4. Environment Variables — `.env`

All passwords, IPs, and ports are stored in `ELK\.env`. Edit this before first boot.

```ini
SIEM_HOST=192.168.0.3           # LAN IP of this Windows PC
LINUX_DESKTOP_IP=192.168.0.117  # LAN IP of Linux desktop

ELK_VERSION=8.13.4
ELK_NET_SUBNET=172.30.0.0/24
WEBAPP_NET_SUBNET=172.31.0.0/24

KIBANA_HOST_PORT=5602
ES_HOST_PORT=9201
LOGSTASH_BEATS_PORT=5044

ELASTIC_PASSWORD=ElkLab@2024
KIBANA_SYSTEM_PASSWORD=KibanaLab@2024
LOGSTASH_INTERNAL_PASSWORD=LogstashLab@2024

DB_NAME=webapp
DB_USER=webapp
DB_PASSWORD=WebApp@2024
SECRET_KEY=elk-lab-flask-secret-2024
```

---

## 5. Scripts

| Script         | Purpose                                          |
|----------------|--------------------------------------------------|
| `.\run.ps1`    | Start everything (ELK + Webapp). Waits for ES health, seeds users |
| `.\stop.ps1`   | Stop all containers (data preserved)             |
| `.\status.ps1` | Show container status, ES health, event counts, index list |
| `.\rebuild.ps1`| Rebuild images. `-Clean` wipes volumes. `-All` re-pulls base images |

### run.ps1 — What it does (5 steps)

1. Creates Docker networks `elk-net` and `webapp-net` if they don't exist
2. Starts ELK stack (`docker/elk/docker-compose.yml`)
3. Polls `http://localhost:9201/_cluster/health` until ES is green or yellow
4. Seeds ES users via REST API:
   - Sets `kibana_system` password so Kibana can authenticate
   - Creates role `logstash_writer` (write-only on log indices)
   - Creates user `logstash_internal` with that role (least privilege)
5. Starts webapp stack (`docker/webapp/docker-compose.yml`)

---

## 6. ELK Stack Configuration

### 6.1 Elasticsearch

Config: `docker/elk/elasticsearch/elasticsearch.yml`

```yaml
discovery.type: single-node       # Lab only — no clustering
xpack.security.enabled: true      # Auth required on all connections
network.host: 0.0.0.0
```

Elasticsearch health will always be **YELLOW** in this lab. That is normal and expected.
Yellow = all data is safe, but replica shards cannot be assigned (no second node exists).

Health check:
```powershell
Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" `
  -Headers @{ Authorization = "Basic " + [Convert]::ToBase64String(
    [Text.Encoding]::ASCII.GetBytes("elastic:ElkLab@2024")) }
```

### 6.2 Logstash

Config: `docker/elk/logstash/logstash.yml`

```yaml
http.host: "0.0.0.0"
xpack.monitoring.enabled: false
config.reload.automatic: true     # Hot-reload — no restart needed after edits
config.reload.interval: 30s
```

> **CRITICAL — BOM Warning:** PowerShell's `Set-Content -Encoding utf8` writes a
> UTF-8 BOM (bytes EF BB BF) at the start of every file. Logstash's config parser
> fails immediately with `Expected "input", "filter", "output" at line 1, column 1 (byte 1)`.
>
> Always write Logstash config files using .NET directly:
> ```powershell
> $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
> [System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
> ```

Logstash API (stats + health check):
```powershell
Invoke-RestMethod "http://localhost:9600/_node/stats" | Select-Object status
# Pipeline event counts:
(Invoke-RestMethod "http://localhost:9600/_node/stats").pipelines.main.events
```

Test pipeline syntax (without restarting):
```powershell
docker exec logstash bin/logstash --config.test_and_exit `
  --path.settings /usr/share/logstash/config `
  --path.config /usr/share/logstash/pipeline
```

### 6.3 Kibana

Config: injected as environment variables in `docker/elk/docker-compose.yml`

```yaml
ELASTICSEARCH_USERNAME: kibana_system
ELASTICSEARCH_PASSWORD: ${KIBANA_SYSTEM_PASSWORD}
```

Kibana uses the built-in `kibana_system` user (not `elastic`). The password is set
by `run.ps1` step 4 before Kibana finishes starting up.

URL: `http://localhost:5602` — Login: `elastic` / `ElkLab@2024`

---

## 7. Logstash Pipeline Files

Directory: `docker/elk/logstash/pipeline/`
Hot-reload: every 30 seconds automatically.

All files must be **UTF-8 without BOM**. See warning in §6.2.

### `01-input.conf` — Ingestion sources

```
beats  → port 5044   Winlogbeat (Windows) + Filebeat (Linux + Docker sidecar)
tcp    → port 5000   Docker container JSON logs
syslog → port 5514   Linux syslog (UDP and TCP)
```

### `10-webapp-filter.conf` — Flask app log parsing

Flask writes structured JSON logs. This filter renames fields to Elastic Common Schema (ECS):

| Flask field    | ECS field                        |
|----------------|----------------------------------|
| `user`         | `[user][name]`                   |
| `ip`           | `[client][ip]`                   |
| `method`       | `[http][request][method]`        |
| `path`         | `[url][path]`                    |
| `status_code`  | `[http][response][status_code]`  |
| `action`       | `[event][action]`                |
| `outcome`      | `[event][outcome]`               |
| `duration_ms`  | `[event][duration]`              |

Tags added:
- `login_success` — when `action=login` and `outcome=success`
- `login_failure` — when `action=login` and `outcome=failure`

### `20-syslog-filter.conf` — Linux syslog parsing

Uses Grok to parse RFC3164 syslog format:
```
%{SYSLOGTIMESTAMP} %{SYSLOGHOST} %{DATA:proc}[%{POSINT:pid}]: %{GREEDYDATA:msg}
```

Tag `linux_auth` added when process is: `sshd`, `sudo`, `su`, `login`, `passwd`.

### `30-beats-filter.conf` — Winlogbeat / Filebeat tagging

All Winlogbeat events get tag `windows_security`. Then by event ID:

| Event ID | Tag              | Meaning             |
|----------|------------------|---------------------|
| 4624     | `login_success`  | Successful logon    |
| 4625     | `login_failure`  | Failed logon        |
| 4634     | `logout`         | Logoff              |
| 4647     | `logout`         | User-initiated logoff|
| 4688     | `process_creation`| New process created|
| PowerShell channel | `powershell` | PS script execution |

### `99-output.conf` — Index routing

```
webapp tag       → webapp-logs-YYYY.MM.dd
windows_security → windows-logs-YYYY.MM.dd
syslog/linux_auth→ syslog-YYYY.MM.dd
docker_log       → docker-logs-YYYY.MM.dd
(anything else)  → misc-logs-YYYY.MM.dd
```

Logstash connects to Elasticsearch as `logstash_internal` using env var
`${LOGSTASH_INTERNAL_PASSWORD}` (least-privilege write-only account).

---

## 8. Web Application

### Stack
- Python Flask with structured JSON logging
- PostgreSQL 15 (psycopg2)
- SHA-256 password hashing with per-user salt

### Endpoints

| Method | Path          | Auth  | Description              |
|--------|---------------|-------|--------------------------|
| GET    | `/`           | No    | Redirect to login or dashboard |
| GET/POST | `/login`   | No    | Login form               |
| GET/POST | `/register`| No    | Register new user        |
| GET    | `/logout`     | Yes   | End session              |
| GET    | `/dashboard`  | Yes   | User list + activity     |
| GET    | `/api/health` | No    | JSON health check        |
| GET    | `/api/users`  | Admin | JSON user list           |

### Default Credentials

```
Username: admin     Password: Admin@2024!    Role: admin
```

### Log format (every request)

```json
{
  "timestamp": "2026-06-12T18:00:00Z",
  "log_type": "webapp",
  "action": "login",
  "outcome": "success",
  "user": "admin",
  "ip": "172.31.0.1",
  "method": "POST",
  "path": "/login",
  "status_code": 200,
  "duration_ms": 42
}
```

### Filebeat Sidecar

The `filebeat` container reads Flask log files from a shared Docker volume and ships
them to Logstash. A critical fix for Windows:

```yaml
# docker/webapp/docker-compose.yml
command: ["filebeat", "-e", "--strict.perms=false"]
```

> Windows NTFS shows all Docker-mounted files as permission 777. Filebeat refuses to
> start if config files are world-writable. `--strict.perms=false` bypasses this check.

---

## 9. Agent Configuration

### 9.1 Winlogbeat — Windows PC (this machine)

Winlogbeat runs as a **native Windows service** (not in Docker) because Windows Event
Log is only accessible via the Windows Event Log API — not available inside containers.

Config: `C:\Program Files\Winlogbeat\winlogbeat.yml`

```yaml
output.logstash:
  hosts: ["127.0.0.1:5044"]   # Logstash is local (Docker port-forwarded)

setup.kibana:
  host: "127.0.0.1:5602"
```

Channels collected:
- `Security` — Event IDs: 4624, 4625, 4634, 4647, 4688, 4698, 4720-4726, 4732, 4756
- `System` — service start/stop, driver events
- `Application` — application errors
- `Microsoft-Windows-PowerShell/Operational` — script execution
- `Microsoft-Windows-Windows Defender/Operational` — AV detections

Service commands:
```powershell
Get-Service winlogbeat                    # Check status
Restart-Service winlogbeat                # Restart after config change
& "C:\Program Files\Winlogbeat\winlogbeat.exe" test config   # Validate config
& "C:\Program Files\Winlogbeat\winlogbeat.exe" test output   # Test connection to Logstash
```

Windows Firewall rules required (added during setup):
```powershell
# Allow inbound on Logstash Beats port from LAN
New-NetFirewallRule -DisplayName "ELK Logstash Beats" -Direction Inbound -Protocol TCP -LocalPort 5044 -Action Allow

# Allow inbound on Kibana from LAN
New-NetFirewallRule -DisplayName "ELK Kibana" -Direction Inbound -Protocol TCP -LocalPort 5602 -Action Allow
```

### 9.2 Filebeat — Linux Desktop (192.168.0.117)

Install script: `agents/install-filebeat-linux.sh`

```bash
sudo bash agents/install-filebeat-linux.sh 192.168.0.3
```

Config: `agents/filebeat-linux.yml` (deployed by the script)

```yaml
filebeat.inputs:
  - type: log
    paths: ["/var/log/syslog", "/var/log/auth.log", "/var/log/kern.log"]

output.logstash:
  hosts: ["192.168.0.3:5044"]    # SIEM_HOST

setup.kibana:
  host: "192.168.0.3:5602"
```

Service commands (on Linux):
```bash
sudo systemctl status filebeat
sudo systemctl restart filebeat
sudo filebeat test output -c /etc/filebeat/filebeat.yml
```

---

## 10. Kibana — Index Patterns and Dashboards

### 10.1 Index Patterns (Data Views)

Created via API in `run.ps1`. All use `@timestamp` as the time field.

| Pattern         | Data source                   |
|-----------------|-------------------------------|
| `windows-logs-*`| Winlogbeat (this PC)          |
| `webapp-logs-*` | Flask app (Filebeat sidecar)  |
| `syslog-*`      | Filebeat (Linux desktop)      |
| `docker-logs-*` | Docker container stdout       |
| `misc-logs-*`   | Untagged / fallthrough        |

To recreate manually: **Kibana → Stack Management → Data Views → Create data view**

### 10.2 Dashboard — Web Application (`webapp-logs-*`)

| Panel | Type | Query/Aggregation |
|-------|------|-------------------|
| Login attempts over time | Date histogram | `event.action: login` |
| Success vs Failure | Pie | `event.outcome` terms |
| Top users | Data table | `user.name` terms |
| HTTP status codes | Pie | `http.response.status_code` terms |
| Top source IPs | Bar | `client.ip` terms |
| Recent failed logins | Table | `event.outcome: failure` |

### 10.3 Dashboard — Windows Security (`windows-logs-*`)

| Panel | Type | Query/Aggregation |
|-------|------|-------------------|
| Login timeline | Date histogram | `tags: login_success OR login_failure` |
| Failed logins by machine | Bar | `winlog.computer_name` terms |
| Event ID breakdown | Pie | `winlog.event_id` terms |
| PowerShell activity | Count | `tags: powershell` |
| Process creation | Table | `tags: process_creation` |

### 10.4 Dashboard — Linux Infrastructure (`syslog-*`)

| Panel | Type | Query/Aggregation |
|-------|------|-------------------|
| Syslog by process | Bar | `process.name` terms |
| SSH auth attempts | Date histogram | `tags: linux_auth` |
| Auth failures | Table | `tags: linux_auth AND message: *fail*` |

### 10.5 Useful Saved Searches

| Name | KQL Query |
|------|-----------|
| Login failures (all sources) | `tags: login_failure` |
| Admin activity | `user.name: admin` |
| Windows security events | `tags: windows_security` |
| PowerShell execution | `tags: powershell` |
| SSH auth events | `tags: linux_auth AND process.name: sshd` |
| Docker errors | `tags: docker_log AND log.level: ERROR` |
| Grok parse failures | `tags: _grokparsefailure` |

---

## 11. Elasticsearch Index Templates

Index templates enforce consistent field mappings and prevent type conflicts.
Applied automatically to all new indices matching the pattern.

### windows-logs-* template

Key setting — maps `winlog.event_data.*` as `keyword` to prevent auto-detection:

```json
{
  "dynamic_templates": [{
    "winlog_event_data_as_keyword": {
      "path_match": "winlog.event_data.*",
      "mapping": { "type": "keyword" }
    }
  }]
}
```

> **Why this matters:** Winlogbeat sends `winlog.event_data.param1` with values that
> sometimes look like dates (`"2126-05-19T16:14:24Z"`). If ES auto-detects the first
> occurrence as `text` and the next as `date`, it throws a mapping conflict and rejects
> documents. Pinning to `keyword` prevents this.

Apply via API:
```powershell
$h = @{ Authorization="Basic <base64>"; "Content-Type"="application/json" }
Invoke-RestMethod -Method PUT -Uri "http://localhost:9201/_index_template/windows-logs-template" `
  -Headers $h -Body (Get-Content template.json -Raw)
```

---

## 12. Day-to-Day Operations

### Starting / Stopping

```powershell
cd C:\Users\Salivan Veerasekaran\apps\ELK

.\run.ps1          # Start all (ELK + Webapp)
.\stop.ps1         # Stop all (data preserved)
.\status.ps1       # Health check
.\rebuild.ps1      # Rebuild images
.\rebuild.ps1 -Clean   # Wipe volumes and rebuild (data lost)
.\rebuild.ps1 -All     # Re-pull base images and rebuild
```

### Container Management

```powershell
# View logs
docker logs -f logstash
docker logs -f kibana
docker logs --tail 50 webapp

# Restart a single service
docker restart logstash
docker restart kibana

# Enter a container shell
docker exec -it logstash bash
docker exec -it elasticsearch bash
```

### Elasticsearch Queries (PowerShell)

```powershell
$cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("elastic:ElkLab@2024"))
$h = @{ Authorization="Basic $cred" }
$base = "http://localhost:9201"

# Cluster health
Invoke-RestMethod "$base/_cluster/health" -Headers $h

# List all indices
Invoke-RestMethod "$base/_cat/indices?h=index,docs.count,health&s=index" -Headers $h

# Count documents in an index
Invoke-RestMethod "$base/windows-logs-*/_count" -Headers $h

# Delete an index (e.g. to fix a bad mapping)
Invoke-RestMethod -Method DELETE "$base/windows-logs-2026.06.12" -Headers $h

# Search (last 10 login failures)
$q = '{"query":{"term":{"tags":"login_failure"}},"size":10,"sort":[{"@timestamp":"desc"}]}'
Invoke-RestMethod -Method POST "$base/windows-logs-*/_search" -Headers ($h + @{"Content-Type"="application/json"}) -Body $q
```

### Logstash Stats

```powershell
$ls = Invoke-RestMethod "http://localhost:9600/_node/stats"
$ls.status                          # green / red
$ls.pipelines.main.events           # in / out / filtered counts
```

---

## 13. Troubleshooting

### Logstash: "Expected input/filter/output at line 1, column 1 (byte 1)"

**Cause:** Config file has a UTF-8 BOM. PowerShell `Set-Content -Encoding utf8` always writes BOM.

**Fix:** Rewrite the file without BOM:
```powershell
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("C:\...\pipeline\01-input.conf", $content, $utf8NoBom)
```

Verify:
```powershell
$bytes = [System.IO.File]::ReadAllBytes("path\to\file.conf")
Write-Host "First byte: $($bytes[0])"   # Must NOT be 239 (0xEF = BOM start)
```

### Logstash: Syntax error in pipeline config

**Cause:** Logstash config language does NOT support semicolons as separators.
Each setting must be on its own line:

```
# WRONG
tcp { port => 5000; codec => json }

# CORRECT
tcp {
  port  => 5000
  codec => json
}
```

### Elasticsearch: Mapping conflict — "cannot be changed from type [text] to [date]"

**Cause:** Field was first indexed as `text`, later ES auto-detected same field as `date`.

**Fix:**
1. Delete the affected index: `Invoke-RestMethod -Method DELETE "http://localhost:9201/windows-logs-2026.06.12" -Headers $h`
2. Create an index template pinning the field to `keyword` (see §11)
3. Let the index auto-recreate on next ingest

### Elasticsearch: yellow health

Normal for a single-node lab. All data is safe. Replica shards cannot be assigned
because there is no second node. Not an error.

### Kibana "server not ready yet"

Kibana waits for Elasticsearch to be healthy before starting. Wait 2-3 minutes.
Check ES health first, then check Kibana logs:
```powershell
docker logs --tail 30 kibana
```

### Winlogbeat not sending events

```powershell
# Test config
& "C:\Program Files\Winlogbeat\winlogbeat.exe" test config

# Test connection to Logstash
& "C:\Program Files\Winlogbeat\winlogbeat.exe" test output

# Check service
Get-Service winlogbeat
Restart-Service winlogbeat

# Check Logstash is reachable
Test-NetConnection -ComputerName 127.0.0.1 -Port 5044
```

### Docker port binding error (Windows)

**Cause:** Windows Docker Desktop cannot bind ports to a specific non-loopback host IP.

**Wrong:**
```yaml
ports:
  - "192.168.0.3:5044:5044"   # Fails on Windows Docker
```
**Correct:**
```yaml
ports:
  - "5044:5044"               # Binds to 0.0.0.0 (all interfaces)
```

### Filebeat on Linux: permission denied errors

```bash
sudo chmod go-w /etc/filebeat/filebeat.yml
sudo chown root:root /etc/filebeat/filebeat.yml
sudo systemctl restart filebeat
```

### Docker network conflict

**Cause:** Another project uses the same subnet.

**Fix:** Change `ELK_NET_SUBNET` and `WEBAPP_NET_SUBNET` in `.env` to unused ranges,
then run `.\rebuild.ps1 -Clean` to recreate everything.

Check existing networks:
```powershell
docker network ls
docker network inspect <name>
```

---

## 14. Security Considerations

| Area           | Current Lab Setting    | Production Recommendation              |
|----------------|------------------------|----------------------------------------|
| Transport TLS  | Disabled               | Enable TLS on all ES/Kibana/Logstash   |
| Passwords      | Stored in `.env` file  | Use Vault or Docker secrets            |
| ES binding     | `0.0.0.0`              | Bind to private interface only         |
| Kibana         | Direct HTTP            | Reverse proxy (nginx) + HTTPS          |
| Beats port     | No mutual TLS          | Enable mTLS with certificates          |
| Log retention  | No ILM policy          | Create ILM in Kibana (e.g. 30-day TTL) |
| Winlogbeat     | Plaintext output       | TLS output to Logstash                 |

Minimum hardening before any LAN exposure:
1. Change all passwords in `.env`
2. Never expose ports 5602 or 9201 on a public interface
3. Restrict Windows Firewall rules to your specific LAN subnet

---

## 15. Rebuilding from Scratch

If you need to tear down and rebuild everything:

```powershell
cd C:\Users\Salivan Veerasekaran\apps\ELK

# Stop everything
.\stop.ps1

# Full wipe and rebuild (all data lost)
.\rebuild.ps1 -Clean -All

# Start fresh
.\run.ps1
```

This will:
- Pull latest base images from Docker Hub
- Rebuild the Flask app image
- Wipe all Elasticsearch data (all indices gone)
- Recreate Docker networks
- Re-seed Elasticsearch users
- Winlogbeat will re-ship all buffered Windows events

---

ELK Lab SOP v2.0  |  2026-06-12  |  blackperl (192.168.0.3)
