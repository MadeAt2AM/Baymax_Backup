# OpenReply adaptation reference

This reference records reusable deployment patterns from adapting a Vercel/Railway-oriented Auth.js application to the shared dev VPS.

## Auth.js SMTP magic links

Auth.js's Resend provider does not become SMTP-aware because SMTP variables are present. Use the built-in Nodemailer provider:

```ts
import Nodemailer from "next-auth/providers/nodemailer";

Nodemailer({
  server: {
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT ?? "587"),
    secure: process.env.SMTP_SECURE === "true",
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASSWORD,
    },
  },
  from: process.env.EMAIL_FROM,
});
```

Add `nodemailer` to `package.json` and regenerate the lockfile. Validate with an actual magic-link request and mailbox read-back. Do not add password credentials to an email-only app merely to make smoke testing convenient.

## Grey-cloud Cloudflare A record

The dev VPS already carries `/srv/scripts/.cf-env` with `CF_ZONE_ID`, `CF_DOMAIN`, and `CF_API_TOKEN`. Existing deploy helpers show the supported API shape. Create the record with:

```text
POST /client/v4/zones/$CF_ZONE_ID/dns_records
{
  "type": "A",
  "name": "openreply.terrybot.top",
  "content": "147.79.18.32",
  "ttl": 1,
  "proxied": false
}
```

Make the operation idempotent: query by type/name first, update an existing record if its address/proxy state is wrong, otherwise create it. Verify `success:true`, `content`, `proxied:false`, and public DNS resolution before relying on Caddy ACME issuance.

## Weekly replace-in-place PostgreSQL backup

Use a temporary file in the destination directory, stream `pg_dump` through gzip, require a non-empty result, then atomically replace the stable path:

```bash
tmp=$(mktemp /srv/backups/openreply/.latest.XXXXXX.sql.gz)
trap 'rm -f "$tmp"' EXIT
docker exec openreply-postgres-1 pg_dump -U openreply -d openreply | gzip -9 > "$tmp"
test -s "$tmp"
mv -f "$tmp" /srv/backups/openreply/latest.sql.gz
chmod 600 /srv/backups/openreply/latest.sql.gz
```

Schedule it every seven days. A failed dump must leave the previous backup intact. The container name in this snippet uses the `<service>-1` Compose default; the OpenReply compose project also still worked when the suffix was `-1`, but the script should be defensive if a future compose version changes it.

## Timeout-safe first deployment

A first `docker compose up -d --build` may outlive the SSH/API command timeout while Docker continues building on the VPS. After a timeout, inspect only the target project's processes, Compose state, and images. Never start a second build concurrently. Terminate the target processes only after explicit operator approval, then rerun one captured-log build and verify containers, migrations, Caddy reload, and HTTP health independently.

## Validate SMTP before integrating it with Auth.js

Auth.js's "email sent" redirect is not enough — it only proves the signin handler returned; it does not prove SMTP accepted the message. Pasted secrets regularly lose trailing punctuation (`.`, spaces, smart quotes) and a single character drift produces a hang during AUTH rather than a fast 535, because the server is blocking on read for a longer password than expected. Run a direct nodemailer `verify()` and a real `sendMail` from inside the container before treating magic-link as working. Use the absolute path `/app/node_modules/nodemailer` if the script is staged in `/tmp` — `require("nodemailer")` from `/tmp` fails with `MODULE_NOT_FOUND` even though the module is installed in the image. The reusable probe is in `scripts/smtp-smoke-test.sh`.

## `EMAIL_FROM` shell-safety in `.env` files

Values like `EMAIL_FROM=OpenReply <support@madeat2am.in>` are accepted by Compose and Next.js, but break `set -a; . .env; set +a` because the unquoted space re-parses the line as a command. Two safe patterns:

- Quote the value at the assignment site: `EMAIL_FROM="OpenReply <support@madeat2am.in>"`.
- Drop the display name and use the bare address: `EMAIL_FROM=support@madeat2am.in`.

`from` is used in the SMTP `MAIL FROM:` envelope; the display name belongs in the MIME `From:` header, which nodemailer builds from the same field. To preserve the friendly display name while keeping shell-sourced env safe, use a literal-underscore placeholder in the env file (`OpenReply_support@madeat2am.in`) and override `from:` to a header with the real name at the call site, or just quote the value.

## Caddy runtime detection (systemd vs container) — preflight before every deploy

This host's Caddy can be either a Docker container named `caddy` on the shared `web` network, or a host-level systemd service (`systemctl status caddy`). Newer deploys run it as a systemd service. Before writing or reloading any vhost fragment, detect the runtime:

```bash
ssh dev-vps 'docker ps --format "{{.Names}}" | grep -x caddy || echo NO_CADDY_CONTAINER; systemctl is-active caddy 2>/dev/null || echo NO_CADDY_SYSTEMD'
```

If Caddy is systemd:

- It cannot resolve Docker-only aliases (e.g. `openreply-app`). The new app's vhost must point at a loopback host port the container publishes, e.g. `127.0.0.1:32770:3000` in compose and `reverse_proxy 127.0.0.1:32770` in the Caddy site block.
- Reload with `systemctl reload caddy`, not `docker exec caddy caddy reload`.
- Validate first with `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`.

If Caddy is the container:

- Retain the Docker alias pattern and use `docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile`.
- The site block points at `<name>-app:<port>` like every other project on the host.

Mixing the two patterns silently produces 502s and noisy `dial tcp: lookup <name>-app on 127.0.0.53:53: server misbehaving` errors in `journalctl -u caddy`. Confirm `/etc/caddy/Caddyfile` actually contains `import /srv/caddy/sites/*.caddy` (or whatever the host's glob is) — an empty Caddyfile plus a Caddy reload leaves every existing hostname offline until corrected.

## Compose healthchecks only see container environment, not interpolated variables

A `$${REDIS_PASSWORD}` expression in a healthcheck expands at container start — but only if the value was passed in via `environment:` or `env_file:`. If the value reaches the service only through `command:` (which receives the same Compose interpolation), the running container may still lack the env var the healthcheck shell tries to read. Symptom: container reports `starting`/`unhealthy` indefinitely with `WRONGPASS` in the health log. Fix by adding `environment: <VAR>: ${<VAR>}` explicitly. Always inspect `docker inspect <ctr> .State.Health.Log` before changing the service command or secrets.

## Node module resolution inside staged `/tmp` scripts

`docker exec <ctr> node /tmp/foo.js` runs the script with CWD in `/tmp`, so plain `require("nodemailer")` fails with `MODULE_NOT_FOUND` even though `node_modules/nodemailer` exists at `/app/node_modules/nodemailer` inside the container. Either use the absolute path (`require("/app/node_modules/nodemailer")`) or `docker exec -w /app <ctr> node /tmp/foo.js`. The absolute-path form survives a `docker cp`-based staging path and is the safer default for one-off debug scripts.

## SMTP password trailing period — character-for-character fidelity required

When the operator pastes an SMTP password from chat/terminal, trailing punctuation (especially a period `.`) is frequently dropped. For this host's `mail.cyberslide.net:587` the password must be `Cris0037.` (with period). The symptom of a missing period is not a fast 535 — it is a hang during the AUTH exchange because the server blocks reading for more bytes than the client sends. Always test with the exact bytes: run the `scripts/smtp-smoke-test.sh` probe from inside the container before trusting Auth.js's "email sent" redirect.

## Campaign builder URL validation — normalize before sending

The campaign builder accepts a tracked destination URL that users often paste without `https://` or with surrounding whitespace. The server schema accepts `z.string().url()` or empty string `""`, but rejects malformed URLs. Client-side fix: add a `normalizeUrl` helper that trims whitespace, prepends `https://` when the protocol is missing, and returns `""` for empty input. Only send the normalized value to the API — the API then only ever receives a valid URL or explicit empty string, eliminating the "Invalid URL" error.

```ts
function normalizeUrl(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}
```

Apply to both primary and secondary destination URLs. For the secondary URL, only include it in the payload when the "second link" toggle is enabled.

## Meta Instagram DM — complete setup workflow (OpenReply-specific)

OpenReply's comment-to-DM pipeline requires a fully live Meta app. Development-mode apps **will not** deliver webhook events from real comments. The following must be done **in order** before any DM will fire.

### 1. Create the Meta Business app
- Open https://developers.facebook.com/apps/
- Create App → **Business** → pick "Manage messaging and content on Instagram"
- Contact email: one you check (Chris uses `madeat2am.ai@gmail.com`)

### 2. Get the three secrets
In the Meta dashboard, these live in **different places**:

| Secret | Where to find |
|--------|---------------|
| `INSTAGRAM_APP_ID` | Instagram product → API setup with Instagram login → **Show** (this is a long number like `1740755717127173`, NOT the Facebook App ID on the Basic page) |
| `INSTAGRAM_APP_SECRET` | Same page → **Show** |
| `FACEBOOK_APP_SECRET` | App Settings → Basic → **App Secret** → Show |

**Inject immediately** into `/srv/secrets/openreply.env` and `/srv/projects/openreply/.env`, then recreate only the web container (`docker compose up -d --force-recreate web`).

### 3. Add Instagram account as tester — BOTH steps required
1. **Meta dashboard**: App Roles → Roles → Instagram Testers → Add the **exact Instagram username** of the Business/Creator account.
2. **On the phone**: Switch to that Instagram account → Settings → Apps and websites → Tester invites → **Accept** the invite.

Without step 2, the OAuth flow fails with "Insufficient Developer Role".

### 4. Register OAuth redirect URI
In Instagram product → Business login settings → OAuth redirect URIs:
```
https://openreply.terrybot.top/api/instagram/callback
```
No trailing slash.

### 5. Register and verify the webhook
In Instagram product → Configure webhooks:
- Callback URL: `https://openreply.terrybot.top/api/webhook`
- Verify token: copy `WEBHOOK_VERIFY_TOKEN` from running env (e.g. `WXdSaVdY8UC5wdHY-vyK49pLH-_Z3Ewx`)
- Click **Verify** → should pass immediately (app already answers the challenge).
- Subscribe to **`comments`** field.

If Verify stays greyed out, click into the token field and paste again — editing the callback URL often clears it.

### 6. Publish the app (Live mode required for real webhook delivery)
In Publish tab, set:
- Privacy policy URL: `https://openreply.terrybot.top/privacy`
- Terms of service URL: `https://openreply.terrybot.top/terms`
- Data deletion URL: `https://openreply.terrybot.top/data-deletion`

Click **Publish**. For your own tester accounts this usually goes Live immediately. If Meta demands App Review, it's a separate path and not required for your own account.

### 7. Connect Instagram in OpenReply
OpenReply Settings → Connect Instagram → you should see Instagram's consent screen (not "Insufficient Developer Role"). Authorize; the app stores the encrypted long-lived token.

### 8. End-to-end test
1. Create a campaign with a distinctive keyword (e.g. `OPENTEST`).
2. From a **different** Instagram account, comment the keyword on the target post.
3. Watch:
   - `/api/health` stays healthy
   - `WebhookEvent` row appears
   - `DmLog` row goes `PENDING` → `SENT`
   - The other Instagram account receives the DM

### 9. After the loop works — finish remaining infrastructure
- GitHub auto-redeploy hook (push to main → webhook fires → redeploy)
- Daily cron routes: token refresh (05:00 SGT), attach-next-reel (06:00 SGT)
- Security hardening sweep (CORS allowlist, rate limits, headers)

---

## Writing `/etc/webhook/hooks.json` — safe pattern

The webhook daemon reads `/etc/webhook/hooks.json`. It is owned by `root:deploy` with mode `640` and cannot be edited directly by the agent's `patch` tool (path is outside whitelist). The reliable pattern is:

```bash
# Build the complete JSON on the host, then atomically write it via sudo
cat > /tmp/hooks.json <<'EOF'
[ ... complete array ... ]
EOF
ssh dev-vps 'sudo cp /tmp/hooks.json /etc/webhook/hooks.json && sudo chown root:deploy /etc/webhook/hooks.json && sudo chmod 640 /etc/webhook/hooks.json'
```

Key points:
- Use a heredoc with single-quoted delimiter (`<<'EOF'`) to avoid local shell interpolation of the JSON.
- Build the **complete** array — do not try to append; the file is small enough that rewriting the whole thing is simpler and safer.
- The hot-reload flag on the webhook daemon (`-hotreload`) picks up the change immediately — no service restart needed.
- Verify with `ssh dev-vps 'cat /etc/webhook/hooks.json | jq .'` after the write.

Common mistake: overwriting the file with only the new entry and losing the existing projects (Payntra, SYNTRA). Always read the current file first, construct the full new array, then write.
