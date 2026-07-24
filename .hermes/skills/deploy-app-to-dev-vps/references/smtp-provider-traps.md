# SMTP provider traps — debugging `550 Missing From header at envelope`

Reference for when transactional email from a node service (a "from"
address sent via an SMTP envelope) is rejected by the upstream SMTP
server with messages like:

```
550 Missing From header at envelope. Please fix email client settings
or contact your system administrator.
```

or

```
550 You are not allowed to send emails as <address> while logged as
<auth-user>. Please fix email client settings or contact your system
administrator.
```

## The two failure modes

These are **provider-policy rejections**, not configuration bugs in
your app. Both stem from misaligned `MAIL FROM:` (SMTP envelope) vs
`From:` (MIME header) vs the authenticated SMTP user.

### Mode 1: envelope from matches auth-user but message has no `From:` header

The upstream SMTP server accepts the SMTP transaction (TLS, AUTH,
MAIL FROM, RCPT TO all return 2xx) and then, on the `DATA` payload,
inspects the **message-level `From:` header** to verify it's
present and parseable. If it's missing, the server rejects with
`550 Missing From header at envelope`.

**Common cause:** nodemailer versions >= 9.0.x have a regression in
which `transporter.sendMail({ from, envelope, html })` strips the
message-level `From:` header in certain edge cases (single-part
HTML body, no `headers:` list provided, `envelope.from` set).
The SMTP envelope is set correctly, but the MIME body is missing
the line that the server cross-checks against it.

**Wire-trace proof:** enable `debug: true, logger: true` on the
nodemailer transport and watch the `DEBUG [...]: <header>: ...`
lines after `DATA → 354 go ahead`. If you see `To:`, `Subject:`,
`Message-ID:`, `MIME-Version:`, `Content-Type:` headers but
**no `From:` line before the body**, nodemailer silently dropped
the From header — that's the bug.

**Fix (in order of preference):**

1. **Pin nodemailer to `^6.9.x`** — that's the last known-good
   major. nodemailer 6 ships the From header reliably with the
   `sendMail({ from, envelope, html })` shape. Bump other deps
   in lockstep as needed.
2. **If you must stay on nodemailer 9**, build the MIME yourself
   via `new MailComposer({...}).compile().build(...)` then pass
   `transporter.sendMail({ raw: <buffer> })`. Note that
   `MailComposer` is no longer re-exported from the top-level
   nodemailer module in 9; pull it from
   `nodemailer/lib/mail-composer/index.js` (note the explicit
   `/index.js` — ESM rejects directory imports otherwise).
3. **Always pass an explicit `from:`** with both display name and
   address (`"Display Name <addr@host>"`) and let nodemailer derive
   `envelope.from` from it. Don't omit `from:`.

### Mode 2: envelope from differs from authenticated user

Some hosting providers (mailcow on Haraka, some Hetzner-hosted
mail servers, ...) reject any `MAIL FROM:` that doesn't match the
authenticated SMTP user. Error response:

```
550 You are not allowed to send emails as <envelope-from> while
logged as <auth-user>. Please fix email client settings or contact
your system administrator.
```

When your "from" address is something friendly like
`SYNTRA Platform <platform@madeat2am.in>` but the auth user is
`support@madeat2am.in`, nodemailer sends envelope
`platform@madeat2am.in` (the bare address parsed from the
display-name + angle bracket) and the server rejects.

**Fix:** pre-derive a bare envelope address from the from-string and
dedupe it against `smtp.user`. If the derived envelope value
differs from the auth user, omit `envelope` from `sendMail` (so
nodemailer derives envelope from the auth user and the server
is happy); if the values match, set `envelope.from` explicitly
for safety.

```typescript
function extractBareAddress(from: string): string | null {
  const angle = from.match(/<([^<>]+@[^<>]+)>/);
  if (angle) return angle[1]!.trim();
  const plain = from.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  return plain ? plain[0] : null;
}

// In sendEmail:
const envelopeFromCandidate = extractBareAddress(smtp.from);
// Skip envelope if it'd differ from smtp.user to avoid provider rejection
await transporter.sendMail({
  from: smtp.from,
  envelope: envelopeFromCandidate === extractBareAddress(smtp.user)
    ? { from: envelopeFromCandidate, to }
    : undefined,
  to, subject, html,
});
```

## Diagnostic procedure

When a deployed service reports `Failed to send ... 550`, drill in
with:

1. **Capture the SMTP wire trace.** Enable nodemailer transport
   debug logging:

   ```diff
   function buildTransport(smtp) {
     return nodemailer.createTransport({
       host: smtp.host, port: smtp.port, secure: smtp.secure,
       requireTLS: isStartTLS,
       auth: { user: smtp.user, pass: smtp.pass },
   +   logger: process.env["SYNRA_SMTP_DEBUG"] === "1",
   +   debug:  process.env["SYNRA_SMTP_DEBUG"] === "1",
     });
   }
   ```

   `SYNRA_SMTP_DEBUG=1` (or any opt-in env name you prefer) flips
   the trace on without redeploying code that defaults to off.
   The trace emits exactly one `DEBUG [..]: <header>: <value>`
   line per MIME header in the order nodemailer serialized them —
   look for the missing `From:` between `MAIL FROM` and the body.

2. **Probe the SMTP server directly** with Python or `nc` so the
   envelope is in your control:

   ```python
   import smtplib, ssl
   from email.message import EmailMessage
   msg = EmailMessage()
   msg["Subject"] = "test"; msg["From"] = "support@madeat2am.in"
   msg["To"] = "support@madeat2am.in"; msg.set_content("body")
   with smtplib.SMTP("mail.cyberslide.net", 587, timeout=10) as s:
       s.starttls(context=ssl.create_default_context())
       s.login("support@madeat2am.in", "***")
       s.send_message(msg)
   ```

   If that succeeds and nodemailer fails, the bug is in the
   MIME-serialization layer (Mode 1). If that ALSO fails with
   the same error, the bug is the envelope-from matching the
   auth user (Mode 2).

3. **Compare envelope vs header vs auth user.** Print all three
   in the failing code path:

   ```typescript
   console.log({
     authUser:    smtp.user,
     mailFrom:    envelopeFromCandidate,
     headerFrom:  smtp.from,
   });
   ```

   The triplet should satisfy:
   `mailFrom === extractedBareAddress(authUser)` for strict
   providers, and `headerFrom` should contain a parseable email
   address for hosts that validate the MIME header.

## Multiple SMTP configurations live

If the system ships per-tenant SMTP (each company has its own
`smtp_config` JSON) AND a platform-level SMTP (for platform-admins
contacting the operator), make sure the platform-config getter
and the tenant-config getter are wired separately. A common shape:

```typescript
function resolveMailer({ userRole, companySmtp, platformSmtp }) {
  // Platform admins use the platform SMTP. Tenants use theirs.
  const usePlatform = userRole === "platform_admin" || !companySmtp;
  return { smtp: usePlatform ? platformSmtp : companySmtp, kind: usePlatform ? "platform" : "tenant" };
}
```

Drop `password` out of platform settings before echoing them back
to the SPA — see the multi-tenant `sanitizeCompanyForRole` pattern
in the api-server code for how to redact `pass` while keeping
`host/port/secure/user/from` visible.

## When a 200-response hides a delivery failure

`{"message":"If an account with that email exists, a reset link has been sent."}` from the forgot-password endpoint only proves the route ran — it does NOT prove the email arrived. Three failure modes that pass the 200-response check but fail at the recipient:

1. **Wire-level 550** — covered by Modes 1 and 2 above. The API logs `Failed to send ... password reset email`. Easy to catch via `docker logs`.
2. **DKIM-aligned sender required by Gmail** — the SMTP server returns `250 Message Queued`, the API logs `Sent message`, Gmail accepts the message into its pipeline, but Gmail puts it in the recipient's **spam folder** (or refuses it outright) because the From-domain doesn't DKIM-sign against the SMTP server's signing key. The recipient never sees the email unless they check spam. The `gws gmail search` will still return the message because Gmail search spans all folders — to confirm it landed in **Inbox**, open the message in a real browser. Fix: align the From domain's DKIM with the SMTP server's signing key, or add the SMTP server IP to Gmail Postmaster Tools allowed-IPs.
3. **Subdomain-stripped DKIM** — `From: SYNTRA Platform <noreply@syntra.cyberslide.net>` and DKIM signed against `madeat2am.in` (a parent domain). Some providers (Hetzner mail relay, certain SendGrid configs) reject the alignment. Symptom: same as #2 — message in spam or rejected with `550 DKIM check failed`. Fix: sign against the actual From domain or use a relaxed-aligned `d=` value matching the parent.

The full delivery-verification recipe (inbox check via gws/himalaya/mailhog + link round-trip + DB restore + debug-env scrub) is in `references/email-delivery-verification.md`.

## Related skill references

- `references/email-delivery-verification.md` — the recipient-side
  leg of the email-flow loop: read the inbox, parse the link, POST
  it to verify the round-trip, restore the DB to pre-test state,
  scrub debug env vars. Pair with this file (sender-side).
- `references/security-hardening-patterns.md` — runtime
  `Dockerfile` multi-stage dependency pitfalls (gotcha #10 in
  `deploy-app-to-dev-vps/SKILL.md`).
- `references/case-insensitive-email.md` — defensive helper
  patterns when matching on email.
- `references/seeding-patterns.md` — bcrypt + Postgres `crypt()`
  + SMTP test endpoint plumbing.
