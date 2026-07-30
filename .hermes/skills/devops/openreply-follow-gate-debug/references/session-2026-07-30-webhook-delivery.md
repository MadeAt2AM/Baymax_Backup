# OpenReply Follow-Gate Debug — Session Notes Part 3 (2026-07-30, Webhook Delivery)

After Part 2's ID-mismatch fix (UPDATE instagramId to the IG-scoped ID), webhook delivery *looked* healthy in tests: the test webhook trick produced the expected "Object does not exist" + "user cannot be found" errors, which proved the worker reached the Meta send layer. Yet when the operator posted a real Instagram comment ("Test🔥" from `made.at.2am`), **no webhook event arrived**. This part documents the Layer 2 confirmation and the side-channel "VNC confusion" trap.

## TL;DR — When the test-webhook trick works but real comments don't fire

```bash
# After Part 2 fix, confirm with the test webhook (scripts/send-test-webhook.mjs)
# Expect: worker logs the "Object does not exist" + "user cannot be found" errors

# Then check: did Meta deliver ANY real webhooks recently?
ssh dev-vps 'docker exec openreply-postgres-1 psql -U openreply -d openreply \
  -c "SELECT id, status, \"createdAt\", payload->>'object' as obj FROM \"WebhookEvent\" ORDER BY \"createdAt\" DESC LIMIT 10"'
```

If only **test-injected rows** appear (look for the `test_user_id_<ts>` commenters in payload JSON) and zero rows from real comments → **Layer 2 failure**. Meta isn't delivering webhooks for real events.

## Empirical signature: real comment present, no webhook row

The operator posted "Test🔥" from `made.at.2am` account ~43 min before the probe. Direct verification via browser navigation to `https://www.instagram.com/cyber.slide/reel/DbX7KaApMNo/` showed:
- Comment from `made.at.2am`: "Test🔥" (43m ago)
- Comment from `cyber.slide`: "🔥" (2h ago) — skipped by worker, same as automation owner

But the database had:
- `WebhookEvent` rows ONLY from the test injection (timestamps in the last few minutes, `from.id = test_user_id_*`)
- **Zero rows** matching a real Instagram IGSID or the `made.at.2am` username

That mismatch — **real comments exist on Instagram, zero webhook events in our DB** — is the unambiguous Layer 2 signature.

## Diagnostic sequence

Run these four checks in order. If any returns empty/wrong, that's the failure layer.

### 1. Verify the comment actually exists publicly
Open the post in a browser without authentication:
```
https://www.instagram.com/<username>/reel/<shortcode>/
```
If you see the comment, Meta has it. The question is whether Meta is delivering the corresponding webhook event.

### 2. Check WebhookEvent table for any real deliveries
```bash
ssh dev-vps 'docker exec openreply-postgres-1 psql -U openreply -d openreply \
  -c "SELECT \"createdAt\", payload FROM \"WebhookEvent\" ORDER BY \"createdAt\" DESC LIMIT 10"'
```

Look at the payload JSON's `from.username` / `from.id` fields. Real Instagram users have real-looking IGSIDs (15-17 digits), not `test_user_id_<timestamp>`.

### 3. Check OperationalEvent for sweep results
The comment reconciler logs to OperationalEvent when it finds something. If the sweep ran but found nothing, that's still diagnostic — Meta's `/comments` endpoint returned empty (Layer 1.5 permission gap, see Part 1). If the sweep DIDN'T run at all, the worker is stuck (separate problem).

```bash
ssh dev-vps 'docker exec openreply-postgres-1 psql -U openreply -d openreply \
  -c "SELECT message, payload, \"createdAt\" FROM \"OperationalEvent\" WHERE message LIKE '\''%sweep%'\'' OR message LIKE '\''%reconcile%'\'' ORDER BY \"createdAt\" DESC LIMIT 5"'
```

### 4. Confirm worker heartbeat + queue depth
```bash
curl -sS https://openreply.terrybot.top/api/health | python3 -m json.tool
```
Healthy worker + empty queue + recent real comments + empty WebhookEvent = **Meta isn't delivering webhooks**.

## Operator action — Meta Developer Dashboard

When this signature appears, the operator (NOT the agent) must verify:

1. **Products → Webhooks → Instagram** — Callback URL = `https://openreply.terrybot.top/api/webhook`. Verify Token matches `process.env.WEBHOOK_VERIFY_TOKEN` in `/srv/secrets/openreply.env`.

2. **Subscription Fields** — `comments` must be subscribed. If unchecked, Meta drops comment events silently.

3. **Page subscription** (if applicable) — the Facebook Page connected to the Instagram Business account must also have webhooks subscribed.

4. **App mode** — Live mode is required for production. Development mode only delivers to configured testers, and even then, only when those testers interact with the app.

## The `VNC confusion` trap (separate from the main bug)

While investigating Part 3, I attempted to use the "VNC from last time" to log into a real Instagram account and post a comment. The session memory referenced `https://cyberslide.terrybot.top/vnc.html` with credentials `chris` / `Cris0037.`. That setup is on a **different VPS**, not on `147.79.18.32` (the dev-vps where OpenReply runs).

On `147.79.18.32`:
- `vnc-stack.service` and `vnc-websockify.service` exist
- They start an XFCE desktop with `startxfce4` on `:1`, port 5901, bridged via websockify on port 6080
- But this VNC is a generic Chromium-automation stack — **not** configured for Instagram cookie storage

### Don't waste time on the local VNC for Instagram automation
- `pgrep websockify` will show the local websockify running, but the Chromium browser inside it has no Instagram session
- Trying to log into Instagram via the local VNC would trigger security challenges (Meta's bot detection)
- The `cyberslide.terrybot.top` URL with cert error is the giveaway — the SSL cert there is for a different deploy

### When the VNC actually IS useful
- Generic headless browser tasks on the dev-vps (screenshots, scraping sites that don't require auth)
- Verifying that the VNC stack works end-to-end (check `systemctl is-active vnc-stack vnc-websockify`)

### Symptom: trying to use the wrong VNC
- `https://cyberslide.terrybot.top/vnc.html` → `ERR_CERT_AUTHORITY_INVALID` → you're hitting a different VPS or the cert has expired
- Local VNC shows black screen / "Failed to connect" → usually means `DISPLAY=:1` environment wasn't set when launching Chromium, or the XFCE session died
- noVNC shows "Connect" button but click does nothing → URL needs the `?autoconnect=true` query param, OR the websockify cert/auth blocks

### Proper VNC test sequence (when needed)
```bash
# 1. Confirm services are up
ssh <host> 'systemctl is-active vnc-stack vnc-websockify'

# 2. Confirm ports listening
ssh <host> 'ss -tlnp | grep -E ":6080|:5901"'

# 3. Connect via noVNC
#    URL: https://<host>/vnc.html?host=<host>&port=6080&password=<vnc-pass>&autoconnect=true
#    (substitute the correct host — cyberslide.terrybot.top for the
#    Instagram-cookie VNC, NOT the dev-vps)
```

## Recipe: inject a "real-looking" test webhook when polling is broken

If Meta isn't delivering webhooks but you need to validate the worker pipeline anyway, the test-webhook trick from Part 2 still works. Use a unique `comment_id` per attempt (BullMQ dedup trap):

```js
import { createHmac } from "crypto";
const commentId = "realish_test_" + Date.now();
const commenterId = "realish_user_" + Date.now();

const payload = JSON.stringify({
  object: "instagram",
  entry: [{
    id: "<IG_SCOPED_ID>",         // from /me.id, NOT /me.user_id
    time: Date.now(),
    changes: [{
      field: "comments",
      value: {
        comment_id: commentId,
        media_id: "<POST_ID>",
        text: "test",             // matches the campaign keyword
        from: { id: commenterId, username: "realish_tester" }
      }
    }]
  }]
});

// HMAC-SHA256 with FACEBOOK_APP_SECRET (not WEBHOOK_VERIFY_TOKEN)
const signature = "sha256=" + createHmac("sha256", FACEBOOK_APP_SECRET)
  .update(payload).digest("hex");

await fetch("https://openreply.terrybot.top/api/webhook", {
  method: "POST",
  headers: { "Content-Type": "application/json", "x-hub-signature-256": signature },
  body: payload
});
```

Expected worker logs after the Part 2 fix:
```
[DM Worker] Public comment reply failed: Meta API Error 100: ... Object with ID '<FAKE_COMMENT_ID>' does not exist
[DM Worker] Job comment_<IG_SCOPED_ID>_<COMMENT_ID> failed (attempt 1): The requested user cannot be found
```

Both errors are EXPECTED — they prove the worker reached the Meta API layer. If you DON'T see them, the lookup is still broken.

## Updated decision tree (combined Parts 1, 2, and 3)

```
"DMs not firing"
├── Run verify-ig-token.sh (Layer 1)
│   ├── Exit 0 (token valid) ──────────────────────────────► Layer 1.5
│   ├── Exit 1 (code 190) ────────────────────────────────► Reconnect OAuth
│   └── Exit 2 (code 101) ─────────────────────────────────► Operator: Meta dashboard
├── Layer 1.5: probe-permission-gap.sh (counts vs comments)
│   ├── counts > 0, comments empty ──────────────────────► Operator: reconnect, tick ALL boxes
│   └── counts > 0, comments visible ────────────────────► Layer 1.7
├── Layer 1.7: probe-id-mismatch.sh
│   ├── Exit 0 (DB matches scoped id) ───────────────────► Layer 2 (webhook delivery)
│   └── Exit 1 (mismatch) ────────────────────────────────► Run the UPDATE, re-probe
├── Layer 2: webhooks reaching us?
│   ├── WebhookEvent has test rows only (test_user_id_*) ─► Real webhooks not delivered
│   │   ├── Confirm real comments exist publicly ─────────► Meta IS receiving them
│   │   └── Check Meta Dashboard → Products → Webhooks    ─► Operator action required
│   ├── WebhookEvent empty entirely ─────────────────────► Signature/webhook config broken
│   └── WebhookEvent has rows + DmLog has rows ───────────► DMs firing ✅
└── Real comment from secondary IG account ──► Should fire DM within seconds
```

## Open question

When Meta is confirmed as the failure layer (operator has verified webhook subscription in the dashboard), the next step is to **trigger a fresh real comment** to see if delivery resumes. The polling safety net will also kick in within 5 minutes for the most recent comment. If both webhook delivery AND polling fail to surface the new comment, the Layer 1.5 permission gap (Part 1) is the most likely cause — even with the operator's fix, the polling endpoint may still return empty until the next OAuth reconnection completes with all permission boxes ticked.

The most robust end-to-end validation is to **trigger a new real comment** after the operator confirms Layer 2 in the dashboard. Don't try to debug further from the VPS side once Layer 2 is the suspected layer — escalate back to the operator.