# Live curl smoke tests — protocol for verifying an app actually works after deploy

The deployment mechanics (DNS, Caddy, webhook, TLS) are covered in the parent skill. This reference covers the **application-layer** verification that runs after a successful deploy: prove that real Postgres, real SMTP, real JWT cookies, and real domain routing all work end-to-end.

The protocol: every assertion is a real HTTP call against `https://<app>.<domain>` from outside the dev VPS. No `localhost`. No "tests pass." Only "this user-visible behavior happens."

## Why this matters (lesson from 2026-07-04, Payntra)

We shipped 6 phases of auth (login, logout, forgot, reset, profile, password change) end-to-end. Every single behavior was verified with a real curl call before the next phase started. The pattern caught two real bugs that unit tests would have missed:

- Reset secret came back from `psql` with a trailing newline → Zod's `min(64)` rejected it. Trim with `tr -d '[:space:]'` before sending.
- SMTP send took 5.9s; the "Reset link sent" success log was rotated out before we could read it. **But the DB state was authoritative**: `SELECT reset_secret IS NOT NULL FROM users` proved the route ran the SMTP path. The email arriving in your inbox is downstream and unverifiable from CLI — DB state is your ground truth.

## The protocol

For every API route you ship, before declaring it done:

1. **Negative case first** — empty body, missing fields, bad creds → 400 / 401 with the right shape
2. **Auth gate** — same request without cookie → 401 `unauthorized`
3. **Auth setup** — POST the setup endpoint (e.g. login) with `-c cookies.txt` to persist
4. **Positive case** — same request with cookie → 200 + expected payload
5. **State mutation verified** — read the DB directly to confirm the mutation happened, not just that the API returned 200
6. **Single-use / idempotency** — repeat the positive case → 410 Gone / 409 Conflict / 200-with-no-change
7. **Cleanup** — `curl -b cookies.txt -X POST .../logout` to confirm logout clears the cookie
8. **Cross-user negative case** (per-user-resource endpoints only) — log in as a *second* user, attempt the same mutation against a target ID owned by the first user → MUST be 404 (not 403, not 200), and the target must be unchanged. See worked example below.
9. **Garbage UUID** — same endpoint with `id=not-a-uuid` → 404 (rejects early without DB roundtrip). Same endpoint with `id=00000000-0000-0000-0000-000000000000` → 404.

## Worked example: auth round-trip (Payntra 2026-07-04)

```bash
# 1. Negative: empty body → 400 with Zod issues
curl -sS -X POST https://payntra.terrybot.top/api/auth/login \
  -H 'Content-Type: application/json' -d '{}' \
  -w '\nHTTP %{http_code}\n'
# Expected: 400 {"error":"invalid_input","issues":[...]}

# 2. Negative: bad creds → 401 (constant-time padded to avoid enumeration)
curl -sS -X POST https://payntra.terrybot.top/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"nobody@nowhere.com","password":"BadPass1!"}' \
  -w '\nHTTP %{http_code}\n'
# Expected: 401 {"error":"invalid_credentials"}

# 3. Auth setup: login with valid creds, persist cookie
curl -sS -X POST https://payntra.terrybot.top/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"chris@madeat2am.in","password":"TestPass1!"}' \
  -c /tmp/payntra.cookies \
  -w '\nHTTP %{http_code}\n'
# Expected: 200 {"ok":true} + Set-Cookie: payntra_token=... HttpOnly Secure
# Verify cookie file:
cat /tmp/payntra.cookies
# Expected: lines starting with #HttpOnly_.payntra.terrybot.top

# 4. Positive: GET protected route with cookie
curl -sS https://payntra.terrybot.top/api/profile -b /tmp/payntra.cookies \
  -w '\nHTTP %{http_code}\n'
# Expected: 200 {"id":"...","email":"...","createdAt":"..."}

# 4b. Auth gate: same route WITHOUT cookie
curl -sS https://payntra.terrybot.top/api/profile -w '\nHTTP %{http_code}\n'
# Expected: 401 {"error":"unauthorized"}

# 5. State mutation: password change
curl -sS -X PUT https://payntra.terrybot.top/api/profile/password \
  -H 'Content-Type: application/json' -b /tmp/payntra.cookies \
  -d '{"currentPassword":"TestPass1!","newPassword":"NewPass2@"}' \
  -w '\nHTTP %{http_code}\n'
# Expected: 200 {"ok":true}

# 6. Confirm new password works, old doesn't
curl -sS -X POST https://payntra.terrybot.top/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"chris@madeat2am.in","password":"NewPass2@"}' -w '\nHTTP %{http_code}\n'
# Expected: 200

curl -sS -X POST https://payntra.terrybot.top/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"chris@madeat2am.in","password":"TestPass1!"}' -w '\nHTTP %{http_code}\n'
# Expected: 401
```

## Worked example: ownership-protected PATCH (Payntra 2026-07-04, Phase 5)

Any mutating endpoint whose path takes a row ID (`/api/<resource>/items/:id`) must enforce ownership. The protocol for the endpoint is identical to the auth round-trip above, with three extra rows: cross-user negative, garbage UUID, and **state verification after the attack**.

```bash
# Setup: log in as the legitimate owner
rm -f /tmp/owner.cookies
curl -sS -X POST https://payntra.terrybot.top/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"chris@madeat2am.in","password":"TestPass1!"}' \
  -c /tmp/owner.cookies -w '\nlogin: %{http_code}\n'
# Expected: 200, cookie persisted

# Read the ledger to grab a real item ID owned by chris
TARGET_ID=$(curl -sS https://payntra.terrybot.top/api/ledger/2026-07 \
  -b /tmp/owner.cookies | jq -r '.items[0].id')
echo "target: $TARGET_ID"

# Happy paths (all 200, payload echoes the updated row)
curl -sS -X PATCH https://payntra.terrybot.top/api/ledger/items/$TARGET_ID \
  -H 'Content-Type: application/json' -b /tmp/owner.cookies \
  -d '{"status":"PAID"}' -w '\n%{http_code}\n'

curl -sS -X PATCH https://payntra.terrybot.top/api/ledger/items/$TARGET_ID \
  -H 'Content-Type: application/json' -b /tmp/owner.cookies \
  -d '{"notes":"paid via DBS PayLah"}' -w '\n%{http_code}\n'

# Negative cases (all 400)
curl -sS -X PATCH https://payntra.terrybot.top/api/ledger/items/$TARGET_ID \
  -H 'Content-Type: application/json' -b /tmp/owner.cookies -d '{}' -w '\n%{http_code}\n'
curl -sS -X PATCH https://payntra.terrybot.top/api/ledger/items/$TARGET_ID \
  -H 'Content-Type: application/json' -b /tmp/owner.cookies \
  -d '{"status":"MAYBE"}' -w '\n%{http_code}\n'
curl -sS -X PATCH https://payntra.terrybot.top/api/ledger/items/$TARGET_ID \
  -H 'Content-Type: application/json' -b /tmp/owner.cookies \
  -d '{"amount":-50}' -w '\n%{http_code}\n'

# Garbage UUID → 404 (no DB roundtrip; route validates format first)
curl -sS -X PATCH https://payntra.terrybot.top/api/ledger/items/not-a-uuid \
  -H 'Content-Type: application/json' -b /tmp/owner.cookies \
  -d '{"status":"PAID"}' -w '\n%{http_code}\n'
# Expected: 404 not_found

# Non-existent UUID → 404 (real DB lookup, ownership chain returns nothing)
curl -sS -X PATCH https://payntra.terrybot.top/api/ledger/items/00000000-0000-0000-0000-000000000000 \
  -H 'Content-Type: application/json' -b /tmp/owner.cookies \
  -d '{"status":"PAID"}' -w '\n%{http_code}\n'

# No auth → 401
curl -sS -X PATCH https://payntra.terrybot.top/api/ledger/items/$TARGET_ID \
  -H 'Content-Type: application/json' \
  -d '{"status":"PAID"}' -w '\n%{http_code}\n'

# ── THE CROSS-USER ATTACK ───────────────────────────────────────
# Create an intruder user (seed directly into DB if no signup endpoint yet).
# See "Creating test users in the DB" below — bcrypt-hash the password first,
# then INSERT, then log them in.

HASH=$(ssh -i ~/.ssh/baymax_dev_vps deploy@147.79.18.32 \
  "sudo -n docker exec payntra-app node -e \"const b=require('bcryptjs');b.hash('TestPass1!',10).then(h=>console.log(h))\"")
ssh -i ~/.ssh/baymax_dev_vps deploy@147.79.18.32 \
  "sudo -n docker exec payntra-db psql -U payntra -d payntra -c \
   \"INSERT INTO users (email, password_hash) VALUES ('intruder@madeat2am.in', '$HASH');\""

# Log in as the intruder
rm -f /tmp/intruder.cookies
curl -sS -X POST https://payntra.terrybot.top/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"intruder@madeat2am.in","password":"TestPass1!"}' \
  -c /tmp/intruder.cookies -w '\nlogin: %{http_code}\n'

# Try to mutate chris's item — MUST be 404 (not 403)
curl -sS -X PATCH https://payntra.terrybot.top/api/ledger/items/$TARGET_ID \
  -H 'Content-Type: application/json' -b /tmp/intruder.cookies \
  -d '{"status":"PAID","notes":"OWNED BY ATTACKER"}' -w '\n%{http_code}\n'
# Expected: 404 {"error":"not_found"}

# CRITICAL VERIFICATION: re-read chris's item and confirm the attack didn't land
curl -sS https://payntra.terrybot.top/api/ledger/2026-07 -b /tmp/owner.cookies \
  | jq --arg id "$TARGET_ID" '.items[] | select(.id == $id)'
# Expected: notes from the legitimate owner, status from the legitimate owner,
# amount from the legitimate owner — NOTHING from intruder's payload.

# Cleanup the intruder
ssh -i ~/.ssh/baymax_dev_vps deploy@147.79.18.32 \
  "sudo -n docker exec payntra-db psql -U payntra -d payntra -c \
   \"DELETE FROM users WHERE email = 'intruder@madeat2am.in';\""
```

**Two design decisions baked into this example that you must replicate:**

1. **404 instead of 403** for cross-user access. A 403 confirms the resource exists in someone else's account, which is an enumeration leak. Returning 404 (with the same shape as "truly not found") is the only safe choice. The Payntra route does not distinguish between "no such id" and "id belongs to someone else" — both produce identical 404 responses.

2. **Atomic ownership check in the SQL**, not in application code. The PATCH route calls one statement:

   ```sql
   UPDATE ledger_items li
   SET status = $1, notes = $2, amount = $3
   FROM monthly_ledgers ml
   WHERE li.ledger_id = ml.id
     AND ml.user_id = $4
     AND li.id = $5
   RETURNING li.id, li.name, li.amount, li.status, li.notes, li.created_at
   ```

   `WHERE ml.user_id = $4` is the ownership check. If the item doesn't belong to the requester, the WHERE filters it out, `RETURNING` produces zero rows, and the route returns 404. **One roundtrip, no TOCTOU window, no enumeration leak.** The earlier code review lesson "think before coding" + the verification step above together catch this — don't ship a PATCH endpoint without it.

## Worked example: templates CRUD round-trip (Payntra 2026-07-04, Phase 6)

A simple GET/POST/PATCH/DELETE cycle for the most common resource pattern. Includes the **pure-template-fallback** verification, which is the load-bearing assertion that the rollover engine correctly distinguishes "no prior month → use templates" from "prior month exists → clone it".

```bash
# List existing templates (200, returns the lifetime baseline)
curl -sS https://payntra.terrybot.top/api/templates \
  -b /tmp/payntra.cookies -w '\nGET: %{http_code}\n'

# Create a new one (201, echoes the inserted row)
curl -sS -X POST https://payntra.terrybot.top/api/templates \
  -H 'Content-Type: application/json' -b /tmp/payntra.cookies \
  -d '{"name":"Netflix","defaultAmount":17.98,"isActive":true}' \
  -w '\nPOST: %{http_code}\n'
# Save the returned id
TID=$(curl -sS -X POST https://payntra.terrybot.top/api/templates \
  -H 'Content-Type: application/json' -b /tmp/payntra.cookies \
  -d '{"name":"Spotify"}' | jq -r '.template.id')

# PATCH (200, reflects updates)
curl -sS -X PATCH https://payntra.terrybot.top/api/templates/$TID \
  -H 'Content-Type: application/json' -b /tmp/payntra.cookies \
  -d '{"name":"Spotify Premium","defaultAmount":22.99}' -w '\nPATCH: %{http_code}\n'

# Toggle is_active — first call flips true→false, second false→true
curl -sS -X POST https://payntra.terrybot.top/api/templates/$TID/toggle \
  -b /tmp/payntra.cookies -w '\ntoggle 1: %{http_code}\n'
curl -sS -X POST https://payntra.terrybot.top/api/templates/$TID/toggle \
  -b /tmp/payntra.cookies -w '\ntoggle 2: %{http_code}\n'

# DELETE (204 No Content)
curl -sS -X DELETE https://payntra.terrybot.top/api/templates/$TID \
  -b /tmp/payntra.cookies -w '\nDELETE: %{http_code}\n'

# Idempotency: DELETE again → 404 (not 204, not 200)
curl -sS -X DELETE https://payntra.terrybot.top/api/templates/$TID \
  -b /tmp/payntra.cookies -w '\nDELETE 2nd: %{http_code}\n'

# Validation negative cases (all 400)
curl -sS -X POST https://payntra.terrybot.top/api/templates \
  -H 'Content-Type: application/json' -b /tmp/payntra.cookies \
  -d '{"defaultAmount":100}' -w '\nno name: %{http_code}\n'        # 400 "Required"
curl -sS -X POST https://payntra.terrybot.top/api/templates \
  -H 'Content-Type: application/json' -b /tmp/payntra.cookies \
  -d '{"name":"X","defaultAmount":-50}' -w '\nneg amt: %{http_code}\n' # 400 "non-negative"
curl -sS -X PATCH https://payntra.terrybot.top/api/templates/$TID \
  -H 'Content-Type: application/json' -b /tmp/payntra.cookies \
  -d '{}' -w '\nempty patch: %{http_code}\n'                          # 400 "at least one field"

# Garbage UUID → 404 (regex pre-check, no DB roundtrip)
curl -sS -X PATCH https://payntra.terrybot.top/api/templates/not-a-uuid \
  -H 'Content-Type: application/json' -b /tmp/payntra.cookies \
  -d '{"name":"X"}' -w '\nbad uuid: %{http_code}\n'

# No auth → 401
curl -sS https://payntra.terrybot.top/api/templates -w '\nno auth: %{http_code}\n'

# Cross-user attack — same pattern as the PATCH example below. Log in
# as a freshly-created intruder user, attempt to PATCH/DELETE/TOGGLE
# chris's template id → MUST be 404, target must be unchanged.

# ── THE TEMPLATE FALLBACK VERIFICATION (load-bearing) ──────────
# This is the rollover engine's other half: when NO prior month
# exists, the engine clones active expense_templates into the new
# ledger. Worth a dedicated test because the contract is subtle:
# `default_amount` from the template becomes the ledger item's
# amount, NOT the prior month's amount.

# Step 1: confirm the template's default_amount is what we expect
ssh -i ~/.ssh/baymax_dev_vps deploy@147.79.18.32 \
  "sudo -n docker exec payntra-db psql -U payntra -d payntra -t -A \
   -c \"SELECT name, default_amount FROM expense_templates \
       WHERE user_id=(SELECT id FROM users WHERE email='chris@madeat2am.in');\""

# Step 2: delete ALL of chris's monthly_ledgers (no prior month exists)
ssh -i ~/.ssh/baymax_dev_vps deploy@147.79.18.32 \
  "sudo -n docker exec payntra-db psql -U payntra -d payntra -c \
   \"DELETE FROM monthly_ledgers \
    WHERE user_id=(SELECT id FROM users WHERE email='chris@madeat2am.in');\""

# Step 3: GET a far-future month — triggers initialization, MUST fall back to templates
curl -sS https://payntra.terrybot.top/api/ledger/2027-03 \
  -b /tmp/payntra.cookies -w '\nGET 2027-03: %{http_code}\n'
# Expected: 201 {"created":true,"items":[{"name":"...","amount":<from template>,"status":"PENDING","notes":null}]}
# Critical assertion: amount == template.default_amount, notes is null
# (templates don't carry notes; cloned prior months DO carry notes verbatim)
```

**Why the fallback assertion matters:** the rollover engine has two paths and they're NOT equivalent. Path A (prior month exists) clones the prior month's *item values*, which may have drifted from the templates via PATCH. Path B (no prior month) clones the template's `default_amount` directly. A user editing a template expecting all future months to use the new amount is depending on Path B firing for every new month they open — that's the load-bearing UX of the rollover engine.

## Worked example: forgot/reset password flow

```bash
# 1. Trigger forgot → always 200 (no user enumeration)
curl -sS -X POST https://payntra.terrybot.top/api/auth/forgot-password \
  -H 'Content-Type: application/json' \
  -d '{"email":"chris@madeat2am.in"}' -w '\nHTTP %{http_code}\n'
# Expected: 200 {"ok":true}

# 2. SMTP verification — DB state is authoritative, not the email inbox.
#    Read the reset_secret back from the DB to use it:
RESET_SECRET=$(ssh -i ~/.ssh/baymax_dev_vps deploy@147.79.18.32 \
  "sudo -n docker exec payntra-db psql -U payntra -d payntra -t -A \
   -c \"SELECT reset_secret FROM users WHERE email='chris@madeat2am.in';\"" \
  | tr -d '[:space:]')
# CRITICAL: tr -d '[:space:]' — the psql output has a trailing newline that
# breaks Zod's min(64) check otherwise.
echo "secret length: ${#RESET_SECRET}"   # Must print 64

# 3. Reset with valid secret
curl -sS -X POST https://payntra.terrybot.top/api/auth/reset-password \
  -H 'Content-Type: application/json' \
  -d "{\"secret\":\"$RESET_SECRET\",\"newPassword\":\"Reset3#pass\"}" \
  -w '\nHTTP %{http_code}\n'
# Expected: 200 {"ok":true}

# 4. Reuse same secret → 410 Gone (single-use + 5-min TTL)
curl -sS -X POST https://payntra.terrybot.top/api/auth/reset-password \
  -H 'Content-Type: application/json' \
  -d "{\"secret\":\"$RESET_SECRET\",\"newPassword\":\"Another4#pass\"}" \
  -w '\nHTTP %{http_code}\n'
# Expected: 410 {"error":"link_expired_or_used"}

# 5. Login with the new reset password
curl -sS -X POST https://payntra.terrybot.top/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"chris@madeat2am.in","password":"Reset3#pass"}' \
  -w '\nHTTP %{http_code}\n'
# Expected: 200
```

## Creating test users in the DB

In early phases there's no signup endpoint, so to test the login flow you need to seed a user directly. Two paths:

**Option A: shell into the app container and hash with bcryptjs**

```bash
# Get a real bcryptjs hash for the password you want
ssh -i ~/.ssh/baymax_dev_vps deploy@147.79.18.32 \
  "sudo -n docker exec payntra-app node -e \"const b=require('bcryptjs');b.hash('TestPass1!',10).then(h=>console.log(h))\""
# Output: $2a$10$s8Uz3URU/CX5/mnssoQ47u9EF/E3k5CYDKx.GyQ4EIP9MwIQ46QnC

# Insert (or update) the user
ssh -i ~/.ssh/baymax_dev_vps deploy@147.79.18.32 \
  "sudo -n docker exec payntra-db psql -U payntra -d payntra \
   -c \"INSERT INTO users (email, password_hash) VALUES ('chris@madeat2am.in', '\$2a\$10\$s8Uz3URU/...') ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash;\""
```

**Option B: ship a `/api/auth/register` endpoint in Phase 0.** The PRD literally says FR-1.1 "Sign Up/In" — so signup is in scope. If your PRD doesn't mention signup, either it's a closed beta or you'll need this endpoint eventually anyway.

## Pitfalls in the verification protocol

| Pitfall | Symptom | Fix |
|---|---|---|
| `psql -t -A` output has trailing newline | Reset secret Zod-rejected as `<64` chars | `tr -d '[:space:]'` after the SELECT |
| SMTP send returns silently with no error log | "Did the email actually send?" | DB state is authoritative; check `reset_secret IS NOT NULL` |
| `wget` healthcheck inside alpine container fails | Container shows "unhealthy" even though app is fine | Use `127.0.0.1` not `localhost` (covered in pitfall K of parent skill) |
| Cookie domain mismatch | Set-Cookie ignored, no cookie persisted | Cookie `domain` must match the public hostname (e.g. `payntra.terrybot.top`, NOT `.terrybot.top` or empty) |
| HTTPS-only cookies blocked during local dev | `curl http://localhost:...` returns no cookie | Use `https://` for the public URL OR set `COOKIE_SECURE=false` in `.env` for local dev only |
| `app.log.info()` success line missing | Hard to confirm SMTP send | Check DB state OR add `app.log.info({msgId: info.messageId})` after `sendMail` to capture the SMTP message ID |
| Curl cookie file shows `0.0.0.0` instead of hostname | Cookie not scoped correctly | Cookie must have explicit `domain` in the Set-Cookie header; verify with `curl -v` |
| Mutating endpoint returns 403 on other-user resource | User enumeration leak: an attacker learns the UUID exists in someone else's account | Return **404 instead of 403** — never confirm an object exists outside the requester's tenant. The atomic-ownership pattern (next row) makes this cheap. |
| Two SQL roundtrips: `SELECT … WHERE user_id = $1` then `UPDATE …` | TOCTOU race between check and update; two roundtrips; leaks 200 vs 403 distinction | Single statement: `UPDATE target SET … FROM owner_table o WHERE target.id = $X AND target.owner_id = o.id AND o.user_id = $Y … RETURNING *`. One roundtrip, atomic, no TOCTOU, zero rows returned → route returns 404. Verified 2026-07-04 (Payntra `updateLedgerItem`). |
| Route trusts `req.params.id` and queries DB before UUID regex check | Garbage IDs waste a DB roundtrip and show up as 500 errors in logs | Validate UUID format in the route (regex pre-check), return 404 before touching the DB. Cheap, cleaner logs, faster 404. |
| Skipped the "re-read after attack" verification step | Code looks correct, smoke test only checked status code 404, but payload actually overwrote the row in some race condition | After the cross-user negative test, **re-GET the target with the legitimate owner's cookie and diff against pre-attack state**. The state verification is the only thing that proves the mutation was rejected, not just hidden behind a status code. |
| Asserting only the status code on validation failures, not the Zod issue text | A bug in the Zod schema ships to prod because the generic "invalid_input" message looked correct | The 400 message should include the Zod issue text (`amount must be a non-negative number`). If the message is generic, drill into why the schema didn't catch it. |
| Bcrypt hash containing `$` triggers bash variable expansion inside `docker exec … -c "INSERT … '$HASH'"` | INSERT succeeds with empty/corrupted hash, login fails with cryptic 401 | Pipe SQL via heredoc / `<<<` instead of `-c`. Never inline a bcrypt hash in a `docker exec psql -c` command line. Pattern: `docker exec -i payntra-db psql … <<< "INSERT … VALUES ('intruder@…', '\$2a\$10\$…');"`. Verified 2026-07-04 (Payntra Phase 5 intruder test). |
| Verifying template fallback while a prior month exists | Test passes locally but doesn't prove the fallback fired — the engine might have cloned from the prior month instead | `DELETE FROM monthly_ledgers WHERE user_id = …` before the GET. The `created: true` response with `notes: null` and `amount == template.default_amount` is the proof the fallback fired. Verified 2026-07-04 (Payntra Phase 6). |
| `docker cp /tmp/insert.sql payntra-db:/tmp/…` fails with `lstat: no such file or directory` | The remote /tmp path is wrong (often perms or path); INSERT never runs | Use `docker exec -i payntra-db psql … <<< "INSERT …"` instead — works from the container's stdin without filesystem round-trips. |

## What this protocol catches that unit tests miss

- Cookie domain / Secure flag mismatches (tests use `localhost` which has no domain)
- Caddy reverse_proxy routing (only manifests on the public URL)
- Real Postgres connection (test DB may differ in charset, time zone, extensions)
- Real SMTP creds (mocked in unit tests)
- TLS handshake + cert chain (off by default in dev)
- DNS propagation (no DNS in unit tests)
- Webhook HMAC signature validation (only real GitHub sends real signatures)

## Cost on the wire

Each positive assertion is ~5s (TLS handshake + DB roundtrip). A full auth round-trip suite (login → cookie → profile → change pw → re-login → forgot → DB read → reset → reuse-410 → new login) is about 12 curl calls, runs in ~30s, and proves more than 50 unit tests.

Run it as the last step of every phase. If anything returns the wrong status code, you have a real bug, not a test-env mismatch.