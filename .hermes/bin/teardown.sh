#!/usr/bin/env bash
# teardown.sh — remove a deployed project
#
# Usage:
#   teardown.sh <project-name>
#
# Architecture: DNS ops run locally (CF API), Docker/Caddy ops run on dev VPS via SSH.

set -euo pipefail

NAME="${1:?usage: teardown.sh <project-name>}"
DEV_VPS="deploy@147.79.18.32"
SSH_KEY="${HOME}/.ssh/baymax_dev_vps"
PROJECT_DIR="/srv/projects/${NAME}"
CADDY_SITE="/srv/caddy/sites/${NAME}.caddy"
CF_DNS="$(dirname "$(readlink -f "$0")")/cf-dns.sh"

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)
ssh_run() { ssh "${SSH_OPTS[@]}" "$DEV_VPS" "$1"; }

red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }

echo "=== Tearing down ${NAME} ==="

# 1. Stop and remove container (on dev VPS)
yellow "[1/4] Stopping container on dev VPS"
ssh_run "cd '${PROJECT_DIR}' 2>/dev/null && docker compose down -v 2>&1 | tail -5 || docker rm -f '${NAME}-app' 2>/dev/null || true"

# 2. Remove Caddy site block (on dev VPS)
yellow "[2/4] Removing Caddy site block"
ssh_run "rm -f '${CADDY_SITE}' && docker exec caddy caddy reload --config /etc/caddy/Caddyfile 2>&1 | tail -2 || true"

# 3. Delete DNS record (local — CF API)
yellow "[3/4] Removing DNS record"
"${CF_DNS}" del "${NAME}"

# 4. Project files left in place (intentional — user controls when to rm -rf)
yellow "[4/4] Project files left at ${PROJECT_DIR} (delete manually if needed)"
yellow "      To remove completely: ssh ${DEV_VPS} 'sudo rm -rf ${PROJECT_DIR}'"

green "=== TEARDOWN COMPLETE: ${NAME} ==="