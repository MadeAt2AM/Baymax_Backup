// send-test-webhook.mjs — Send a properly HMAC-signed fake Instagram comment
// webhook to verify the full receive → queue → worker → DM pipeline without
// needing a real Instagram comment.
//
// Usage:
//   node send-test-webhook.mjs [vps-host]
//
// Reads FACEBOOK_APP_SECRET from /srv/projects/openreply/.env on the VPS and
// the decrypted IG token from /tmp/plain_token.txt to populate realistic
// metadata. Generates a unique comment_id per run (Date.now()) to avoid the
// BullMQ jobId dedup trap.
//
// What to watch after sending:
//   - WebhookEvent table gets a new row with status=PROCESSED
//   - Queue briefly shows waiting=1 then drains
//   - Worker logs:
//       [DM Worker] Job comment_<IG_SCOPED_ID>_<COMMENT_ID> completed   ← OK if
//         followed by Meta API errors (fake IDs cause failures at send layer)
//       OR
//       silent (no job log)  ← BAD: lookup mismatch or worker not running

import { createHmac } from "crypto";
import { execSync } from "child_process";
import fs from "fs";

const VPS = process.argv[2] || "dev-vps";
const TOKEN_FILE = "/tmp/plain_token.txt";
const ENV_FILE = "/srv/projects/openreply/.env";

function ssh(cmd) {
  return execSync(`ssh ${VPS} '${cmd.replace(/'/g, "'\\''")}'`, { encoding: "utf8" });
}

if (!fs.existsSync(TOKEN_FILE)) {
  console.error(`[test-webhook] No decrypted token at ${TOKEN_FILE}. Run verify-ig-token.sh first.`);
  process.exit(1);
}

// 1. Read FACEBOOK_APP_SECRET from VPS env file
const env = ssh(`cat ${ENV_FILE}`);
const fbSecret = env.split("\n").find(l => l.startsWith("FACEBOOK_APP_SECRET="))?.split("=")[1]?.trim();
if (!fbSecret) {
  console.error(`[test-webhook] FACEBOOK_APP_SECRET not found in ${ENV_FILE}`);
  process.exit(1);
}

// 2. Read the IG-scoped ID (the one webhooks deliver as entry.id)
const meJson = ssh(`curl -sS -G 'https://graph.instagram.com/v21.0/me' \
  --data-urlencode 'fields=id,user_id,username' \
  --data-urlencode 'access_token=$(cat ${TOKEN_FILE})'`);
const me = JSON.parse(meJson);
const IG_SCOPED_ID = me.id;
const POST_ID = ssh(`docker exec openreply-postgres-1 psql -U openreply -d openreply -tA \
  -c "SELECT \\"postId\\" FROM \\"Automation\\" WHERE \\"isActive\\" = true LIMIT 1"`).trim();

if (!IG_SCOPED_ID) { console.error("[test-webhook] /me.id empty"); process.exit(1); }
if (!POST_ID) { console.error("[test-webhook] No active automation with postId"); process.exit(1); }

// 3. Build payload with UNIQUE comment_id to avoid BullMQ jobId dedup
const commentId = `test_comment_${Date.now()}`;
const commenterId = `test_user_${Date.now()}`;
const payload = JSON.stringify({
  object: "instagram",
  entry: [{
    id: IG_SCOPED_ID,
    time: Date.now(),
    changes: [{
      field: "comments",
      value: {
        comment_id: commentId,
        parent_id: POST_ID,
        media_id: POST_ID,
        username: "manual_test_user",
        text: "test",
        timestamp: String(Date.now()),
        attachments: [],
        from: { id: commenterId, username: "manual_test_user" }
      }
    }]
  }]
});

// 4. HMAC-SHA256 the body using FACEBOOK_APP_SECRET
const signature = "sha256=" + createHmac("sha256", fbSecret).update(payload).digest("hex");

console.log(`[test-webhook] Sending comment_id=${commentId}`);
console.log(`[test-webhook] commenter_id=${commenterId}`);
console.log(`[test-webhook] entry.id=${IG_SCOPED_ID} (IG-scoped — this is what webhooks actually send)`);
console.log(`[test-webhook] media_id=${POST_ID}`);

// 5. Fire it
const res = await fetch("https://openreply.terrybot.top/api/webhook", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "x-hub-signature-256": signature
  },
  body: payload
});
console.log(`[test-webhook] HTTP ${res.status}: ${await res.text()}`);

// 6. Print what to look for next
console.log("\n[test-webhook] What to look for in the next 10s:");
console.log("  1. WebhookEvent row with status='PROCESSED'");
console.log("  2. Worker log: '[DM Worker] Job comment_<id>_<cid> completed'");
console.log("     followed by 'Public comment reply failed: ... Object with ID <cid> does not exist'");
console.log("     AND 'Job ... failed (attempt 1): The requested user cannot be found'");
console.log("  ↑ These errors are GOOD — they prove the automation lookup succeeded.");
console.log("  ↑ No worker log = lookup mismatch (run probe-id-mismatch.sh).");