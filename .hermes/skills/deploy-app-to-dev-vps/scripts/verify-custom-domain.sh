#!/usr/bin/env bash
# verify-custom-domain.sh — live verification of the three-layer
# custom-domain routing pattern (Caddy vhost + post-login redirectTo +
# CORS allowlist). Drop into <repo>/scripts/ and adapt the variables.
#
# Usage:
#   PLATFORM_HOST=syntra.terrybot.top \
#   CUSTOM_DOMAIN=syntra.cyberslide.net \
#   TEST_USER_EMAIL=chrisspeakseh@gmail.com \
#   TEST_USER_PASSWORD='Test123!' \
#   COMPANY_ID=19 \
#   ./scripts/verify-custom-domain.sh
#
# Required on PATH: ssh, curl, jq. Reads /srv/scripts/.gh-token on the VPS
# via `ssh dev-vps` if APP_API env is unset (i.e. calls go through VPS ssh).
#
# Exits non-zero on the first failure with a clear diagnostic message.

set -uo pipefail

: "${PLATFORM_HOST:?PLATFORM_HOST must be set (e.g. syntra.terrybot.top)}"
: "${CUSTOM_DOMAIN:?CUSTOM_DOMAIN must be set (e.g. syntra.cyberslide.net)}"
: "${TEST_USER_EMAIL:?TEST_USER_EMAIL required (a user belonging to the company)}"
: "${TEST_USER_PASSWORD:?TEST_USER_PASSWORD required}"
: "${COMPANY_ID:=19}"

# Where to run docker exec / read DB from. Override if API isn't on dev-vps.
VPS="${VPS:-dev-vps}"

# Internal-API URL on the VPS — bypass Caddy so we can pin the Host header
# to simulate cross-origin login without a real cross-origin fetch.
API_URL="${API_URL:-http://127.0.0.1:8080}"

PASS=0
FAIL=0

ok()   { printf '  ✓ %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  ✗ %s\n' "$1"; FAIL=$((FAIL+1)); }
hdr()  { printf '\n[%s]\n' "$1"; }

# 1. DNS CNAME — the customer domain should CNAME to the platform host.
hdr "1. DNS — CNAME chain"
CNAME=$(dig +short "$CUSTOM_DOMAIN" CNAME | sed 's/\.$//')
if [ "$CNAME" = "$PLATFORM_HOST" ]; then
  ok "CNAME $CUSTOM_DOMAIN → $PLATFORM_HOST"
else
  bad "CNAME expected $PLATFORM_HOST, got '$CNAME'"
fi
A_REC=$(dig +short "$PLATFORM_HOST" A | head -1)
[ -n "$A_REC" ] && ok "A record $PLATFORM_HOST → $A_REC" || bad "A record for $PLATFORM_HOST missing"

# 2. Caddy vhost — site block must exist for the custom domain.
hdr "2. Caddy vhost"
if ssh "$VPS" "test -f /srv/caddy/sites/${PLATFORM_HOST%%.*}-extra-hosts.caddy" >/dev/null 2>&1; then
  if ssh "$VPS" "grep -q '$CUSTOM_DOMAIN {' /srv/caddy/sites/${PLATFORM_HOST%%.*}-extra-hosts.caddy"; then
    ok "site block for $CUSTOM_DOMAIN present in -extra-hosts.caddy"
  else
    bad "Caddy extras file exists but has no block for $CUSTOM_DOMAIN — append to /srv/secrets/<name>-custom-domains and rerun <name>_dev.sh"
  fi
else
  bad "/srv/caddy/sites/<name>-extra-hosts.caddy missing — write_extra_caddy() never ran on this VPS"
fi

# 3. HTTPS reachability on the custom domain (ACME cert in place).
hdr "3. HTTPS reachability"
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 "https://$CUSTOM_DOMAIN/" 2>/dev/null || echo 000)
if [ "$CODE" = "200" ]; then
  ok "https://$CUSTOM_DOMAIN/ → HTTP 200"
else
  bad "https://$CUSTOM_DOMAIN/ → HTTP $CODE (LE cert may still be provisioning, wait 30s and retry)"
fi

# 4. API branding endpoint — the api should resolve CYBERSLIDE on the
#    custom hostname (Host header passed through to req.hostname).
hdr "4. API branding on custom Host"
BRAND=$(ssh "$VPS" "docker exec syntra_api wget -qO- 'http://127.0.0.1:8080/api/public/branding?host=$CUSTOM_DOMAIN'" 2>/dev/null)
if echo "$BRAND" | grep -q '"branded":true'; then
  ok "branding resolves: $BRAND"
else
  bad "branding did NOT resolve: $BRAND"
fi

# 5. Login from PLATFORM_HOST → response should include redirectTo.
hdr "5. Login from $PLATFORM_HOST → should bounce to $CUSTOM_DOMAIN"
LOGIN_A=$(ssh "$VPS" "docker exec syntra_api wget -qO- -X POST 'http://127.0.0.1:8080/api/auth/login' \
  --header 'Content-Type: application/json' \
  --header 'Host: $PLATFORM_HOST' \
  --post-data '{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASSWORD\"}'" 2>/dev/null)
RTO=$(echo "$LOGIN_A" | jq -r '.redirectTo // empty' 2>/dev/null)
if [ "$RTO" = "https://$CUSTOM_DOMAIN/dashboard" ]; then
  ok "redirectTo=$RTO"
else
  bad "expected redirectTo=https://$CUSTOM_DOMAIN/dashboard, got '$RTO' — got: $LOGIN_A"
fi

# 6. Login from CUSTOM_DOMAIN → redirectTo should be null (same-host).
hdr "6. Login from $CUSTOM_DOMAIN → no bounce"
LOGIN_B=$(ssh "$VPS" "docker exec syntra_api wget -qO- -X POST 'http://127.0.0.1:8080/api/auth/login' \
  --header 'Content-Type: application/json' \
  --header 'Host: $CUSTOM_DOMAIN' \
  --post-data '{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASSWORD\"}'" 2>/dev/null)
RTB=$(echo "$LOGIN_B" | jq -r '.redirectTo // "MISSING"' 2>/dev/null)
if [ "$RTB" = "null" ]; then
  ok "redirectTo=null (same-host case correctly suppressed)"
else
  bad "expected redirectTo=null, got '$RTB' — got: $LOGIN_B"
fi

# 7. Login from PLATFORM_HOST as a platform admin (no company) → no bounce.
hdr "7. Login as platform_admin → no bounce"
PA_EMAIL="${PLATFORM_ADMIN_EMAIL:-platform@syntra.com}"
PA_PASS="${PLATFORM_ADMIN_PASSWORD:-Test123!}"
LOGIN_C=$(ssh "$VPS" "docker exec syntra_api wget -qO- -X POST 'http://127.0.0.1:8080/api/auth/login' \
  --header 'Content-Type: application/json' \
  --header 'Host: $PLATFORM_HOST' \
  --post-data '{\"email\":\"$PA_EMAIL\",\"password\":\"$PA_PASS\"}'" 2>/dev/null)
RTC=$(echo "$LOGIN_C" | jq -r '.redirectTo // "MISSING"' 2>/dev/null)
if [ "$RTC" = "null" ]; then
  ok "redirectTo=null (platform_admin has no company)"
else
  bad "expected redirectTo=null, got '$RTC' — got: $LOGIN_C"
fi

# 8. CORS — preflight from the custom origin must succeed.
hdr "8. CORS preflight from $CUSTOM_DOMAIN origin"
ACAO=$(curl -sI -X OPTIONS "https://$PLATFORM_HOST/api/public/branding" \
  -H "Origin: https://$CUSTOM_DOMAIN" \
  -H "Access-Control-Request-Method: GET" \
  2>/dev/null | grep -i '^access-control-allow-origin:' | awk '{print $2}' | tr -d '\r')
if [ "$ACAO" = "https://$CUSTOM_DOMAIN" ]; then
  ok "Access-Control-Allow-Origin: $ACAO"
else
  bad "expected Access-Control-Allow-Origin: https://$CUSTOM_DOMAIN, got '$ACAO' — CORS allowlist missing the host"
fi

echo
echo "──────────────────────────────────────────"
printf '  %d passed, %d failed\n' "$PASS" "$FAIL"
echo "──────────────────────────────────────────"
[ "$FAIL" -eq 0 ]