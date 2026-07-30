#!/usr/bin/env bash
# verify-ig-token.sh — Decrypt the stored Instagram access token from OpenReply's
# PostgreSQL and call Meta's /me endpoint to verify the token is valid.
#
# Usage:
#   ./verify-ig-token.sh
#
# Reads ENCRYPTION_KEY from the web container's env. Decrypts the accessToken
# from the InstagramAccount table and tests it against Meta's Graph API.
#
# Exit codes:
#   0 — token valid (Meta accepted)
#   1 — token invalid / rejected by Meta
#   2 — usage / connectivity error
#
# This is the FIRST diagnostic step for any "DM not firing" symptom in OpenReply.
# Run this BEFORE patching worker logic.
#
# CRITICAL (2026-07-30): Uses graph.instagram.com, NOT graph.facebook.com.
# Instagram Graph API tokens are scoped to the Instagram endpoint; the same
# token returns code 190 against graph.facebook.com even when fully valid for
# Instagram operations.

set -euo pipefail

VPS="${VPS:-dev-vps}"
CONTAINER="${CONTAINER:-openreply-web-1}"

echo "==> Pulling encrypted token from DB..."
ssh "$VPS" "docker exec openreply-postgres-1 psql -U openreply -d openreply -tA -c \"SELECT \\\"accessToken\\\" FROM \\\"InstagramAccount\\\" LIMIT 1\"" > /tmp/enc_token.txt

TOKEN_LEN=$(wc -c < /tmp/enc_token.txt)
echo "    Encrypted token: $TOKEN_LEN bytes"

echo "==> Writing decrypt script to VPS..."
cat > /tmp/decrypt_ig_token.mjs << 'EOF'
import { createDecipheriv } from "crypto";
import fs from "fs";
const enc = fs.readFileSync(process.argv[2], "utf8").trim();
const E = process.env.ENCRYPTION_KEY;
if (!E) { console.error("ENCRYPTION_KEY missing"); process.exit(2); }
const key = Buffer.from(E, "hex");
const combined = Buffer.from(enc, "base64");
const iv = combined.subarray(0, 16);
const tag = combined.subarray(16, 32);
const ct = combined.subarray(32);
try {
  const dec = createDecipheriv("aes-256-gcm", key, iv);
  dec.setAuthTag(tag);
  fs.writeFileSync(process.argv[3], Buffer.concat([dec.update(ct), dec.final()]).toString("utf8"));
} catch (e) {
  console.error("Decryption failed: " + e.message);
  process.exit(2);
}
EOF

B64=$(base64 -w 0 /tmp/decrypt_ig_token.mjs)
ssh "$VPS" "echo '$B64' | base64 -d > /tmp/dec.mjs && \
  docker cp /tmp/enc_token.txt $CONTAINER:/tmp/enc_token.txt && \
  docker cp /tmp/dec.mjs $CONTAINER:/tmp/dec.mjs && \
  docker exec $CONTAINER node /tmp/dec.mjs /tmp/enc_token.txt /tmp/plain_token.txt && \
  docker cp $CONTAINER:/tmp/plain_token.txt /tmp/plain_token.txt"

PLAIN_LEN=$(wc -c < /tmp/plain_token.txt)
echo "    Decrypted token: $PLAIN_LEN bytes"

echo "==> Testing token against Meta Graph API (graph.instagram.com)..."
TOKEN=$(cat /tmp/plain_token.txt)
RESPONSE=$(ssh "$VPS" "curl -sS 'https://graph.instagram.com/v21.0/me?access_token=$TOKEN'" 2>&1)
echo "    Response: $RESPONSE"

if echo "$RESPONSE" | grep -q '"id"'; then
  echo ""
  echo "✓ Token is VALID. Meta authentication works."
  echo "  → If DMs are still not firing, check for permission gap (Step 1.5 in SKILL.md)."
  exit 0
elif echo "$RESPONSE" | grep -q '"code":190'; then
  echo ""
  echo "✗ Token is INVALID (Meta code 190: $(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | head -1))."
  echo "  → Reconnect Instagram account via OAuth in OpenReply dashboard to regenerate."
  exit 1
else
  echo ""
  echo "? Unexpected response — see above."
  exit 2
fi