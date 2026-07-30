---
name: openreply-specific-lessons
description: OpenReply-specific deployment lessons learned on the dev VPS — SMTP auth, webhook signature verification, follow-gate logic, the Instagram Graph API endpoint gotcha (graph.instagram.com vs graph.facebook.com), and the workflow rule for not delegating VPS-side debugging back to Chris when SSH access is available.
---

# OpenReply-Specific Deployment Lessons

## SMTP Authentication
- The SMTP password for `support@madeat2am.in` must include the trailing period: `Cris0037.`
- SMTP host: `mail.cyberslide.net`, port: `587`, STARTTLS
- Always verify SMTP auth with a real `sendMail` test from inside the container using nodemailer with `logger:true`

## Webhook Signature Verification
- Meta/Instagram webhooks are signed with either:
  - Facebook App Secret (`FACEBOOK_APP_SECRET`)
  - Instagram App Secret (`INSTAGRAM_APP_SECRET`)
  - NOT the webhook verify token (`WEBHOOK_VERIFY_TOKEN`)
- The verification logic must try both secrets and accept if either matches
- Signature format: `sha256=<hex_digest>` in `X-Hub-Signature-256` header

## Follow-Gate Logic (Require Follow)
- In DM worker, the follow status check must be: `sendFollowPrompt = alreadyFollows === false;`
- NOT: `sendFollowPrompt = alreadyFollows !== true;` (inverted logic)
- The follow-check endpoint properly handles three states:
  - `true` (follows) → deliver link/reward
  - `false` (doesn't follow) → show follow prompt
  - `null` (unknown) → fail-open: deliver link (don't trap real followers)

## Database / BullMQ migration
- Run `docker compose run --rm migrate` (or equivalent Prisma command) on first pull
- BullMQ jobs queue from `app/api/webhook/route.ts` uses job IDs like `comment_<igId>_<commentId>` to dedupe

## Environment Variables
- Critical secrets must be set in both:
  - `/srv/secrets/openreply.env` (source of truth)
  - `/srv/projects/openreply/.env` (copied on first deploy, manual edits survive)
- Missing SMTP_PASSWORD will cause silent auth failures
- All Meta/Facebook secrets must be present for webhook verification to work

## Verification Steps
1. Check webhook endpoint responds to Meta's challenge:
   ```bash
   curl -sS "https://openreply.terrybot.top/api/webhook?hub.mode=subscribe&hub.verify_token=WXdSaVdY8UC5wdHY-vyK49pLH-_Z3Ewx&hub.challenge=12345"
   ```
   Should return `12345`

2. Verify webhook signature validation works by sending a test payload with correct HMAC-SHA256 signature using Facebook or Instagram app secret

3. Check worker logs for DM processing:
   ```bash
   docker logs --since 5m openreply-worker-1 | grep -iE 'dmLog|SENT|processComment'
   ```

4. Validate that automations have `requireFollow` set correctly in the database:
   ```sql
   SELECT id, name, require_follow FROM automations WHERE is_active = true;
   ```

## Instagram Graph API endpoint gotcha (CRITICAL — burns debugging sessions)

**Instagram-Login app tokens only authenticate against `graph.instagram.com`, NOT `graph.facebook.com`.** A token generated through the Instagram OAuth flow will return `{"error":{"message":"Invalid OAuth access token - Cannot parse access token","code":190,"type":"OAuthException"}}` on `graph.facebook.com/v21.0/me` even when it's perfectly valid. The same token returns `{"id":"...","username":"cyber.slide"}` on `graph.instagram.com/v21.0/me`.

**Diagnostic sequence when a freshly generated token appears to be invalid (always run step 1 first):**

```bash
# Get the decrypted token. The encryption uses AES-256-GCM with IV + auth
# tag prepended to the ciphertext — see lib/meta/oauth.ts for the algorithm.
# Decrypt from the DB if no decrypted_token.txt exists:
docker exec openreply-postgres-1 psql -U openreply -d openreply -tA \
  -c "SELECT \"accessToken\" FROM \"InstagramAccount\" LIMIT 1" > /tmp/full_token.txt
docker cp /tmp/full_token.txt openreply-web-1:/tmp/full_token.txt
docker exec openreply-web-1 node -e '
import("crypto").then(({createDecipheriv}) => {
  const fs = require("fs");
  const enc = fs.readFileSync("/tmp/full_token.txt", "utf8").trim();
  const E = process.env.ENCRYPTION_KEY;
  const key = Buffer.from(E, "hex");
  const combined = Buffer.from(enc, "base64");
  const iv = combined.subarray(0, 16);
  const authTag = combined.subarray(16, 32);
  const ct = combined.subarray(32);
  const dec = createDecipheriv("aes-256-gcm", key, iv);
  dec.setAuthTag(authTag);
  fs.writeFileSync("/tmp/decrypted_token.txt",
    Buffer.concat([dec.update(ct), dec.final()]).toString("utf8"));
});'

# 1. TEST ON graph.instagram.com FIRST — this is the correct endpoint
#    for Instagram-Login tokens:
curl -sS "https://graph.instagram.com/v21.0/me?fields=id,username&access_token=$TOKEN"
# ↑ If this returns {"id":"...","username":"..."}, the token is VALID.
#   The bug is upstream — wrong endpoint in code, not the token itself.

# 2. Cross-check with graph.facebook.com to confirm the misdiagnosis pattern:
curl -sS "https://graph.facebook.com/v21.0/me?fields=id,name&access_token=$TOKEN"
# ↑ If THIS returns 190 "Cannot parse access token" while the IG endpoint
#   worked, the token format is Instagram-only (IGAA-prefixed). Confirms
#   the OpenReply code MUST use graph.instagram.com, not graph.facebook.com.
```

**Root cause pattern:** When you see OAuth code that calls
`getMetaGraphApiVersion()` to build `${apiBase}/v21.0/...`, check whether
`apiBase` resolves to `graph.instagram.com` or `graph.facebook.com`. The
correct base for Instagram-Login apps is `graph.instagram.com`. Facebook-Login
apps use `graph.facebook.com` but require different scopes.

**Symptom of misdiagnosis:** Spending 2+ hours blaming Meta app mode,
tester invites, App Review status, or token expiry when the token is
fine and the issue is endpoint mismatch. Always run BOTH endpoint tests
as step 1 of any "token appears invalid" investigation, in this order:
graph.instagram.com first (correct), then graph.facebook.com (which will
return 190 even for valid IG tokens — that's expected).

**OpenReply-specific context (as of the 2026-07-30 deployment):**
`/srv/projects/openreply/lib/meta/client.ts` correctly uses
`instagramGraphBase()` (→ `graph.instagram.com`) for all media/comments/DMs
endpoints. The token generated through the Instagram OAuth callback
(`app/api/instagram/callback/route.ts`) is an Instagram-Login token and
must only be tested on `graph.instagram.com`. The campaign post
`18107701655106615` (reel `https://www.instagram.com/reel/DbX7KaApMNo/`)
is correctly bound to the campaign and ready for testing.

## Workflow preference: execute via SSH, don't ask Chris to run commands

**When the agent has dev-vps SSH access, do NOT delegate command execution back to Chris.** Chris has explicitly said "you already have access to the dev vps, why asking me to do this, do yourself and update here."

Concrete rules:
- If you have the encrypted token in the DB and need to test it against Meta's API → decrypt inside the running container, then `curl` from the dev VPS, then report the result. Don't ask Chris to run the test.
- If you need to read a log file, query a DB row, or restart a container → do it via SSH, paste the output, continue.
- The only time to ask Chris is when the action requires something only he has: his Instagram account on his phone (to accept tester invites), his Meta Developer Dashboard login (to toggle Live mode, approve App Review), or his operator action in a UI flow he controls.
- When in doubt, try the SSH path first. If the action is genuinely impossible from the VPS (e.g. typing a verification code into a phone prompt), THEN ask Chris — and tell him exactly what command to run / button to click.
- Never suggest "let me know if you need me to do this for you" when you already have the SSH access to do it yourself.

## Comment-to-DM flow: no comments = no DMs

When the worker is healthy, the campaign is active, the token is valid, but DMs still don't fire: **check whether there are actually any comments on the bound post.** The polling safety net (`lib/polling/comment-reconciler.ts`) runs every 5 minutes via the worker, but it can only enqueue jobs for comments that actually exist in Instagram's data. Verify with:

```bash
TOKEN=$(docker exec openreply-web-1 cat /tmp/decrypted_token.txt)
curl -sS -G "https://graph.instagram.com/v21.0/<POST_ID>/comments" \
  --data-urlencode "access_token=$TOKEN" \
  --data-urlencode "fields=id,text,from.username,timestamp"
# If "data":[] → no comments to process. Tell Chris to comment from a
# secondary IG account with the campaign keyword, then re-check.
```

If no comments exist, the entire system is working correctly and the
operator action (posting a real test comment) is what's missing. Do NOT
keep "fixing" the code in this state.