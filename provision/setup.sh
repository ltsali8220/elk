#!/usr/bin/env bash
set -euo pipefail

echo "=== [1/9] System packages ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl gnupg ca-certificates jq apt-transport-https software-properties-common

echo "=== [2/9] Install Docker ==="
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu jammy stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker vagrant
systemctl enable --now docker

echo "=== [3/9] Kernel tuning ==="
sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" >> /etc/sysctl.conf

echo "=== [4/9] Create Docker networks ==="
docker network inspect elk-net    >/dev/null 2>&1 || docker network create --subnet="${ELK_NET_SUBNET}"    elk-net
docker network inspect webapp-net >/dev/null 2>&1 || docker network create --subnet="${WEBAPP_NET_SUBNET}" webapp-net

echo "=== [5/9] Start ELK stack ==="
cd /vagrant/docker/elk
docker compose --env-file /vagrant/.env up -d

echo "Waiting for Elasticsearch..."
until curl -s -u "elastic:${ELASTIC_PASSWORD}" "http://${ELASTICSEARCH_IP}:9200/_cluster/health" \
      | grep -qE '"status":"(green|yellow)"'; do
  sleep 5
done
echo "Elasticsearch ready."

echo "=== [6/9] Seed ES users ==="
# kibana_system password
curl -s -X POST -u "elastic:${ELASTIC_PASSWORD}" \
  "http://${ELASTICSEARCH_IP}:9200/_security/user/kibana_system/_password" \
  -H "Content-Type: application/json" \
  -d "{\"password\":\"${KIBANA_SYSTEM_PASSWORD}\"}"

# logstash_writer role
curl -s -X PUT -u "elastic:${ELASTIC_PASSWORD}" \
  "http://${ELASTICSEARCH_IP}:9200/_security/role/logstash_writer" \
  -H "Content-Type: application/json" \
  -d '{"cluster":["manage_index_templates","monitor"],"indices":[{"names":["*-logs-*","syslog-*","docker-logs-*","misc-logs-*"],"privileges":["write","create_index","create"]}]}'

# logstash_internal user
curl -s -X PUT -u "elastic:${ELASTIC_PASSWORD}" \
  "http://${ELASTICSEARCH_IP}:9200/_security/user/logstash_internal" \
  -H "Content-Type: application/json" \
  -d "{\"password\":\"${LOGSTASH_INTERNAL_PASSWORD}\",\"roles\":[\"logstash_writer\"],\"full_name\":\"Logstash Internal\"}"

echo "=== [7/9] Start webapp ==="
cd /vagrant/docker/webapp
docker compose --env-file /vagrant/.env up -d

echo "=== [8/9] Install Filebeat (system agent) ==="
curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elastic.gpg
echo "deb [signed-by=/usr/share/keyrings/elastic.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" \
  > /etc/apt/sources.list.d/elastic-8.x.list
apt-get update -qq
apt-get install -y -qq "filebeat=${ELK_VERSION}"

cp /vagrant/agents/filebeat-linux.yml /etc/filebeat/filebeat.yml
sed -i "s/__LOGSTASH_HOST__/${LOGSTASH_IP}/g"   /etc/filebeat/filebeat.yml
sed -i "s/__KIBANA_HOST__/${KIBANA_IP}/g"         /etc/filebeat/filebeat.yml
sed -i "s/__ELASTIC_PASSWORD__/${ELASTIC_PASSWORD}/g" /etc/filebeat/filebeat.yml

systemctl enable --now filebeat

echo "=== [9/9] Done ==="
echo ""
echo "  Kibana:        http://${ELK_VM_IP}:5601  (elastic / ${ELASTIC_PASSWORD})"
echo "  Web App:       http://${ELK_VM_IP}:8080  (admin / Admin@2024!)"
echo "  Elasticsearch: http://${ELK_VM_IP}:9200"
echo ""
