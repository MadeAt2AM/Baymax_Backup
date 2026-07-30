# SMTP Delivery Debugging on the dev VPS

When a deployed app sends email (magic links, password resets, notifications)
but the recipient never receives it, the failure is almost always downstream
of the app itself. This reference captures the live debugging path that
worked for OpenReply's SMTP magic-link setup on mail.cyberslide.net.

## The three layers of "did the email arrive"

1. **App → SMTP server** — did Auth.js / nodemailer successfully hand the
   message to the SMTP relay? This is the only layer the app controls.
2. **SMTP server → recipient inbox** — did the relay actually deliver it?
   This is the layer that fails silently most often.
3. **Recipient filtering** — did Gmail/Outlook/etc. file it as Spam,
   Promotions, Updates, or silently drop it?

## Layer 1: verify the app can talk to SMTP

Run the actual nodemailer transport inside the app's container, not on
the host. The host and the container can have different network paths:

```bash
# From the host, exec into the app container and test the real transport:
ssh dev-vps 'docker exec -e SMTP_PASSWORD=Cris0037. openreply-web-1 node -e "
const n = require(\"/app/node_modules/nodemailer\");
const t = n.createTransport({host:\"mail.cyberslide.net\", port:587, secure:false, auth:{user:\"support@madeat2am.in\", pass:process.env.SMTP_PASSWORD}});
t.verify().then(()=>t.sendMail({from:\"OpenReply <support@madeat2am.in>\", to:\"chrisspeakssg@gmail.com\", subject:\"Test\", text:\"test\"})).then(r=>console.log(\"SENT\", r.messageId, r.response)).catch(e=>console.error(\"FAIL\", e.code, e.response, e.message));
"'
```

Key gotchas:

- **nodemailer is not on the host.** It lives in the app's node_modules.
  Use the container's node_modules path, not a host `npm install`.
- **The SMTP password may have a trailing character.** In this setup,
  the working password is `Cris0037.` (with a period), not `Cris0037`.
  A missing trailing character produces a silent auth timeout, not an
  explicit error.
- **STARTTLS on port 587.** Don't use port 465 (SSL) — it fails silently
  here. Port 587 with `secure: false` (STARTTLS upgrade) is correct.
- **The sender must be a real mailbox on the relay.**
  `OpenReply <support@madeat2am.in>` works. A bare `OpenReply <openreply@...>`
  that isn't a real mailbox on mail.cyberslide.net gets silently dropped.

## Layer 2: check the SMTP relay's delivery log

The SMTP server accepted the message (response `250 Message Queued`),
but that does **not** mean it was delivered. The queue ID from the SMTP
response is your ticket:

```
250 Message Queued (1C6BA2EC-A3A6-45B3-8355-8E8BB1A49D3F.1)
```

To check whether that message was delivered, deferred, bounced, or
filtered by the relay:

```bash
# Check the mail server's delivery log for the queue ID
ssh mail.cyberslide.net 'grep 1C6BA2EC-A3A6-45B3-8355-8E8BB1A49D3F.1 /var/log/mail.log'
```

If the relay is not under your control, ask the operator for the
delivery status of that queue ID. "Accepted" ≠ "delivered."

## Layer 3: check the recipient inbox

The app's SMTP credentials are tied to one mailbox (e.g.
`madeat2am.ai@gmail.com` via the host's Gmail utility). The
**recipient** is a different mailbox (e.g. `chrisspeakssg@gmail.com`).
You cannot inspect the recipient's inbox through the app's credentials.

Search the recipient's Gmail for:

- `from:(support@madeat2am.in)`
- `subject:"Sign in to openreply.terrybot.top"`
- `to:chrisspeakssg@gmail.com`

Check Spam, Promotions, Updates, and All Mail. Gmail sometimes files
magic-link emails into Promotions even when the sender is a real
mailbox on a legitimate domain.

## The diagnostic sequence

When the user says "I didn't get the email":

1. **Confirm the app accepted the request.**
   `curl -X POST /api/auth/signin/nodemailer` should return HTTP 302
   to `/api/auth/verify-request?provider=nodemailer&type=email`.
   A 302 means Auth.js accepted the email and handed it to the provider.

2. **Confirm the SMTP relay accepted the message.**
   Check the app logs for the SMTP response. `250 Message Queued`
   means the relay took it. Anything else (timeout, 535, 550) means
   the app-to-SMTP layer failed.

3. **Get the queue ID from the SMTP response.**
   This is the only way to trace the message past the relay.

4. **Check the relay's delivery log with the queue ID.**
   This tells you if it was delivered, deferred, bounced, or filtered.

5. **Check the recipient's inbox.**
   This is the final layer and the one you can't automate.

## Common failure patterns

| Symptom | Root cause | Fix |
|---|---|---|
| SMTP auth times out after STARTTLS | Wrong password (missing trailing char) | Use the exact password from the working config |
| SMTP returns `550 5.7.1` | Sender not a real mailbox on the relay | Use `support@madeat2am.in` |
| SMTP returns `250 Message Queued` but no email | Relay accepted but didn't deliver | Check relay delivery log with queue ID |
| Email lands in Spam/Promotions | Gmail filtering | Ask recipient to check those tabs; add sender to contacts |
| Auth.js returns 302 but no SMTP log | Auth.js didn't actually call nodemailer | Check that `EMAIL_FROM` is set and the provider is configured |
| IMAP test times out | Port 993 may be blocked; use SMTP delivery log instead | Don't test via IMAP; trace via SMTP queue ID |

## The "SMTP accepted but Gmail didn't get it" case

This is the most common and most frustrating failure. The app did
everything right — Auth.js returned 302, nodemailer sent the message,
the SMTP server returned `250 Message Queued`. But the email never
arrives.

In this case:

1. The problem is **not** in the app code.
2. The problem is **not** in the SMTP authentication.
3. The problem is **not** in the SMTP server accepting the message.
4. The problem is in the relay's delivery to Gmail, or in Gmail's
   filtering.

The only way to resolve this is:

- Get the queue ID from the SMTP response.
- Ask the relay operator to check the delivery log for that queue ID.
- If the relay says "delivered," ask the recipient to check Spam/Promotions.
- If the relay says "deferred" or "bounced," the relay operator must
  investigate the bounce reason (often a transient Gmail throttling issue).

The app cannot fix a relay-to-Gmail delivery problem. The app's job is
to get the message to the relay with a valid queue ID. Everything after
that is infrastructure the app doesn't control.