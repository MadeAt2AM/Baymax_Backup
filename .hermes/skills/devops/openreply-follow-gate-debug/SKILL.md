---
name: openreply-follow-gate-debug
description: Debug OpenReply follow-gate DM failures when Require is on.
---

# Debug OpenReply Follow-Gate DM Failures

## Problem
"Require Follow" toggle ON but DMs do not fire (or any "DM not sent" symptom in OpenReply).

## Three Failure Layers — Diagnose Top-Down
Before touching worker code, **verify Meta API access works at all**. The 2026-07-30 session burned 10+ tool calls patching worker logic when the real culprit was an invalid Instagram access token rejected by Meta (code 190 "Cannot parse access token"). Symptom was identical: DMs not firing, no errors in worker logs.

**Layer 1 — Meta Authentication**: Can the worker talk to Meta?
**Layer 2 — Webhook Delivery**: Is Meta delivering events to us?
**Layer 3 — Worker Logic**: Does our processing do the right thing?

## Root Causes (in order of frequency)
1. **Invalid/expired/corrupted Instagram access token** — Meta returns code 190 ("Cannot parse access token") or code 190 subcode 463 ("Token expired"). Worker silently swallows the error in the polling safety net. **Sub-case 1b:** even a freshly regenerated token returns 190 because the Meta App itself is in a bad state (code 101 from `/oauth/access_token`). Not VPS-recoverable — operator must check the Meta developer dashboard.
2. **Webhook signature verification failure** — `FACEBOOK_APP_SECRET` or `INSTAGRAM_APP_SECRET` mismatch in env.
3. **Worker logic bug** — `requireFollow` or other guard not checked, keyword matcher misses, dedupe logic drops the comment.

## Diagnostic Steps (run on VPS, in this exact order)

### Step 0 — Verify Meta can authenticate (MOST OFTEN THE ROOT CAUSE)

Decrypt the stored Instagram access token and call Meta's `/me` endpoint directly. If this fails with code 190, **stop** — no amount of worker patching will help until the token is regenerated via OAuth.

```bash
# 1. Pull encrypted token from DB
ssh dev-vps 'docker exec openreply-postgres-1 psql -U openreply -d openreply -tA -c "SELECT \"accessToken\" FROM \"InstagramAccount\" LIMIT 1" > /tmp/enc_token.txt'

# 2. Decrypt using the worker's ENCRYPTION_KEY (aes-256-gcm: iv[16] || tag[16] || ciphertext)
#    Base64 the script, write to VPS, then run inside the web container so ENCRYPTION_KEY is set
cat > /tmp/decrypt.mjs << 'EOF'
import { createDecipheriv } from "crypto";
import fs from "fs";
const enc = fs.readFileSync(process.argv[2], "utf8").trim();
const E = process.env.ENCRYPTION_KEY;
const key = Buffer.from(E, "hex");
const combined = Buffer.from(enc, "base64");
const iv = combined.subarray(0, 16);
const tag = combined.subarray(16, 32);
const ct = combined.subarray(32);
const dec = createDecipheriv("aes-256-gcm", key, iv);
dec.setAuthTag(tag);
fs.writeFileSync(process.argv[3], Buffer.concat([dec.update(ct), dec.final()]).toString("utf8"));
EOF
B64=$(base64 -w 0 /tmp/decrypt.mjs)
ssh dev-vps "echo '$B64' | base64 -d > /tmp/dec.mjs && \
  docker cp /tmp/enc_token.txt openreply-web-1:/tmp/enc_token.txt && \
  docker cp /tmp/dec.mjs openreply-web-1:/tmp/dec.mjs && \
  docker exec openreply-web-1 node /tmp/dec.mjs /tmp/enc_token.txt /tmp/plain_token.txt && \
  docker cp openreply-web-1:/tmp/plain_token.txt /tmp/plain_token.txt"

# 3. Test with Meta — **use graph.instagram.com, NOT graph.facebook.com**
#    Instagram Graph API tokens are scoped to the Instagram endpoint. Hitting
#    graph.facebook.com with the same token returns code 190 even when the
#    token is fully valid for Instagram operations. This burned ~5 tool calls
#    in the 2026-07-30 session before the endpoint was switched.
TOKEN=$(cat /tmp/plain_token.txt)
ssh dev-vps "curl -sS 'https://graph.instagram.com/v21.0/me?access_token=$TOKEN' 2>&1 | head -200"

# PASS:  {"id":"27821852394097749","username":"cyber.slide"}  → token is valid
# FAIL:  {"error":{"code":190,...}}                            → token invalid
#        → Regenerate by reconnecting Instagram account in OpenReply dashboard OAuth flow
```

**Why this matters**: In the 2026-07-30 session, the token passed local decryption but Meta still rejected it. The encryption key in `.env` may have been rotated since the token was originally encrypted. The only fix is a fresh OAuth reconnection.

### Step 0.5 — Verify Meta App credentials (NEW 2026-07-30)

If Step 0 returned `code: 190` for a freshly regenerated token, the issue is upstream — the App itself is in a bad state at Meta. Probe directly:

```bash
ssh dev-vps 'APP_ID=$(grep INSTAGRAM_APP_ID /srv/projects/openreply/.env | cut -d= -f2); \
  APP_SECRET=$(grep INSTAGRAM_APP_SECRET /srv/projects/openreply/.env | cut -d= -f2); \
  curl -sS -X POST "https://graph.facebook.com/v21.0/oauth/access_token" \
    -d "client_id=$APP_ID" -d "client_secret=$APP_SECRET" \
    -d "grant_type=client_credentials"'
```

- `code: 101` → **App is suspended / deleted / in Development mode / unverified**. Not VPS-recoverable. Operator must go to developers.facebook.com.
- `code: 190` with valid App Secret → double-check secret value against Meta dashboard (one common cause: copy-paste dropped a trailing character).
- `{"access_token":"...", "token_type":"bearer"}` → App credentials valid; reconnect Instagram and re-run Step 0.

### Step 1 — Verify campaign state
```bash
ssh dev-vps 'docker exec openreply-postgres-1 psql -U openreply -d openreply -c "SELECT id, name, \"isActive\", \"requireFollow\", \"postId\", keywords FROM \"Automation\" WHERE \"isActive\" = true;"'
```
Note: table is `"Automation"` (capital A) and columns are PascalCase, not snake_case. Earlier sessions used lowercase table names and got "relation does not exist" errors.

### Step 1.5 — Detect permission gap via `comments_count` (NEW 2026-07-30)

If Layer 1 passes but the worker still doesn't process comments, test for the **permission gap pattern**: the token can see comment counts but cannot read actual comments. This happens when the OAuth scope list includes the permission but the operator didn't check all boxes on the consent screen, or the app isn't Live yet.

```bash
# Get a comment count via /me/media (uses instagram_business_basic — always granted)
ssh dev-vps 'TOKEN=$(docker exec openreply-web-1 cat /tmp/plain_token.txt); \
  curl -sS -G "https://graph.instagram.com/v21.0/27821852394097749/media" \
  --data-urlencode "access_token=$TOKEN" \
  --data-urlencode "fields=id,media_type,comments_count" \
  --data-urlencode "limit=5"'

# Then fetch comments on the campaign post (uses instagram_business_manage_comments)
ssh dev-vps 'TOKEN=$(docker exec openreply-web-1 cat /tmp/plain_token.txt); \
  curl -sS -G "https://graph.instagram.com/v21.0/<POST_ID>/comments" \
  --data-urlencode "access_token=$TOKEN" \
  --data-urlencode "fields=id,text,from,timestamp"'
```

**Permission gap signature:** `comments_count: 3` from media endpoint, **but** `/comments` endpoint returns `{"data": []}`. Token has metadata access but not comment read scope.

**Fix:** Reconnect Instagram in OpenReply settings. On the Instagram consent screen, ensure **all** permission checkboxes are checked (basic profile, messages, comments, insights) BEFORE clicking Authorize. A partial grant produces a token that can fetch counts but not content.

### Step 2 — Check OperationalEvent for sweep/poll errors
The comment reconciler **silently swallows Meta API errors** — only logs when something actually fires. Pull the full log:
```bash
ssh dev-vps 'docker exec openreply-postgres-1 psql -U openreply -d openreply -c "SELECT id, level, message, payload, \"createdAt\" FROM \"OperationalEvent\" ORDER BY \"createdAt\" DESC LIMIT 20"'
```
Look for `code: 190` in payload JSON — this confirms token rejection at the poll layer.

### Step 3 — Check webhook events in DB
```bash
ssh dev-vps "docker exec openreply-postgres-1 psql -U openreply -d openreply -c \"SELECT id, status, \\\"createdAt\\\" FROM \\\"WebhookEvent\\\" ORDER BY \\\"createdAt\\\" DESC LIMIT 10\""
```
- Empty result table → Meta is not delivering webhooks (app not Live, missing permissions, or wrong callback URL).
- Many rows with `status='PROCESSED'` but no `DmLog` entries → worker dropped them (logic bug or token error).

### Step 4 — Check worker logs for sweep activity
```bash
ssh dev-vps "docker logs --since 10m openreply-worker-1 2>&1 | tail -50"
```
The worker logs only `[DM Worker] Started` — sweep errors go to DB only. **Don't trust silent success.**
```

## Pre-Deployment Verification Gate

Before committing, pushing, rebuilding, or live-testing any follow-gate worker
diff, verify the **state machine**, not just the happy path.

```bash
cd /root/.hermes/projects/openreply/repo
npm test -- --run __tests__/dm-worker.test.ts
npm run typecheck
git diff --check
```

Capture the literal commands, stdout/stderr, exit codes, and current HEAD in a
dated `VERIFICATION-YYYY-MM-DD.md`. A site returning HTTP 200 only proves the
currently deployed revision is alive; it does not validate an uncommitted local
diff.

### Mandatory `processPostback` invariants

Review the code and add tests proving all of these before deployment:

1. Every identifier referenced by the postback path exists in
   `ProcessPostbackJob` and is destructured from `job.data`. A postback does
   **not** carry the original comment ID unless the queue contract explicitly
   adds it; do not reuse a comment-time API argument by accident.
2. The follow-status result is handled as a three-state value:
   - `false` → re-prompt on a real button tap, silent return on read fallback.
   - `true` → continue to the single canonical reward-delivery path.
   - `null`/unverifiable → follow the documented fail-open policy through that
     same canonical path; do not create a second ad-hoc send branch.
3. A successful branch sends the reward **once**. If a branch sends directly,
   it must return; preferably it should not send directly at all and should
   fall through once to the shared quota, fallback, logging, and error path.
4. `reserveWorkspaceDMSend`, `releaseWorkspaceDMReservation`, `DmLog.upsert`,
   tracked-link fallback, and dedupe behaviour execute exactly once per reveal.
5. Tests cover a `followcheck:` button tap for follower, non-follower, and
   unverifiable status, plus the existing read-fallback cases. Comment-time
   prompt tests alone do not exercise `processPostback`.

**Static red flags:** an undefined `commentId` inside `processPostback`, a
follower branch that calls `sendDirectMessageWithLinkButton` before the shared
send block, or an `else` that groups `true` and `null` into a direct-send branch.
Treat any of these as not deployable until the focused tests and typecheck pass.

## Fix

### Fix A — Token regeneration (most common)

If Step 0 failed with code 190:
1. In OpenReply dashboard → Settings → Disconnect Instagram
2. Reconnect Instagram via OAuth (this generates a fresh token encrypted with current ENCRYPTION_KEY)
3. Re-run Step 0 to verify Meta accepts the new token
4. Re-test the comment-to-DM flow

### Fix B — Worker logic patch

Only if Step 0 passes and worker is dropping comments. Patch `/srv/projects/openreply/lib/queue/dm-worker.ts` line 407 (the `getUserFollowStatus` check). The original buggy line:

```ts
sendFollowPrompt = alreadyFollows !== true;  // BUG: treats null (unknown) as "not following"
```

Corrected (handles three states: true=follower, false=not, null=unknown → don't prompt):

```ts
sendFollowPrompt = alreadyFollows === false;
```

Redeploy:
```bash
ssh dev-vps "cd /srv/projects/openreply && docker compose up -d --force-recreate worker"
```

## Verification
1. Redeploy the worker after the patch.
2. Post a comment from a secondary IG account with the campaign keyword.
3. Check worker logs for `status=SENT` dmLog entry.
4. Confirm the DM arrives in the recipient's Instagram inbox.

## Common Pitfalls
- **`require_follow` column missing** from `Automation` table — run `npx prisma migrate deploy` if so.
- **Worker code not rebuilt** — always redeploy the **worker** container after patching dm-worker.ts.
- **Campaign `instagram_account_id` does not match** any connected IG account in the DB.
- **Invalid Instagram access token** (code 190) — encryption key may have been rotated since token was stored; only fix is OAuth reconnection. Worker swallows these errors silently — OperationalEvent is the only signal.
- **Meta App in bad state (code 101)** — the freshly regenerated token still returns 190 because the App itself is suspended/in-Dev-mode/unverified at Meta. Not VPS-recoverable; see Step 0.5 above.
- **Poll safety net silently passes** — `reconcileComments()` only writes OperationalEvent when `stat.enqueued > 0 || stat.errors.length > 0`. No DB entries ≠ success. Always pull errors from `OperationalEvent.payload` (JSON column, contains the raw Meta error code).
- **PostgreSQL table casing**: tables are PascalCase (`"Automation"`, `"WebhookEvent"`, `"InstagramAccount"`, `"DmLog"`, `"OperationalEvent"`) and columns are PascalCase too. Lowercase queries return "relation does not exist" — wasted debugging time.
- **Token in `.env` and `/srv/secrets/openreply.env` can drift** — if SMTP_PASSWORD or similar secrets get blanked, auth-related features fail silently. Always grep both files together when diagnosing.
- **Worker process restart doesn't redeploy code** — must `docker compose up -d --force-recreate worker` (not just `restart`) to pick up file changes.
- **`graph.facebook.com` vs `graph.instagram.com` endpoint (NEW 2026-07-30)** — Instagram Graph API tokens are scoped to `graph.instagram.com`. Hitting `graph.facebook.com/v21.0/me` with the same token returns code 190 even when fully valid for Instagram operations. Always test against `graph.instagram.com` first when verifying an IG token.
- **Permission gap symptom (NEW 2026-07-30)** — token has metadata read scope but not content read scope (e.g. `instagram_business_basic` granted but `instagram_business_manage_comments` denied). Signature: `comments_count > 0` from `/me/media` endpoint, but `/comments` endpoint returns `{"data":[]}`. Fix: reconnect Instagram and ensure ALL permission checkboxes are ticked on the OAuth consent screen.
- **Token passed locally but Meta rejects (Layer 1a)** — `accessToken` decrypts cleanly with the current `ENCRYPTION_KEY`, but Meta returns code 190. Encryption key may have been rotated since the token was stored, or token is corrupted in DB. Only fix is OAuth reconnection.
- **Instagram ID type mismatch (NEW 2026-07-30 Part 2)** — Meta's `/me` returns two different IDs for the same account: `id` (Instagram-scoped, e.g. `27821852394097749`) and `user_id` (Business account, e.g. `17841444703583862`). Webhooks deliver `entry.id` which is the **scoped ID**, but the OAuth callback stores `userInfo.user_id` (Business account ID) by default. The worker's `findMany({ automation: { instagramId: <entry.id> } })` lookup silently returns empty → no DM, no errors, no OperationalEvent. **Signature:** `WebhookEvent.status=PROCESSED`, worker logs `[DM Worker] Job ... completed`, but `DmLog` table is empty. Fix: `UPDATE "InstagramAccount" SET "instagramId" = '<id_FROM_ME>'` to align with what webhooks actually deliver.
- **Test webhook jobId dedup trap (NEW 2026-07-30 Part 2)** — BullMQ `jobId` is set to `comment_<instagramAccountId>_<commentId>`. Sending two test webhooks with the same hardcoded `comment_id` will result in the second being silently dropped as a duplicate. Always use a unique `comment_id` per test run (`comment_test_<Date.now()>`). Symptom: worker doesn't log anything on the second run, queue stays empty, you think the fix didn't work.

- **Webhook not delivered even when token is valid and ID matches (NEW 2026-07-30 Part 3)** — confirmed via real Instagram comment from `made.at.2am` ("Test🔥", 43 min old) where the `WebhookEvent` table was empty and no OperationalEvent was generated. Token decrypted, passed `/me`, comment ID matched, but Meta NEVER sent the webhook. This is Layer 2 (webhook delivery), distinct from Layer 1 (auth) and Layer 1.7 (ID mismatch). Symptom: `WebhookEvent` table has only test-injected rows; **zero rows from real Meta deliveries**. Diagnostic: navigate to the post in a browser (no auth needed) and check if real comments are visible — if they exist but no webhook rows, Meta isn't delivering. Operator must verify in Meta Developer Dashboard → Products → Webhooks → Instagram → Comments subscription that the callback URL is subscribed and the `comments` field is selected. See Part 3 reference for the exact diagnostic sequence.
- **`VNC/cyberslide.terrybot.top` confusion trap (NEW 2026-07-30 Part 3)** — memory recalled a VNC at `cyberslide.terrybot.top` that was used last time. That setup is on a different VPS, not `147.79.18.32`. The local VPS only has `vnc-stack.service` + `vnc-websockify.service` for generic Chromium automation (not Instagram automation). Trying to use the local VNC for cookie-bearing Instagram accounts won't help — those cookies live on the OTHER VPS. Don't waste time spinning up the local VNC stack; check `pgrep websockify` on the OTHER host if cookie reuse is the goal.
- **Fake user/comment IDs in test webhooks are expected to fail (NEW 2026-07-30 Part 2)** — when sending test webhooks, `commenterId` and `commentId` are fake IGSIDs. Expect: `Meta API Error 100: ... Object with ID '<fake>' does not exist` (public reply attempt) and `The requested user cannot be found` (DM attempt). **These failure messages are the GOOD signal** — they prove the automation lookup succeeded and the worker reached the Meta send layer. No errors = lookup still broken.

## Lesson From 2026-07-30 Session (Part 1)
Diagnosed a 30+ minute follow-gate failure. Patched worker logic in three different places, redeployed twice, before discovering the actual root cause was an invalid Instagram access token that Meta rejected with code 190. The decrypted token passed local checks but Meta refused it. Lesson: **always verify Meta authentication FIRST before debugging worker logic**. The symptom ("DM not sent, no logs") is identical for token failures and code failures, but only token failures leave the worker logs completely silent.

## Lesson From 2026-07-30 Session (Part 2 — ID MISMATCH, NOT TOKEN)

After OAuth reconnection refreshed the token (and `verify-ig-token.sh` exited 0), DMs STILL did not fire. The actual root cause this session was a **silent Instagram ID type mismatch** — not auth, not permissions:

- Meta's `/me` endpoint returns **two different IDs** for the same Instagram Business account:
  - `id` = Instagram-scoped ID (`27821852394097749`) — what webhooks send in `entry.id` and what `/me/media` queries against
  - `user_id` = Business account ID (`17841444703583862`) — what `/<USER_ID>/media` and the `/conversations` endpoint accept
- The OAuth callback at `app/api/instagram/callback/route.ts` stores `userInfo.user_id ?? userInfo.id`, so by default it stores `user_id` (the Business account ID).
- BUT webhooks deliver `entry.id` as the Instagram-scoped ID (`id`), NOT `user_id`.
- The worker's automation lookup is `instagramAccount: { instagramId: instagramAccountId }` where `instagramAccountId` comes from `entry.id`. **This lookup always returns empty** when the stored ID is `user_id` and the webhook delivers `id`.
- Symptom: `WebhookEvent.status = PROCESSED`, queue job added, worker logs `[DM Worker] Job ... completed`, **but no `DmLog` row created** because the `findMany({ automation: ... })` returned `[]`.
- Zero errors. Zero OperationalEvent entries. Just silent no-op.

**Detection — the test webhook trick.** Send a fake webhook with a known `entry.id` and `comment_id`, check `WebhookEvent.status` and queue depth. If the queue drains but no `DmLog` appears, the lookup mismatch is the cause.

**Fix (one-liner):** update the stored `InstagramAccount.instagramId` from `user_id` to `id`:
```sql
UPDATE "InstagramAccount"
SET "instagramId" = '<IG_SCOPED_ID_FROM_ME_ID_FIELD>'
WHERE "instagramId" = '<BUSINESS_ACCOUNT_ID>';
```

**Verify the fix worked:** send another test webhook with a unique `comment_id` (not reused — see dedup trap below). Worker should now produce log lines like:
```
[DM Worker] Public comment reply failed: Meta API Error 100: ... Object with ID '<FAKE_COMMENT_ID>' does not exist
[DM Worker] Job comment_<IG_SCOPED_ID>_<COMMENT_ID> failed (attempt 1): The requested user cannot be found
```
The "Object does not exist" + "user cannot be found" messages prove the automation lookup succeeded — failures are now at the **Meta API send layer**, not the lookup layer.

**Probe both IDs in one call** to confirm the gap before applying the fix:
```bash
ssh dev-vps 'TOKEN=$(docker exec openreply-web-1 cat /tmp/plain_token.txt); \
  curl -sS -G "https://graph.instagram.com/v21.0/me" \
    --data-urlencode "fields=id,user_id,username" \
    --data-urlencode "access_token=$TOKEN"'
# Compare both IDs against the value in DB:
ssh dev-vps 'docker exec openreply-postgres-1 psql -U openreply -d openreply \
    -c "SELECT \"instagramId\" FROM \"InstagramAccount\""'
```

## Reusable Tools
- `scripts/verify-ig-token.sh` — Layer 1 token validity probe (run first).
- `scripts/probe-id-mismatch.sh` — compares `id` vs `user_id` from `/me` against DB-stored `instagramId`, flags mismatch.
- `scripts/send-test-webhook.mjs` — sends a properly HMAC-signed fake comment webhook to verify the full receive → queue → worker pipeline without needing a real Instagram comment.

## Session Notes
- `references/session-2026-07-30.md` — full investigation trace from this session: canonical decrypt-token recipe, Layer 1b (code 101) probe, and the rabbit holes (re-patching dm-worker.ts, reseeding SMTP_PASSWORD, redundant prisma migrate deploys, container restart loops) that wasted turns before the Layer 1 root cause was identified.
- `references/session-2026-07-30-id-mismatch.md` — Part 2 investigation trace covering the ID-type mismatch root cause (NOT a token issue). Includes the test-webhook-injection recipe, the jobId-dedup trap, and the worker-log signature that confirms the fix worked.
- `references/session-2026-07-30-webhook-delivery.md` — Part 3: confirms Layer 2 (Meta not delivering webhooks) as a distinct failure mode. Empirical signature: real comments exist publicly, WebhookEvent table contains only test-injected rows. Also covers the VNC confusion trap (memory recalled a `cyberslide.terrybot.top` VNC that's on a different VPS, not the dev-vps where OpenReply runs).
- `references/session-2026-07-30-end-to-end-success.md` — Part 4: documents the successful resolution (3 SENT DMs within one polling cycle after OAuth reconnect + ID-mismatch fix). Key new lessons: **Meta permission propagation is async (wait 5-10 min after OAuth reconnect before re-probing)**, the **polling safety net is a real recovery mechanism** (don't escalate to operator immediately when Layer 2 fails), and the final symptom-to-fix mapping table.
- `references/postback-verification-2026-08-06.md` — focused pre-deployment state-machine matrix and evidence-record format for `processPostback`; covers undefined queue fields, duplicate-send fall-through, three-state follow status, quota/log accounting, and the required button-tap tests.
