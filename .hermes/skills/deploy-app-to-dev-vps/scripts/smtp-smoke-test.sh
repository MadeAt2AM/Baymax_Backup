#!/usr/bin/env bash
# scripts/smtp-smoke-test.sh
#
# Probe an SMTP configuration end-to-end from inside the running web/api
# container. Verifies the actual AUTH LOGIN/PLAIN handshake and sends a real
# test message, instead of trusting an Auth.js "email sent" redirect.
#
# Usage:
#   ssh dev-vps 'bash /srv/scripts/smtp-smoke-test.sh <container> <recipient>'
#
# Args:
#   container   the name of the web or api container (default: openreply-web-1)
#   recipient   the destination address to send the probe email to
#               (default: $SMTP_USER)
#
# Env expected inside the container (already set in /srv/secrets/<name>.env):
#   SMTP_HOST, SMTP_PORT, SMTP_SECURE, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM
#
# The script:
#   1. Stages /tmp/smtp-smoke.js inside the container via base64-over-ssh
#      (avoids heredoc quoting disasters)
#   2. Requires nodemailer via the absolute path /app/node_modules/nodemailer
#      (CWD inside /tmp breaks plain require())
#   3. Runs verify() + sendMail() with logger:true so the AUTH exchange is
#      visible in the log
#   4. Exits 0 on "250 Message Queued", non-zero on any failure

set -euo pipefail

CONTAINER="${1:-openreply-web-1}"
RECIPIENT="${2:-${SMTP_USER:-}}"

if [ -z "$RECIPIENT" ]; then
  echo "usage: $0 <container> <recipient>" >&2
  exit 2
fi

SCRIPT=$(cat <<'JS'
const nodemailer = require("/app/node_modules/nodemailer");
(async () => {
  const t = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT ?? "587"),
    secure: process.env.SMTP_SECURE === "true",
    auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASSWORD },
    connectionTimeout: 10000,
    greetingTimeout: 10000,
    socketTimeout: 20000,
    logger: true,
  });
  try {
    const ok = await t.verify();
    if (!ok) { console.error("VERIFY_FAIL"); process.exit(1); }
    const info = await t.sendMail({
      from: process.env.EMAIL_FROM,
      to: process.env.SMTP_PROBE_TO,
      subject: "SMTP probe from " + process.env.SMTP_HOST,
      text: "This is a probe. AUTH worked; if you received this, SMTP end-to-end is correct.",
    });
    console.log("SENT", info.messageId, info.response);
  } catch (e) {
    console.error("FAIL", e.code || "", e.responseCode || "", e.message);
    process.exit(1);
  }
})();
JS
)

B64=$(printf '%s' "$SCRIPT" | base64 -w0)

ssh dev-vps bash -s -- "$CONTAINER" "$RECIPIENT" "$B64" <<'REMOTE_EOF'
set -e
CONTAINER="$1"
RECIPIENT="$2"
B64="$3"

printf '%s' "$B64" | base64 -d > /tmp/smtp-smoke.js
docker cp /tmp/smtp-smoke.js "$CONTAINER":/tmp/smtp-smoke.js
docker exec \
  -e SMTP_HOST \
  -e SMTP_PORT \
  -e SMTP_SECURE \
  -e SMTP_USER \
  -e SMTP_PASSWORD \
  -e EMAIL_FROM \
  -e "SMTP_PROBE_TO=$RECIPIENT" \
  "$CONTAINER" \
  node /tmp/smtp-smoke.js
REMOTE_EOF
