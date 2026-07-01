#!/usr/bin/env bash
# teardown.sh — reverse a deploy
#
# Usage:
#   teardown.sh <project-name>
#
# Stops the container, removes Caddy route, deletes DNS record.
# Preserves /srv/projects/<name>/ so you can inspect logs.

set -euo pipefail

NAME="${1:?usage: teardown.sh <project-name>}"

# ---- CONFIGURE FOR YOUR ENVIRONMENT ----
DEV_VPS_USER="deploy"
DEV_VPS_HOST="147.79.18.32"
SSH_KEY="${HOME}/.ssh/baymax_dev_vps"
DOMAIN="terrybot.top"
PROJECT_DIR="/srv/projects/${NAME}"
CADDY_SITE="/srv/caddy/sites/${NAME}.caddy"
# ---------------------------------------

DEV_VPS="${DEV_VPS_USER}@${DEV_VPS_HOST}"
CF_DNS="$(dirname "$(readlink -f "$0")")/cf-dns.sh"

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)
ssh_run() { ssh "${SSH_OPTS[@]}" "$DEV_VPS" "$1"; }

yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }

echo "=== Tearing down ${NAME} ==="

# 1. Stop container
if ssh_run "docker inspect '${NAME}-app' >/dev/null 2>&1"; then
    yellow "[1/4] Stopping container"
    ssh_run "cd '${PROJECT_DIR}' 2>/dev/null && docker compose down -v 2>&1 | tail -5 || docker rm -f '${NAME}-app'" || true
else
    echo "[1/4] No container found, skipping"
fi

# 2. Remove Caddy site block
yellow "[2/4] Removing Caddy site block"
ssh_run "[ -f '${CADDY_SITE}' ] && rm -f '${CADDY_SITE}'"
ssh_run "docker exec caddy caddy reload --config /etc/caddy/Caddyfile 2>&1 | tail -2"

# 3. Delete DNS record
yellow "[3/4] Removing DNS record"
"${CF_DNS}" del "${NAME}"

# 4. Preserve project files (manual cleanup if needed)
yellow "[4/4] Project files left in place at ${PROJECT_DIR}"
yellow "      To remove: ssh ${DEV_VPS} 'rm -rf ${PROJECT_DIR}'"

green "=== TEARDOWN COMPLETE: ${NAME} ==="