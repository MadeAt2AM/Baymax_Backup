# Verifying outbound transactional email end-to-end

Reference for "I sent the password-reset / invite / notification email —
did it actually arrive, did the link work, and is the DB back to a
clean state after I exercised it?"

Pivots off the SMTP wire-trace and rate-limiter recipes elsewhere in
this skill. Adds the missing leg: confirming the *recipient side* of
the transaction, not just the *sender side*.

## When to use

Any time you want to verify that an outbound email from a deployed
service:

1. Was actually queued by the upstream SMTP server (not 550'd).
2. Actually arrived at the recipient's inbox (Gmail, Outlook, etc.).
3. Carries the expected subject / sender / body content.
4. Has a working link (the URL parses, the destination returns 2xx,
   the action it triggers produces the expected side effect).
5. Did not leave the DB in a modified state after the test.

A typical case is a password-reset flow on a tenant user. The recipe
generalises to invites, notifications, billing receipts — anywhere
the mail body carries an actionable URL.

## Recipe (worked example: tenant reset for `madeat2am.ai@gmail.com`)

### 1. Confirm the upstream SMTP server actually queued the message

```bash
ssh dev-vps 'curl -sS -X POST https://<name>.<root>/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"<recipient>\"}"'
# → {"message":"If an account with that email exists, a reset link has been sent."}

# Then grep the API container logs for the wire trace:
ssh dev-vps 'docker logs --tail 120 <api_container> 2>&1 \
  | grep -E "MAIL FROM|RCPT TO|From: |To: |Subject: |S: 250|S: 550|S: 250 Message Queued"'
```

Healthy signature:
```
C: MAIL FROM:<envelope>
S: 250 sender <envelope> OK
C: RCPT TO:<recipient>
S: 250 recipient <recipient> OK
From: <display-name-with-address>
To: <recipient>
Subject: <expected subject>
S: 250 Message Queued (<queue-id>)
```

If `From:` line is missing, see `references/smtp-provider-traps.md`.
If `S: 550` instead of `S: 250 Message Queued`, see the same
reference for the envelope-from vs auth-user mismatch.

### 2. Check the recipient's actual inbox

The right tool depends on the recipient's provider:

| Recipient provider | Tool | Command |
|---|---|---|
| Gmail (`@gmail.com`, Google Workspace) | `google-workspace` skill | `GAPI gmail search "subject:<token> newer_than:30m" --max 10` |
| Any IMAP (Outlook, Fastmail, Yahoo, custom) | `himalaya` skill | `himalaya imap search --output json "SUBJECT <token>"` |
| Catch-all dev inbox (`mailhog`, `mailpit`) | web UI | `<mailhog>:8025` (browser) |

#### Gmail (most common)

```bash
# On this host, the gws CLI lives at:
GAPI=/root/.hermes/.venv/bin/python\ /root/.hermes/skills/productivity/google-workspace/scripts/google_api.py

"$GAPI" gmail search "subject:(<expected subject keyword>) newer_than:30m" --max 10
```

Returns JSON `[{id, threadId, from, to, subject, date, snippet, labels}]`.
`snippet` should contain the brand name + the first few words of the
body — enough to confirm the email is the right one without opening
it.

To read the full body (and pull out the reset link):

```bash
"$GAPI" gmail get <message_id>
# → {"id":..., "body":"<!DOCTYPE html>...<a href=\"https://.../reset-password?token=<raw>\">...</a>..."}
```

The reset link is the `href` value inside the body's `<a>` tag. JSON-
parse it with `python3 -c "import json,sys; print(json.load(sys.stdin)['body'])"`.

**Important:** Gmail applies a "via" header rewrite when the sender's
domain doesn't match the SMTP server's DKIM signature. Open the email
in a real Gmail client first to confirm Gmail did not flag the message
as phishing / spoofing. If it did, the wire trace says "queued" but the
recipient never sees the email — the SMTP server you sent through must
have a DKIM signature aligned with the From: domain. See
`references/smtp-provider-traps.md` Mode 2 for the same class of issue
from the sender side.

#### Catch-all dev inbox (mailhog / mailpit)

```bash
# 1. Trigger the reset
curl -sS -X POST https://<name>.<root>/api/auth/forgot-password \
  -H 'Content-Type: application/json' -d '{"email":"<recipient>"}'

# 2. Check the dev mailbox
curl -sS http://<mailhog-host>:8025/api/v2/messages \
  | python3 -c "import json,sys; m=json.load(sys.stdin); \
       [print(x['From'], x['To'], x['Subject'], x['ID']) for x in m['items']]"

# 3. Read full message
curl -sS http://<mailhog-host>:8025/api/v1/message/<id> \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['Content']['Body'])"
```

### 3. Verify the link inside the email actually works

```bash
RAW_TOKEN="<value from step 2>"

# POST reset-password with the token + a known new password
curl -sS -X POST https://<name>.<root>/api/auth/reset-password \
  -H 'Content-Type: application/json' \
  -d "{\"token\":\"$RAW_TOKEN\",\"newPassword\":\"VerifyTemp123!\"}"
# → {"success":true}   ← token accepted, password rewritten

# Confirm login works with the new password
curl -sS -X POST https://<name>.<root>/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"<recipient>","password":"VerifyTemp123!"}'
# → {"token":"...","user":{...},"redirectTo":"..."}   ← login succeeds
```

Two green responses here = the link works end-to-end. A 401 with
`{"error":"Invalid token"}` means the token was generated but never
persisted (DB write succeeded but read back doesn't match) or it
expired (default expiry is 1 hour — if your email took longer to
arrive, re-trigger). A 401 with `{"error":"Invalid credentials"}`
means the new-password value was rejected — usually because the
hash format isn't bcrypt-compatible. See `references/smtp-provider-traps.md`
for the same root-cause flow from the other end.

### 4. Restore the DB to its pre-test state

The point of using a test recipient is to leave production unchanged.
Two restoration patterns:

**If the recipient password was already known (bulk-seeded user):**

```bash
# Inside the API container so the request has trust proxy = 1
TOKEN=$(curl -sS -X POST https://<name>.<root>/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"<recipient>","password":"VerifyTemp123!"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")

curl -sS -X POST https://<name>.<root>/api/auth/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"newPassword":"<original-password>"}'
# → {"success":true,"mustChangePassword":false}
```

**If you don't know the original password:**

Direct DB rewrite with bcrypt + Postgres `crypt()`:

```bash
ssh dev-vps 'docker exec <pg_container> psql -U <pg_user> -d <db> -Atc "
  UPDATE users
     SET password_hash = crypt(\x27<original-password>\x27, gen_salt(\x27bf\x27, 12)),
         must_change_password = false
   WHERE lower(email) = lower(\x27<recipient>\x27)
   RETURNING id"'
```

Verify with a real `bcrypt.compare` round-trip — see gotcha #37 in
`SKILL.md` (a `crypt(input, stored_hash) = stored_hash` SQL check
always returns `t` because postgres re-encrypts against its own salt,
so it cannot distinguish a valid from an invalid hash):

```bash
ssh dev-vps 'docker exec -e EM=<recipient> -e PW=<original-password> <api_container> \
  node -e "fetch(\"http://127.0.0.1:8080/api/auth/login\",{
    method:\"POST\",headers:{\"Content-Type\":\"application/json\"},
    body:JSON.stringify({email:process.env.EM,password:process.env.PW})
  }).then(async r=>console.log(r.status+\"|\"+(await r.text()).slice(0,80)))"'
# → 200|{"token":...   ← hash is back to the original
```

### 5. Clean up debug env vars and restart the API container

If you enabled `SYNRA_SMTP_DEBUG=1` (or any equivalent) to get the
wire trace, **scrub it from the secrets file and restart**:

```bash
ssh dev-vps 'sed -i "/^SYNRA_SMTP_DEBUG=/d" /srv/secrets/<name>.env
  docker rm -f <api_container> 2>/dev/null
  docker compose -f /srv/projects/<name>/docker-compose.yml up -d api'

# Confirm clean:
ssh dev-vps 'docker exec <api_container> printenv SYNRA_SMTP_DEBUG'
# → (empty)
```

## Pitfalls

1. **Reading the inbox via curl/gws does NOT equal seeing the email
   delivered to a real user.** Gmail sometimes classifies
   low-DKIM-aligned mail as spam — it lands in spam not inbox, and
   `gws gmail search` (which searches all mail, not just inbox) will
   still return it. Open the email in a real browser to confirm
   where Gmail put it. If the operator wants reliable delivery to
   Gmail inboxes, the From domain must DKIM-sign against the SMTP
   server's signing key, or the operator must whitelist the IP in
   Gmail Postmaster Tools.

2. **The `<a href>` URL inside the email body is HTML-encoded.**
   `&amp;` shows up in the raw string when there are query params.
   Strip the encoding before passing to curl:
   `python3 -c "import html,sys; print(html.unescape(sys.argv[1]))" \
     "<href>"`.

3. **Don't run `gmail get` against a message from a different
   operator's session.** The `google-workspace` skill is tied to a
   single Gmail account (`madeat2am.ai@gmail.com` on this host).
   If the recipient is a different Gmail account, the message won't
   show up here. Use that recipient's own session via the himalaya
   skill + their IMAP credentials instead.

4. **The `<email>` lookup uses case-insensitive matching on the
   server side (Postgres `lower()`), but the URL inside the body is
   constructed from the SERVER's stored row, not the request's
   casing.** So if you POST forgot-password with `MADEAT2AM.AI@GMAIL.COM`
   and the stored row is `madeat2am.ai@gmail.com`, the email
   arrives at `madeat2am.ai@gmail.com` (lowercased recipient) but the
   `From:` header on the wire says `MADEAT2AM.AI@GMAIL.COM`
   (preserves the request casing). Watch for this if you're
   character-matching recipient headers in the gmail search.

5. **The reset-password endpoint returns 200 with `{"success":true}`
   even if the new password is identical to the old one.** It doesn't
   tell you whether the password actually changed — verify with a
   fresh login before you declare the link works.

## Variant: notification emails (no link, just body content)

For notification emails (shift swap, leave approved, etc.) skip step 3
(link verification) and replace step 4 with "verify the notification
row was added to the DB":

```bash
ssh dev-vps 'docker exec <pg_container> psql -U <pg_user> -d <db> -Atc "
  SELECT id, type, created_at, read_at
    FROM notifications
   WHERE user_id = (SELECT id FROM users WHERE lower(email)=lower(\x27<recipient>\x27))
   ORDER BY created_at DESC LIMIT 5"'
```

Notification + email both arriving is a stronger signal than either
alone.
