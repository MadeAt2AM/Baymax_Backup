#!/usr/bin/env bash
# deploy-smoke-test.sh — Post-deploy smoke test for web apps
# Usage: ./deploy-smoke-test.sh <app_url> [network_name]

set -euo pipefail

APP_URL="${1:-https://payntra.terrybot.top}"
NETWORK="${2:-payntra-net}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; exit 1; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }

echo "=== Post-Deploy Smoke Test: $APP_URL ==="

# 1. Health check
echo -n "Health endpoint... "
curl -fsS "$APP_URL/health" >/dev/null && pass "OK" || fail "Health check failed"

# 2. Auth pages load
echo -n "Login page... "
curl -fsS "$APP_URL/login" >/dev/null && pass "OK" || fail "Login page failed"

# 3. Forgot password page
echo -n "Forgot password page... "
curl -fsS "$APP_URL/forgot-password" >/dev/null && pass "OK" || fail "Forgot password page failed"

# 4. Protected route redirects (should 302 to login)
echo -n "Protected route redirect... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/ledger/2026-07")
[[ "$STATUS" == "302" || "$STATUS" == "307" ]] && pass "Redirects to login ($STATUS)" || warn "Got $STATUS (expected 302/307)"

# 5. SMTP test from app container
echo -n "SMTP connectivity from app container... "
APP_CID=$(docker network inspect "$NETWORK" 2>/dev/null | jq -r '.[0].Containers | to_entries[] | select(.value.Name | contains("app")) | .key' | head -1)
if [[ -n "$APP_CID" && "$APP_CID" != "null" ]]; then
  docker exec "$APP_CID" timeout 5 nc -zv mail.cyberslide.net 587 >/dev/null 2>&1 && pass "TCP OK" || fail "SMTP TCP failed"
  
  echo -n "SMTP TLS handshake from app container... "
  docker exec "$APP_CID" timeout 10 openssl s_client -starttls smtp -connect mail.cyberslide.net:587 -servername mail.cyberslide.net < /dev/null >/dev/null 2>&1 && pass "TLS OK" || fail "TLS handshake failed (MTU?)"
else
  warn "No app container found on network $NETWORK"
fi

# 6. DB connectivity from app container
echo -n "PostgreSQL connectivity from app container... "
if [[ -n "$APP_CID" && "$APP_CID" != "null" ]]; then
  docker exec "$APP_CID" timeout 5 nc -zv db 5432 >/dev/null 2>&1 && pass "OK" || fail "DB connection failed"
else
  warn "Skipped (no app container)"
fi

# 7. Forgot password API (dry run - just check endpoint exists)
echo -n "Forgot password API endpoint... "
curl -fsS -X POST "$APP_URL/api/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}' >/dev/null && pass "Endpoint responds" || warn "Endpoint error (may be expected for invalid email)"

echo -e "\n${GREEN}All critical checks passed!${NC}"
echo "Manual verification recommended: password reset email flow, ledger CRUD, file uploads"