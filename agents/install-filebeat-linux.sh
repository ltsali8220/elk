#!/usr/bin/env bash
# ============================================================
#  Run this script ON YOUR LINUX DESKTOP (as root / sudo)
#  to install Filebeat and start sending logs to your SIEM.
#
#  Usage:
#    sudo bash install-filebeat-linux.sh <SIEM_IP>
#
#  Example:
#    sudo bash install-filebeat-linux.sh 192.168.0.3
# ============================================================
set -euo pipefail

SIEM_IP="${1:?Usage: sudo bash install-filebeat-linux.sh <SIEM_IP>}"
ELK_VERSION="8.13.4"
ELASTIC_PASSWORD="ElkLab@2024"
KIBANA_PORT="5602"

echo "[1/4] Installing Filebeat ${ELK_VERSION}..."
curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch \
  | gpg --dearmor -o /usr/share/keyrings/elastic.gpg
echo "deb [signed-by=/usr/share/keyrings/elastic.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" \
  > /etc/apt/sources.list.d/elastic-8.x.list
apt-get update -qq
apt-get install -y -qq "filebeat=${ELK_VERSION}"

echo "[2/4] Writing config..."
cat > /etc/filebeat/filebeat.yml << FBEOF
filebeat.inputs:

  - type: log
    enabled: true
    paths:
      - /var/log/syslog
      - /var/log/messages
    fields:
      log_type: syslog
      host_type: linux-desktop
    fields_under_root: false
    tags: ["syslog"]

  - type: log
    enabled: true
    paths:
      - /var/log/auth.log
      - /var/log/secure
    fields:
      log_type: auth
      host_type: linux-desktop
    fields_under_root: false
    tags: ["linux_auth"]

  - type: log
    enabled: true
    paths:
      - /var/log/kern.log
    fields:
      log_type: kernel
      host_type: linux-desktop
    fields_under_root: false
    tags: ["kernel"]

filebeat.modules:
  - module: system
    syslog: { enabled: true }
    auth:   { enabled: true }

processors:
  - add_host_metadata:
      when.not.contains.tags: forwarded

output.logstash:
  hosts: ["${SIEM_IP}:5044"]

setup.kibana:
  host: "${SIEM_IP}:${KIBANA_PORT}"
  username: "elastic"
  password: "${ELASTIC_PASSWORD}"

logging.level: info
logging.to_files: false
FBEOF

echo "[3/4] Testing connectivity to SIEM..."
if nc -z -w 3 "${SIEM_IP}" 5044; then
  echo "  OK - Logstash port 5044 is reachable"
else
  echo "  WARNING - Cannot reach ${SIEM_IP}:5044 - check firewall on Windows PC"
fi

echo "[4/4] Enabling and starting Filebeat..."
systemctl enable filebeat
systemctl restart filebeat
systemctl status filebeat --no-pager

echo ""
echo "Done! Logs from this Linux machine are now flowing to:"
echo "  Logstash:  ${SIEM_IP}:5044"
echo "  Kibana:    http://${SIEM_IP}:${KIBANA_PORT}  (elastic / ${ELASTIC_PASSWORD})"
echo ""
echo "In Kibana create index pattern:  syslog-*  (time field: @timestamp)"
