#!/usr/bin/env bash
# deploy.sh — one-shot container deploy with per-subdomain DNS
#
# Usage:
#   deploy.sh <project-name> [port]
#
# Architecture: this script runs on the CONTROL VPS (not the dev VPS).
# DNS ops hit the Cloudflare API directly. Docker ops run over SSH on
# the dev VPS where Docker + the `web` network already exist.

set -euo pipefail

NAME="${1:?usage: deploy.sh <project-name> [port]}"
PORT="${2:-8080}"

# ---- CONFIGURE THESE FOR YOUR ENVIRONMENT ----
DEV_VPS_USER="deploy"
DEV_VPS_HOST="147.79.18.32"
SSH_KEY="${HOME}/.ssh/baymax_dev_vps"
DOMAIN="terrybot.top"
DEFAULT_VPS_IP="147.79.18.32"
PROJECTS_DIR="/srv/projects"
CADDY_DIR="/srv/caddy"
# ----------------------------------------------

DEV_VPS="${DEV_VPS_USER}@${DEV_VPS_HOST}"
PROJECT_DIR="${PROJECTS_DIR}/${NAME}"
CADDY_SITE="${CADDY_DIR}/sites/${NAME}.caddy"
FULL_DOMAIN="${NAME}.${DOMAIN}"

CF_DNS="$(dirname "$(readlink -f "$0")")/cf-dns.sh"
[ -x "$CF_DNS" ] || { echo "ERR: cf-dns.sh not found at $CF_DNS"; exit 1; }

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)
ssh_run() { ssh "${SSH_OPTS[@]}" "$DEV_VPS" "$1"; }

red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }

echo "=== Deploying ${NAME} on port ${PORT} ==="
echo "    URL will be: https://${FULL_DOMAIN}"

# 1. DNS record (idempotent)
yellow "[1/5] Creating DNS record for ${FULL_DOMAIN}"
"${CF_DNS}" add "${NAME}" "${DEFAULT_VPS_IP}"

# 2. Project directory + scaffold on dev VPS
yellow "[2/5] Creating project directory on dev VPS"
ssh_run "mkdir -p '${PROJECT_DIR}'"

if ! ssh_run "test -f '${PROJECT_DIR}/docker-compose.yml'" 2>/dev/null; then
    yellow "    Scaffolding docker-compose.yml + Dockerfile + app.py"
    cat > /tmp/deploy-scaffold.sh <<SCAFFOLD
#!/usr/bin/env bash
set -euo pipefail
NAME="\$1"; PORT="\$2"; PROJECT_DIR="\$3"
cat > "\${PROJECT_DIR}/docker-compose.yml" <<EOF
services:
  app:
    build: .
    container_name: \${NAME}-app
    restart: unless-stopped
    environment:
      - PORT=\${PORT}
    expose:
      - "\${PORT}"
    networks:
      - web
networks:
  web:
    external: true
    name: web
EOF
cat > "\${PROJECT_DIR}/Dockerfile" <<EOF
FROM python:3.12-alpine
WORKDIR /app
COPY app.py .
EXPOSE \${PORT}
CMD ["python", "app.py"]
EOF
cat > "\${PROJECT_DIR}/app.py" <<EOF
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
PORT = int(os.environ.get("PORT", "\${PORT}"))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        body = f"Hello from \${NAME}!\\nHostname: {self.headers.get('Host')}\\nPath: {self.path}\\n"
        self.wfile.write(body.encode())

if __name__ == "__main__":
    print(f"\${NAME} listening on :{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
EOF
SCAFFOLD
    scp "${SSH_OPTS[@]}" /tmp/deploy-scaffold.sh "${DEV_VPS}:/tmp/deploy-scaffold.sh"
    ssh_run "bash /tmp/deploy-scaffold.sh '${NAME}' '${PORT}' '${PROJECT_DIR}' && rm /tmp/deploy-scaffold.sh"
else
    yellow "    docker-compose.yml already exists, skipping scaffold"
fi

# 3. Build and start container
yellow "[3/5] Building and starting container"
ssh_run "cd '${PROJECT_DIR}' && docker compose up -d --build 2>&1 | tail -15"

# 4. Caddy site block + reload
yellow "[4/5] Configuring Caddy for ${FULL_DOMAIN}"
ssh_run "cat > '${CADDY_SITE}' <<EOF
${FULL_DOMAIN} {
    reverse_proxy ${NAME}-app:${PORT}
}
EOF
docker exec caddy caddy reload --config /etc/caddy/Caddyfile 2>&1 | tail -3"

# 5. Verify HTTPS (cert provisioning can take 30-60s)
yellow "[5/5] Waiting for HTTPS to come up (cert provisioning can take ~30-60s)"
url="https://${FULL_DOMAIN}"
code=000
for i in {1..30}; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        green "    HTTPS OK (HTTP $code)"
        break
    fi
    sleep 3
done

if [ "$code" != "200" ]; then
    yellow "    HTTPS not ready yet (last code: $code). Cert provisioning may still be in progress."
    yellow "      Check back in 30-60s with: curl -I https://${FULL_DOMAIN}"
    echo ""
    yellow "Debug info:"
    ssh_run "docker logs ${NAME}-app 2>&1 | tail -10"
    ssh_run "docker exec caddy caddy list-certificates 2>&1 | head -20"
fi

echo ""
green "=== DEPLOY COMPLETE: https://${FULL_DOMAIN} ==="