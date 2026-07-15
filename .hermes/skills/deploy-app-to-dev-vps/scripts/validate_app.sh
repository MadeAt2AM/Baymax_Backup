#!/usr/bin/env bash
# validate_app.sh — exhaustive end-to-end smoke test for a VPS-deployed app.
# Copy this to /tmp/validate_<name>.sh and adapt the path/method/payload lines.
#
# The script returns 0 only on full PASS. Output is human-readable, colorised,
# and ends with a PASS/FAIL/WARN summary.

set -uo pipefail

BASE="${BASE:-https://<name>.terrybot.top}"
BODY=""

PASS=0
FAIL=0
WARN=0

red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }
blue()   { printf '\033[0;34m%s\033[0m\n' "$*"; }

# IMPORTANT: $BODY=$(cat ...) inside req() runs in a subshell because req() is
# invoked via `code=$(req ...)` — the subshell capture means BODY written
# inside req() never propagates. So we persist to a side-channel file and
# read it back via body_get(). Same trick applies to ANY helper called via
# command-substitution that wants to communicate state to the caller.
req() {
  local method="$1"; local path="$2"; local data="${3:-}"; local token="${4:-}"
  local headers=(-H "Content-Type: application/json")
  [ -n "$token" ] && headers+=(-H "Authorization: Bearer $token")
  local args=(-sS -o /tmp/_body.$$ -w '%{http_code}' -X "$method" "$BASE$path" "${headers[@]}")
  [ -n "$data" ] && args+=(--data "$data")
  local code
  code=$(curl "${args[@]}" --max-time 15) || code="000"
  cp /tmp/_body.$$ /tmp/_resp_body.$$ 2>/dev/null || echo '' > /tmp/_resp_body.$$
  rm -f /tmp/_body.$$
  echo "$code"
}

body_get() { cat /tmp/_resp_body.$$ 2>/dev/null || echo ''; }

# assert <expected_code | 2xx | 3xx | 4xx | 5xx> <actual> <name>
assert() {
  local expected="$1" actual="$2" name="$3"
  case "$expected" in
    2xx) [[ "$actual" =~ ^2 ]] && { green "  ✓ $name -> $actual"; PASS=$((PASS+1)); return 0; } ;;
    3xx) [[ "$actual" =~ ^3 ]] && { green "  ✓ $name -> $actual"; PASS=$((PASS+1)); return 0; } ;;
    4xx) [[ "$actual" =~ ^4 ]] && { green "  ✓ $name -> $actual"; PASS=$((PASS+1)); return 0; } ;;
    5xx) [[ "$actual" =~ ^5 ]] && { green "  ✓ $name -> $actual"; PASS=$((PASS+1)); return 0; } ;;
    *)   [ "$actual" = "$expected" ] && { green "  ✓ $name -> $actual"; PASS=$((PASS+1)); return 0; } ;;
  esac
  red "  ✗ $name -> $actual (expected $expected)"
  FAIL=$((FAIL+1))
  local b; b=$(body_get)
  [ -n "$b" ] && echo "        body: $(echo "$b" | head -c 300)"
  return 1
}

# jq_get <field> — extract a field from the most recent req()'s body.
# IMPORTANT: passing the body via `BODY=$(body_get)` then reading it with
# `os.environ.get('BODY')` from inside a heredoc DOES NOT WORK — the heredoc
# starts a fresh Python subprocess that does NOT inherit parent shell
# variables. Pass body as argv instead.
jq_get() {
  local field="$1"
  local body
  body=$(body_get)
  python3 -c "
import json, sys
try:
    d = json.loads(sys.argv[1])
    print(d.get(sys.argv[2], ''))
except Exception:
    print('')
" "$body" "$field"
}

# Token cache. Rate-limited login endpoints (e.g. 5/email/15min) make
# repeated login attempts in one script run painful and across-runs fatal
# until the window resets. Cache successful tokens to disk; validate each
# cached token with /api/auth/me before trusting it (server may have
# rotated SESSION_SECRET, in which case we re-login).
TOKENS_CACHE="${TOKENS_CACHE:-/tmp/$(basename "$0")_tokens.json}"

# Load cached tokens at script start
if [ -f "$TOKENS_CACHE" ]; then
  while IFS='=' read -r k v; do
    [ -n "$k" ] && [ -n "$v" ] && eval "CACHED_${k}='$v'"
  done < <(python3 -c "
import json
try:
  d = json.load(open('$TOKENS_CACHE'))
  for em, tok in d.items():
    h = em.replace('@','_').replace('.','_').upper()
    print(f'{h}={tok}')
except: pass
")
fi

login() {
  local email="$1"
  local cached_var="CACHED_${email//@/_}"; cached_var="${cached_var//./_}"; cached_var="${cached_var^^}"
  local cached="${!cached_var:-}"
  if [ -n "$cached" ]; then
    local code=$(curl -sS -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $cached" "$BASE/api/auth/me")
    if [ "$code" = "200" ]; then printf '%s' "$cached"; return 0; fi
  fi
  local resp=$(curl -sS -X POST "$BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    --data "{\"email\":\"$email\",\"password\":\"Test123!\"}" \
    --max-time 15)
  local tok=$(printf '%s' "$resp" | python3 -c "
import json, sys
try: print(json.load(sys.stdin).get('token',''))
except: print('')
" 2>/dev/null)
  if [ -n "$tok" ]; then
    python3 - "$email" "$tok" "$TOKENS_CACHE" <<'PY'
import json, sys
em, tok, path = sys.argv[1], sys.argv[2], sys.argv[3]
try: d = json.load(open(path))
except: d = {}
d[em] = tok
json.dump(d, open(path, 'w'))
PY
  fi
  printf '%s' "$tok"
}

# ─── Edit below per app. The section names below are SYNTRA-shaped — adapt
#     to whatever your app's domain is (workforce / billing / CRM / etc.).

blue "── 1. PUBLIC ────────────────────────────────────────────────"
code=$(req GET /api/healthz); assert 200 "$code" "GET /api/healthz"
code=$(req GET /); assert 2xx "$code" "GET / (SPA root)"
code=$(req GET /login); assert 2xx "$code" "GET /login"

blue "── 2. AUTH ─────────────────────────────────────────────────"
TOK_PLATFORM=$(login platform@<app>.com)
TOK_ADMIN=$(login admin@demo.com)
TOK_STAFF=$(login staff1@demo.com)
for label in "platform@<app>.com:$TOK_PLATFORM" "admin@demo.com:$TOK_ADMIN" "staff1@demo.com:$TOK_STAFF"; do
  email=${label%%:*}; t=${label#*:}
  if [ -n "$t" ]; then green "  ✓ login $email"; PASS=$((PASS+1))
  else red "  ✗ login $email"; FAIL=$((FAIL+1)); fi
done

code=$(req GET /api/auth/me "" "$TOK_ADMIN"); assert 200 "$code" "GET /api/auth/me"
code=$(req POST /api/auth/login '{"email":"x@x.com","password":"y"}'); assert 401 "$code" "POST /api/auth/login bad creds -> 401"

# ... add groups for your app's endpoints here, using the assert/jq_get/req
# helpers. Common groups: platform-admin, team, workplaces, shifts, leave,
# invitations, notifications, custom-domain, SMTP test, role-based access.

blue "────────────────────────────────────────────────────────────"
echo
green "PASS: $PASS"
[ "$FAIL" -gt 0 ] && red "FAIL: $FAIL" || echo "FAIL: 0"
[ "$WARN" -gt 0 ] && yellow "WARN: $WARN" || echo "WARN: 0"
echo
[ "$FAIL" -eq 0 ] && exit 0 || exit 1

# ─── Notes for adapting ────────────────────────────────────────
#
# 1. IDempotent live-ID resolution: never hard-code employee/user IDs. After
#    a `DELETE FROM users` the sequence advances; query live IDs every run:
#
#      USER_IDS=$(curl -sS -H "Authorization: Bearer $TOK_ADMIN" \
#        "$BASE/api/users" | python3 -c "
#        import json, sys
#        d = json.load(sys.stdin)
#        m = {u['email']: u['id'] for u in d}
#        print(f\"{m.get('admin@demo.com','')} {m.get('staff1@demo.com','')}\")")
#      UID_ADMIN=$(echo $USER_IDS | awk '{print $1}')
#      UID_STAFF1=$(echo $USER_IDS | awk '{print $2}')
#
# 2. Schema surprises: don't assume field names. grep the API source for
#    the actual z.object() schemas before generating payloads:
#
#      ssh dev-vps 'grep -A 5 "z\\.object" /srv/projects/<name>/artifacts/api-server/src/routes/shift-swaps.ts'
#
# 3. Public token routes that redirect (e.g. /shift-replacements/token/<t>?
#    action=accept) return 302 — use case statements, not assert 2xx:
#
#      case "$code" in 2xx|302|303) green "  ✓ ..."; PASS=$((PASS+1));; *) ...;; esac
#
# 4. Endpoints that need live IDs that don't exist yet (e.g. test-company
#    creation requires ownerName+ownerEmail+ownerTempPassword) — capture
#    the schema from the API source, not from intuition.