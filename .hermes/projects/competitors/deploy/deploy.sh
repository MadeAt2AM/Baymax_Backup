#!/usr/bin/env bash
# One-shot deploy script for the dev VPS.
#
# Usage:
#   bash deploy/deploy.sh
#
# Prerequisites:
#   - Docker + Docker Compose installed
#   - .env file populated (use `cp deploy/.env.example deploy/.env`)
#   - The host directory /srv/competitors-private/ exists with mode 0700
#   - The OPENCLI_BIN binary is at /usr/bin/opencli on the host
#   - Caddy is installed on the host and bootstrapped

set -euo pipefail

# Make sure we run from the repo root.
cd "$(dirname "$0")/.."

# 1. Verify .env exists.
if [ ! -f deploy/.env ]; then
  echo "missing deploy/.env — copy deploy/.env.example and fill in values"
  exit 1
fi

# 2. Verify the host's persistent directory exists.
if [ ! -d /srv/competitors-private ]; then
  echo "creating /srv/competitors-private"
  mkdir -p /srv/competitors-private
  chmod 0700 /srv/competitors-private
fi

# 3. Verify OpenCLI binary is on the host at the configured path.
OPENCLI_BIN="${OPENCLI_BIN:-/usr/bin/opencli}"
if [ ! -x "$OPENCLI_BIN" ]; then
  echo "missing or non-executable opencli at $OPENCLI_BIN"
  echo "run scripts/setup_dev_vps.sh first"
  exit 1
fi

# 4. Warn if the approved Instagram account is not set.
APPROVED_INSTAGRAM_ACCOUNT="${APPROVED_INSTAGRAM_ACCOUNT:-}"
if [ -z "$APPROVED_INSTAGRAM_ACCOUNT" ]; then
  echo "APPROVED_INSTAGRAM_ACCOUNT is empty — the OpenCLI collector will refuse to run"
fi

# 5. Build and bring the API up.
docker compose -f deploy/docker-compose.yml build --pull
docker compose -f deploy/docker-compose.yml up -d postgres
echo "waiting for postgres to be healthy..."
docker compose -f deploy/docker-compose.yml exec -T postgres pg_isready -U "${POSTGRES_USER:-competitors}" -d "${POSTGRES_DB:-competitors}"
docker compose -f deploy/docker-compose.yml up -d api web
docker compose -f deploy/docker-compose.yml ps

# 6. Run Alembic migrations.
docker compose -f deploy/docker-compose.yml exec -T api alembic upgrade head

# 7. Restart Caddy to reload the production Caddyfile.
if command -v caddy >/dev/null 2>&1; then
  echo "reloading host caddy..."
  sudo systemctl reload caddy
else
  echo "caddy not installed on the host — install with: apt-get install -y caddy"
fi

# 8. Smoke-test the deployment.
echo "=== smoke test ==="
sleep 5
curl -fsS https://competitors.terrybot.top/api/healthz || {
  echo "smoke test failed"
  exit 1
}
echo "smoke test passed."
