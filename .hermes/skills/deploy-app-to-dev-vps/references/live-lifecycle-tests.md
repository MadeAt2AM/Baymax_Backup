# Live lifecycle tests on the dev VPS database

This is the working pattern for verifying create / activate / deactivate /
hard-delete (or any other destructive) flows against the live dev database
without tripping the IP or email login rate-limiter, and without leaving
orphan test data behind.

## Why this exists

`loginIpLimiter` and `loginEmailLimiter` (see skill
`security-hardening-web-stack`, the `trust proxy = 1` pitfall) return
`429 Too many attempts` after a handful of `/auth/login` hits from the same
public IP. The verifier on this host shares one egress IP. So any
"create tenant → login as the tenant owner → assert response" round-trip
trips the limiter within 3–5 requests.

Two ways out:

1. **One-off login probe** — call the API from inside the API container.
   Container traffic doesn't pass through Caddy or the limiter middleware.
2. **Full lifecycle script** — mint a short-lived JWT inside the API
   container using the same `SESSION_SECRET` it signs with, then curl
   the public API with `Authorization: Bearer <token>`. Never hits
   `/auth/login` from the public IP.

## One-off login probe (no rate limit, no JWT)

```bash
ssh dev-vps 'docker exec \
  -e EMAIL=tenant-owner@example.com \
  -e PW=TempPass123! \
  <api_container> \
  node -e "fetch(\"http://127.0.0.1:8080/api/auth/login\",{
    method:\"POST\",
    headers:{\"Content-Type\":\"application/json\"},
    body:JSON.stringify({email:process.env.EMAIL,password:process.env.PW})
  }).then(async r => console.log(r.status + \"|\" + await r.text()))"'
```

## Full lifecycle script (mint JWT, never touch /auth/login)

### 1. Discover the seed platform-admin id

```bash
ADMIN_ID=$(ssh dev-vps 'docker exec <pg_container> \
  psql -U <pg_user> -d <db> \
  -Atc "SELECT id FROM users WHERE role='\''platform_admin'\'' \
       ORDER BY id LIMIT 1"')
```

In the SYNTRA deploy this is currently `5`. The lookup is defensive — never
hard-code user ids, the seed may rotate after a delete-and-reseed cycle.

### 2. Mint a 1-hour JWT inside the API container

```bash
TOKEN=$(ssh dev-vps 'docker exec \
  -e SECRET="$(docker exec <api_container> printenv SESSION_SECRET)" \
  -e ADMIN_ID='"$ADMIN_ID"' \
  <api_container> \
  node -e "
    const enc = b => Buffer.from(b).toString(\"base64url\");
    const h = enc(JSON.stringify({alg:\"HS256\",typ:\"JWT\"}));
    const p = enc(JSON.stringify({
      userId:Number(process.env.ADMIN_ID),
      companyId:null,
      role:\"platform_admin\",
      exp:Math.floor(Date.now()/1000)+3600
    }));
    const sig = enc(require(\"crypto\").createHmac(\"sha256\",
      process.env.SECRET).update(\`${h}.${p}\`).digest());
    console.log(\`${h}.${p}.${sig}\`)"')
```

### 3. Build the lifecycle script and deliver it via base64

The script must do five things in order:

1. Create the disposable tenant.
2. Activate login (success).
3. Deactivate → assert 401 Invalid user.
4. Reactivate → assert login succeeds again.
5. Hard-delete tenant → assert 204, then assert 404 on a follow-up GET.

It must also have a `trap cleanup EXIT` that calls
`DELETE /api/platform/companies/$COMPANY_ID` regardless of which step
failed. This is the difference between "test passed, 0 rows left" and
"test failed halfway, 5 orphan rows in the live database".

#### Why base64?

Heredocs across ssh fail silently in catastrophic ways when nested
quotes are involved. Example failure mode: a script with three levels
of `'\''` escaping arrives on the VPS as a half-formed `trap` because
the outer quoting closed early. The cleanup never runs. You discover
this when the next live database query shows 5 companies named
`Baymax Lifecycle 1784139517` and `Baymax Lifecycle 1784139240`.

The base64 delivery is one-way — no quoting, no escaping, exactly the
bytes you wrote.

```python
# On the host, in a Python REPL or execute_code:
import base64
script = r'''set -euo pipefail
BASE="https://<name>.terrybot.top"
AUTH="Authorization: Bearer $TOKEN"
STAMP="$(date +%s)"
COMPANY_NAME="Baymax Lifecycle $STAMP"
OWNER_EMAIL="baymax-lifecycle-$STAMP@example.invalid"
OWNER_PASSWORD="LifecycleTest123!"
COMPANY_ID=""
OWNER_ID=""

cleanup() {
  if [ -n "$COMPANY_ID" ]; then
    curl -sS -o /dev/null -X DELETE "$BASE/api/platform/companies/$COMPANY_ID" -H "$AUTH" || true
  fi
}
trap cleanup EXIT

# 1. Create disposable tenant
CREATE="$(curl -sS --fail-with-body -X POST "$BASE/api/platform/companies" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"name\":\"$COMPANY_NAME\",\"ownerName\":\"Baymax Lifecycle Owner\",
       \"ownerEmail\":\"$OWNER_EMAIL\",\"ownerTempPassword\":\"$OWNER_PASSWORD\",
       \"plan\":\"starter\"}")"
COMPANY_ID="$(printf '%s' "$CREATE" | jq -r '.company.id')"
OWNER_ID="$(printf '%s' "$CREATE" | jq -r '.owner.id')"
printf 'created company=%s owner_id=%s\n' "$COMPANY_ID" "$OWNER_ID"

# 2. Activate login → 200
BEFORE="$(curl -sS -X POST "$BASE/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$OWNER_EMAIL\",\"password\":\"$OWNER_PASSWORD\"}" \
  -w '|%{http_code}')"
printf 'login_active=%s\n' "$BEFORE"
case "$BEFORE" in 200\|*) ;; *) exit 1;; esac

# 3. Deactivate → 401 Invalid user
DEACTIVATE="$(curl -sS --fail-with-body -X PUT \
  "$BASE/api/platform/companies/$COMPANY_ID" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"status":"inactive"}')"
printf 'deactivate=%s\n' "$DEACTIVATE"
INACTIVE_LOGIN="$(curl -sS -X POST "$BASE/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$OWNER_EMAIL\",\"password\":\"$OWNER_PASSWORD\"}" \
  -w '|%{http_code}')"
printf 'login_inactive=%s\n' "$INACTIVE_LOGIN"
case "$INACTIVE_LOGIN" in *'Invalid user'*) ;; *) exit 1;; esac

# 4. Reactivate → 200
REACTIVATE="$(curl -sS --fail-with-body -X PUT \
  "$BASE/api/platform/companies/$COMPANY_ID" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"status":"active"}')"
printf 'reactivate=%s\n' "$REACTIVATE"
ACTIVE_AGAIN="$(curl -sS -X POST "$BASE/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$OWNER_EMAIL\",\"password\":\"$OWNER_PASSWORD\"}" \
  -w '|%{http_code}')"
printf 'login_reactivated=%s\n' "$ACTIVE_AGAIN"
case "$ACTIVE_AGAIN" in 200\|*) ;; *) exit 1;; esac

# 5. Hard-delete → 204, then 404
DELETE_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' \
  -X DELETE "$BASE/api/platform/companies/$COMPANY_ID" -H "$AUTH")"
printf 'hard_delete_status=%s\n' "$DELETE_STATUS"
[ "$DELETE_STATUS" = 204 ]
GET_STATUS="$(curl -sS -o /tmp/lifecycle_get_body -w '%{http_code}' \
  "$BASE/api/platform/companies/$COMPANY_ID" -H "$AUTH")"
printf 'deleted_company_get_status=%s body=%s\n' \
  "$GET_STATUS" "$(cat /tmp/lifecycle_get_body)"
[ "$GET_STATUS" = 404 ]
USER_COUNT="$(docker exec <pg_container> psql -U <pg_user> -d <db> \
  -Atc "SELECT count(*) FROM users WHERE id=$OWNER_ID;")"
printf 'deleted_owner_rows=%s\n' "$USER_COUNT"
[ "$USER_COUNT" = 0 ]

# Tell trap not to re-delete
COMPANY_ID=""
printf 'LIVE_LIFECYCLE_TEST=PASS\n'
'''
b64 = base64.b64encode(script.encode()).decode()
```

```bash
# Deliver and run:
ssh dev-vps "printf '%s' '$b64' | base64 -d | bash"
```

If the script's `exit 1` on a failed assertion is not enough, wrap the
deliver+run in a loop that exits with the script's status. Python's
`subprocess.run(..., timeout=180)` does this cleanly.

### 4. Verify no orphan test rows

```bash
ssh dev-vps 'docker exec <pg_container> psql -U <pg_user> -d <db> \
  -Atc "SELECT count(*) FROM companies WHERE name LIKE '\''Baymax Lifecycle %'\''"'
```

Returns 0. If it returns 1+ the cleanup didn't fire — go look at the
half-written trap, fix the script, and delete the orphans manually:

```bash
ssh dev-vps 'docker exec <pg_container> psql -U <pg_user> -d <db> \
  -Atc "SELECT id,name FROM companies WHERE name LIKE '\''Baymax Lifecycle %'\''"'
# then DELETE via /api/platform/companies/<id>
```

## What this catches that a localhost mock does not

- The actual Caddy reverse proxy routing
- The real JWT signing path (any drift in `SESSION_SECRET` between
  secrets file and the container env breaks the mint step)
- The actual `ON DELETE CASCADE` order on tenant-owned data (some
  foreign keys were `SET NULL`, others `CASCADE` — the live DB has
  the canonical mapping)
- The actual rate-limiter thresholds (a localhost test that bypasses
  Caddy won't catch a future change where the limiter moves from
  per-IP to per-IP-per-account)
- The actual webhook / container restart sequence (the cleanup
  `trap` exercises the live DELETE endpoint, which has its own auth
  middleware)

## What this does not catch

- Browser-side redirects on login (the SPA's `window.location.assign`
  path). Use a Playwright test for that.
- Visual state of the platform admin dashboard. Pair this script with
  a browser smoke test if the change touched any UI component.
