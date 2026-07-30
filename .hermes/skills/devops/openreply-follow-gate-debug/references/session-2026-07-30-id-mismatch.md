# OpenReply Follow-Gate Debug — Session Notes Part 2 (2026-07-30, ID Mismatch)

Continuation of the 2026-07-30 investigation. After the token-validity issue
from Part 1 was resolved (OAuth reconnection + verify-ig-token.sh exit 0),
DMs STILL didn't fire. This part documents the **second** root cause that was
missed initially — an Instagram ID type mismatch between webhooks and the DB.

## TL;DR — Run ALL three probes, in order, before declaring victory

```bash
# Layer 1 — is the token valid?
bash scripts/verify-ig-token.sh

# Layer 1.5 — does it have the right permissions?
bash scripts/probe-permission-gap.sh   # not bundled yet — see Part 1 reference

# Layer 1.7 — is the DB instagramId the type webhooks actually deliver?
bash scripts/probe-id-mismatch.sh
```

If `probe-id-mismatch.sh` exits 1, the fix is a one-line SQL update (see below).
**Do not debug worker logic until all three probes pass.**

## What was wrong

The OAuth callback at `app/api/instagram/callback/route.ts` stores:
```ts
const instagramId = userInfo.user_id ?? userInfo.id;
```

`getUserInfo()` queries `https://graph.instagram.com/v21.0/me?fields=id,user_id,...`
and returns BOTH:
```json
{ "id": "27821852394097749", "user_id": "17841444703583862", "username": "cyber.slide" }
```

- `id` = Instagram-scoped user ID — what Meta delivers in webhook `entry.id`
- `user_id` = Business account ID — what `/<USER_ID>/media` and conversations
  endpoints accept

The `userInfo.user_id ?? userInfo.id` expression stores `user_id` (the
Business account ID) by default. The worker then queries:
```ts
prisma.automation.findMany({
  where: {
    instagramAccount: { instagramId: instagramAccountId },  // from entry.id
  }
})
```

Webhook delivers `entry.id = 27821852394097749`. DB stores `instagramId = 17841444703583862`.
Query returns `[]`. Worker loops over zero automations, does nothing, logs
`[DM Worker] Job ... completed`. **No errors. No OperationalEvent. Silent no-op.**

## The test webhook trick — what finally surfaced it

Rather than wait for a real Instagram comment (and wonder if Meta was even
delivering webhooks), I injected a fake webhook with known IDs and watched
the full pipeline. Recipe that worked:

```js
// Build payload with UNIQUE comment_id (BullMQ dedup trap — see below)
const commentId = "test_comment_" + Date.now();
const commenterId = "test_user_id_" + Date.now();
const payload = JSON.stringify({
  object: "instagram",
  entry: [{
    id: "27821852394097749",          // IG-scoped ID — what webhooks actually send
    time: Date.now(),
    changes: [{
      field: "comments",
      value: {
        comment_id: commentId,
        media_id: "18107701655106615",  // the campaign post
        text: "test",                   // matches the campaign keyword
        from: { id: commenterId, username: "manual_test_user" }
      }
    }]
  }]
});

// HMAC-SHA256 with FACEBOOK_APP_SECRET (not WEBHOOK_VERIFY_TOKEN!)
const signature = "sha256=" + createHmac("sha256", FACEBOOK_APP_SECRET).update(payload).digest("hex");

await fetch("https://openreply.terrybot.top/api/webhook", {
  method: "POST",
  headers: { "Content-Type": "application/json", "x-hub-signature-256": signature },
  body: payload
});
```

**The first tell:** WebhookEvent row created with `status=PROCESSED`. Queue briefly shows `waiting=1`, then drains. Worker logs:
```
[DM Worker] Job comment_27821852394097749_test_comment_manual_123 completed
```
…and that's it. **No DmLog row. No Meta API error.** This is the mismatch signature — the worker thinks it succeeded but did nothing.

After updating `instagramId` to `27821852394097749`, sending a fresh test webhook (with a NEW unique `comment_id`) produced:
```
[DM Worker] Public comment reply failed: Meta API Error 100: ... Object with ID '<FAKE_COMMENT_ID>' does not exist, cannot be loaded due to missing permissions, or does not support this operation
[DM Worker] Job comment_27821852394097749_test_comment_<TS> failed (attempt 1): The requested user cannot be found.
```

The "Object does not exist" + "user cannot be found" errors are **expected and GOOD** — they prove the worker reached the Meta send layer. The fake IGSIDs (`test_user_id_<TS>`) don't exist on Instagram, so Meta rejects the DM attempt. If we don't see these errors, the lookup is still broken.

## The fix

```sql
-- One-line fix — align DB with what webhooks deliver
UPDATE "InstagramAccount"
SET "instagramId" = '27821852394097749'   -- the /me.id field (NOT user_id)
WHERE "instagramId" = '17841444703583862'; -- the Business account ID
```

Or via the worker container:
```bash
ssh dev-vps 'docker exec openreply-postgres-1 psql -U openreply -d openreply -c \
  "UPDATE \"InstagramAccount\" SET \"instagramId\" = '\''<NEW_ID>'\'' WHERE \"instagramId\" = '\''<OLD_ID>'\''"'
```

## Two additional pitfalls surfaced this session

### 1. BullMQ jobId dedup trap

The webhook handler sets `jobId: "comment_<instagramAccountId>_<commentId>"`. If
you send two test webhooks with the **same hardcoded** `comment_id`, the second
is silently dropped as a duplicate. The queue stays empty. You assume the fix
didn't work. **Always use a unique `comment_id` per test run:**
```js
const commentId = "test_comment_" + Date.now();
```

### 2. Two distinct IDs in `/me` response

If you change the OAuth callback to store `userInfo.id` (the IG-scoped ID)
instead of `userInfo.user_id`, the user_id-accepting endpoints (conversations,
media queries keyed off `user_id`) will need an additional translation step.
For this deploy, the simpler fix was the one-line DB update. For future code
changes, consider storing BOTH IDs (`instagramId` and `businessAccountId`) in
the schema to avoid future drift.

## What still needs operator action

The `probe-id-mismatch.sh` fix unblocks webhook-triggered DMs. The polling
safety net (`lib/polling/comment-reconciler.ts`) still depends on the
`/comments` endpoint returning comments, which still returns empty due to
the **Layer 1.5 permission gap** documented in Part 1. So:

- **Webhooks work now** — Meta delivers a comment, system fires the DM
- **Polling does not work yet** — operator must reconnect Instagram and tick
  ALL permission boxes on the consent screen

If the operator wants belt-and-suspenders (no missed comments), both fixes
are needed. The webhook-only fix is enough for the immediate "user reported
the DM isn't firing" symptom.

## Recipes that worked

### Send test webhook (canonical, see `scripts/send-test-webhook.mjs`)

The script auto-fetches `FACEBOOK_APP_SECRET` from the VPS env file, fetches
the IG-scoped ID from `/me`, generates a unique `comment_id`, and fires the
signed POST. Output includes "what to look for" hints.

### Detect ID mismatch (see `scripts/probe-id-mismatch.sh`)

Compares `id` and `user_id` from `/me` against the value stored in DB.
Exit 0 = match, exit 1 = mismatch (with the exact UPDATE statement to fix it).

### Inspect webhook & worker state quickly

```bash
# Recent webhook events
ssh dev-vps 'docker exec openreply-postgres-1 psql -U openreply -d openreply -c \
  "SELECT id, status, \"createdAt\" FROM \"WebhookEvent\" ORDER BY \"createdAt\" DESC LIMIT 5"'

# Queue depth + worker heartbeat
curl -sS https://openreply.terrybot.top/api/health | python3 -m json.tool

# Last 20 worker log lines (filter npm noise)
ssh dev-vps 'docker logs --since 1m openreply-worker-1 2>&1 | grep -v "npm " | tail -20'
```

### Reset worker without losing queue

```bash
ssh dev-vps 'cd /srv/projects/openreply && docker compose restart worker'
# NOTE: 'restart' preserves the in-flight queue; '--force-recreate' drops it
```

## Decision tree (combined Parts 1 & 2)

```
"DMs not firing"
├── Run verify-ig-token.sh
│   ├── Exit 0 ───────────────────────────────────────────► Layer 1.5
│   ├── Exit 1 (code 190) ────────────────────────────────► Reconnect OAuth
│   └── Exit 2 (code 101) ─────────────────────────────────► Operator: Meta dashboard
├── Layer 1.5: probe-permission-gap.sh (counts vs comments)
│   ├── counts > 0, comments empty ──────────────────────► Operator: reconnect, tick ALL boxes
│   └── counts > 0, comments visible ────────────────────► Layer 1.7
├── Layer 1.7: probe-id-mismatch.sh
│   ├── Exit 0 (DB matches scoped id) ───────────────────► Layer 2 (webhook delivery)
│   └── Exit 1 (mismatch) ────────────────────────────────► Run the UPDATE, then re-probe
├── Layer 2: send a test webhook (scripts/send-test-webhook.mjs)
│   ├── Worker logs "Public comment reply failed: ... Object does not exist" ─► OK!
│   └── Worker silent (no job log) ──────────────────────► Investigate worker code or DB
└── Real comment from secondary IG account ──► Should fire DM within seconds
```