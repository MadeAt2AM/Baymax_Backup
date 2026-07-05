#!/usr/bin/env bash
# verify-network.sh — Quick Docker network & MTU verification
# Usage: ./verify-network.sh [network_name] [smtp_host] [smtp_port]

set -euo pipefail

NETWORK="${1:-app-net}"
SMTP_HOST="${2:-mail.cyberslide.net}"
SMTP_PORT="${3:-587}"

echo "=== Host MTU ==="
ip link show eth0 | grep -o 'mtu [0-9]*' || echo "Could not detect eth0 MTU"

echo -e "\n=== Docker Network: $NETWORK ==="
docker network inspect "$NETWORK" 2>/dev/null | jq -r '.[0].Options["com.docker.network.driver.mtu"] // "NOT SET (default 1500)"' | xargs -I{} echo "Network MTU: {}"

echo -e "\n=== Containers on $NETWORK ==="
docker network inspect "$NETWORK" 2>/dev/null | jq -r '.[0].Containers | to_entries[] | "\(.value.Name): \(.value.IPv4Address)"'

echo -e "\n=== Container Interface MTUs ==="
for container in $(docker network inspect "$NETWORK" 2>/dev/null | jq -r '.[0].Containers | keys[]'); do
  mtu=$(docker exec "$container" ip link show eth0 2>/dev/null | grep -o 'mtu [0-9]*' | awk '{print $2}' || echo "N/A")
  echo "  $container: eth0 MTU = $mtu"
done

echo -e "\n=== SMTP Connectivity Test (from host) ==="
timeout 5 nc -zv "$SMTP_HOST" "$SMTP_PORT" 2>&1 || echo "TCP connection failed"

echo -e "\n=== SMTP TLS Handshake Test (from host) ==="
timeout 10 openssl s_client -starttls smtp -connect "$SMTP_HOST:$SMTP_PORT" -servername "$SMTP_HOST" < /dev/null 2>&1 | head -20

echo -e "\n=== SMTP Connectivity Test (from app container) ==="
APP_CONTAINER=$(docker network inspect "$NETWORK" 2>/dev/null | jq -r '.[0].Containers | to_entries[] | select(.value.Name | contains("app")) | .key' | head -1)
if [[ -n "$APP_CONTAINER" && "$APP_CONTAINER" != "null" ]]; then
  echo "Testing from container: $APP_CONTAINER"
  docker exec "$APP_CONTAINER" timeout 5 nc -zv "$SMTP_HOST" "$SMTP_PORT" 2>&1 || echo "TCP connection failed from container"
  
  echo -e "\n=== SMTP TLS Handshake Test (from app container) ==="
  docker exec "$APP_CONTAINER" timeout 10 openssl s_client -starttls smtp -connect "$SMTP_HOST:$SMTP_PORT" -servername "$SMTP_HOST" < /dev/null 2>&1 | head -20
else
  echo "No 'app' container found on network $NETWORK"
fi

echo -e "\n=== PostgreSQL Connectivity (from app container) ==="
if [[ -n "$APP_CONTAINER" && "$APP_CONTAINER" != "null" ]]; then
  docker exec "$APP_CONTAINER" timeout 5 nc -zv db 5432 2>&1 || echo "DB connection failed from container"
  docker exec "$APP_CONTAINER" getent hosts db 2>&1 || echo "DNS resolution failed for 'db'"
else
  echo "Skipped (no app container)"
fi

echo -e "\n=== Done ==="