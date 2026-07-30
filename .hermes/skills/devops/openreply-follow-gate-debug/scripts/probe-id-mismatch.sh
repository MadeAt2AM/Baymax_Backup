#!/bin/bash
# probe-id-mismatch.sh — Detect the Instagram ID type mismatch bug
#
# Meta's /me endpoint returns two IDs for the same Instagram Business account:
#   id       = Instagram-scoped ID (webhooks deliver this in entry.id)
#   user_id  = Business account ID (OAuth callback stores this by default)
#
# If the DB-stored instagramId is user_id and webhooks deliver id, the worker's
# automation lookup silently returns []. No errors. No DMs.
#
# Usage: bash probe-id-mismatch.sh
# Exits:
#   0 = IDs match (or no DB row, no token)
#   1 = Mismatch detected (action required)

set -euo pipefail

VPS="${VPS:-dev-vps}"

# 1. Get the decrypted token
TOKEN_FILE="/tmp/plain_token.txt"
if [[ ! -s "$TOKEN_FILE" ]]; then
  echo "[probe-id-mismatch] No decrypted token at $TOKEN_FILE. Run verify-ig-token.sh first." >&2
  exit 0
fi
TOKEN=$(cat "$TOKEN_FILE")

# 2. Fetch both IDs from /me
echo "[probe-id-mismatch] Querying /me for id + user_id..."
ME_JSON=$(ssh "$VPS" "curl -sS -G 'https://graph.instagram.com/v21.0/me' \
  --data-urlencode 'fields=id,user_id,username' \
  --data-urlencode 'access_token=$TOKEN'")
SCOPED_ID=$(echo "$ME_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id",""))')
USER_ID=$(echo "$ME_JSON"   | python3 -c 'import json,sys; print(json.load(sys.stdin).get("user_id",""))')
USERNAME=$(echo "$ME_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("username",""))')

if [[ -z "$SCOPED_ID" || -z "$USER_ID" ]]; then
  echo "[probe-id-mismatch] /me did not return both ids: $ME_JSON" >&2
  exit 0
fi

echo "[probe-id-mismatch] /me.id       = $SCOPED_ID"
echo "[probe-id-mismatch] /me.user_id  = $USER_ID"
echo "[probe-id-mismatch] /me.username = $USERNAME"

# 3. Get the stored instagramId
DB_ID=$(ssh "$VPS" "docker exec openreply-postgres-1 psql -U openreply -d openreply -tA \
  -c \"SELECT \\\"instagramId\\\" FROM \\\"InstagramAccount\\\" LIMIT 1\"")
DB_ID=$(echo "$DB_ID" | tr -d '[:space:]')

echo "[probe-id-mismatch] DB.instagramId = $DB_ID"

# 4. Compare
if [[ "$DB_ID" == "$SCOPED_ID" ]]; then
  echo "[probe-id-mismatch] OK — DB matches the Instagram-scoped ID (entry.id). Webhook lookups should work."
  exit 0
elif [[ "$DB_ID" == "$USER_ID" ]]; then
  echo "[probe-id-mismatch] MISMATCH — DB stores user_id, but webhooks deliver id."
  echo "[probe-id-mismatch]   Worker will silently fail to find automations on every comment."
  echo "[probe-id-mismatch]   Fix: UPDATE \"InstagramAccount\" SET \"instagramId\" = '$SCOPED_ID' WHERE \"instagramId\" = '$DB_ID';"
  exit 1
else
  echo "[probe-id-mismatch] UNKNOWN — DB id '$DB_ID' matches neither scoped nor user_id. Investigate."
  exit 2
fi