# Custom-Domain / White-Label Routing on the dev VPS

When a tenant wants their app served on their own hostname
(`login.acme.com` instead of `<name>.terrybot.top`), three independent
layers of the stack must agree on the list of trusted hostnames. A bug
report of the form "users are still being served from the platform URL /
my custom domain doesn't work" almost always has **all three** layers
broken at once. Patch them together.

This is the SYNTRA `syntra.cyberslide.net` fix from 2026-07-15, generalised.

---

## The three layers

```
┌────────────────────────────────────────────────────────────────────┐
│ DNS                                                                │
│  login.acme.com  ──CNAME──▶  <name>.terrybot.top  ──A──▶  VPS IP   │
│  (correctly points at the same VPS)                                │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ Caddy reverse proxy (/srv/caddy/sites/<name>.caddy)                │
│   site block for <name>.terrybot.top  ✓ (existing)                 │
│   site block for login.acme.com         ✗  ← MUST EXIST            │
│     → auto-issues ACME cert                                        │
│     → reverse_proxies <name>-web:80                                  │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ Express API                                                        │
│   /api/public/branding  → already keyed on Host ✓                  │
│   /api/auth/login       → MUST return redirectTo  ✗                │
│     when user.company.customDomain is verified AND                 │
│     req.hostname ≠ customDomain                                    │
│   CORS allowlist        → MUST include https://custom-domain  ✗    │
│     otherwise browser preflight fails                              │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ Web SPA                                                            │
│   useBranding() hook  → keyed on window.location.hostname ✓        │
│   onSuccess of login/register/accept-invite                        │
│     → MUST honour response.redirectTo                              │
│     → if present: window.location.assign(redirectTo)               │
│       (not wouter setLocation — it can't cross origins)            │
└────────────────────────────────────────────────────────────────────┘
```

---

## Source-of-truth helper

One helper drives all three layers. Don't fork the list across files —
they will drift and one layer will silently break.

```ts
// artifacts/<api>/src/lib/domain.ts
import * as fs from "node:fs";

const HOSTNAME_RE = /^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$/i;

export function normalizeDomain(input: string): string {
  return input.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
}

export function isValidHostname(domain: string): boolean {
  return HOSTNAME_RE.test(domain);
}

/** Verified custom-domain hostnames this deployment serves.
 *  Sources (in order):
 *    1. <NAME>_CUSTOM_DOMAIN_HOSTS env var (comma-separated, tests/Dockerfiles)
 *    2. /srv/secrets/<name>-custom-domains file (one hostname per line, VPS)
 */
export function getCustomDomainHosts(): string[] {
  const seen = new Set<string>();
  const fromEnv = process.env["SYNRA_CUSTOM_DOMAIN_HOSTS"]; // project-prefix as appropriate
  if (fromEnv) {
    for (const h of fromEnv.split(",").map(s => s.trim()).filter(Boolean)) {
      if (isValidHostname(h)) seen.add(h.toLowerCase());
    }
  }
  try {
    const buf = fs.readFileSync("/srv/secrets/syntra-custom-domains", "utf8");
    for (const line of buf.split(/\r?\n/)) {
      const h = line.trim();
      if (h && !h.startsWith("#") && isValidHostname(h)) seen.add(h.toLowerCase());
    }
  } catch { /* file absent during local dev */ }
  return Array.from(seen);
}

/** True iff `host` is a verified custom-domain hostname this deployment serves. */
export function isKnownCustomDomain(host: string): boolean {
  const norm = normalizeDomain(host);
  if (!norm) return false;
  return getCustomDomainHosts().includes(norm);
}

/** Build an absolute URL on the verified custom domain, ONLY when the host
 *  is in the allowlist. Returns null for unknown hosts so callers can
 *  short-circuit the redirect (open-redirect guard — a bogus DB value can
 *  never lead to an arbitrary redirect). */
export function buildCustomDomainUrl(host: string, path = "/"): string | null {
  if (!isKnownCustomDomain(host)) return null;
  const safePath = path.startsWith("/") ? path : `/${path}`;
  return `https://${normalizeDomain(host)}${safePath}`;
}
```

**Open-redirect defence (critical):** `buildCustomDomainUrl` must return
`null` for hosts not in the allowlist. The DB has user-editable
`companies.customDomain`, so the value could be attacker-controlled.
Validate against the operator-managed allowlist before constructing the
URL. Never construct the redirect from the DB value alone.

---

## API auth flow

In `routes/auth.ts`, every auth response that returns a token also returns
a `redirectTo` field (null in the common case):

```ts
function resolvePostAuthRedirect(
  reqHost: string,
  company: { customDomain: string | null; domainStatus: string | null } | undefined | null,
  destPath: string,
): string | null {
  if (!company?.customDomain || company.domainStatus !== "verified") return null;
  const target = normalizeDomain(company.customDomain);
  if (!target || normalizeDomain(reqHost) === target) return null;
  return buildCustomDomainUrl(target, destPath);
}

// POST /api/auth/login
router.post("/login", ..., async (req, res) => {
  // ... existing auth ...
  let redirectTo: string | null = null;
  if (user.companyId) {
    const [company] = await db
      .select({ customDomain: companies.customDomain, domainStatus: companies.domainStatus })
      .from(companies)
      .where(eq(companies.id, user.companyId))
      .limit(1);
    redirectTo = resolvePostAuthRedirect(req.hostname || "", company, "/dashboard");
  }
  res.json({ token, redirectTo, user: { ... } });
});

// Same pattern for POST /register (both invitation-flow and new-company-flow).
```

**Don't use wouter's `setLocation` for the redirect.** It only updates
the in-memory router — localStorage (and any future cookies) live on the
origin the form was submitted from. A cross-origin bounce requires a full
`window.location.assign(redirectTo)`:

```tsx
// web-app/src/pages/login.tsx
loginMutation.mutate({ data: values }, {
  onSuccess: (response) => {
    const mustChange = response.user?.mustChangePassword ?? false;
    const redirectTo: string | null = response.redirectTo ?? null;
    if (redirectTo) {
      login(response.token, mustChange);          // store token first
      window.location.assign(redirectTo);          // then hard-nav cross-origin
      return;
    }
    login(response.token, mustChange);
    if (mustChange) setLocation("/change-password");
    else setLocation(role === "platform_admin" ? "/platform" : "/dashboard");
  },
  onError: () => toast({ title: "Login failed", variant: "destructive" }),
});
```

Same pattern in `register.tsx` and `accept-invite.tsx`.

---

## CORS allowlist

Hardcoded CORS = single biggest footgun. Replace the static array with
the helper so every custom domain added to the sidecar is automatically
allowed:

```ts
// middlewares/cors.ts
import { getCustomDomainHosts, getPlatformTargets } from "../lib/domain";

export function buildCors() {
  const allowed = new Set<string>();
  for (const o of (process.env["ALLOWED_ORIGINS"] ?? "")
    .split(",").map(s => s.trim()).filter(Boolean)) allowed.add(o);
  for (const host of getPlatformTargets()) allowed.add(`https://${host}`);
  for (const host of getCustomDomainHosts()) allowed.add(`https://${host}`);
  if (allowed.size === 0) allowed.add("https://<name>.<domain>"); // safety net

  return cors({
    origin: (origin, cb) => {
      if (!origin) return cb(null, true);  // same-origin / curl
      if (allowed.has(origin)) return cb(null, true);
      return cb(null, false);               // never throw — see skill gotcha #16
    },
    credentials: false,
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
    maxAge: 600,
  });
}
```

---

## Caddy sidecar

Two-file pattern: keep the platform-host block in `deploy/caddy/<name>.caddy`
(authoritative, in the repo), and materialise per-host blocks from
`/srv/secrets/<name>-custom-domains` at deploy time. The main `Caddyfile`
already does `import /etc/caddy/sites/*.caddy` so both files are picked
up by `caddy reload`.

The deploy helper gets a new function (drop-in snippet at
`templates/extra_hosts_caddy_snippet.sh`):

```bash
write_extra_caddy() {
  local EXTRA_HOSTS_FILE="/srv/secrets/${PROJ_NAME}-custom-domains"
  local EXTRA_SITE_FILE="/srv/caddy/sites/${PROJ_NAME}-extra-hosts.caddy"

  # Seed an empty sidecar on first deploy so the operator knows where to add hosts.
  if [ ! -f "$EXTRA_HOSTS_FILE" ]; then
    cat > "$EXTRA_HOSTS_FILE" <<'SEED'
# Verified custom-domain hostnames this deployment serves.
# One hostname per line; lines beginning with # are comments.
# Example:
#   login.acme.com
SEED
    chmod 644 "$EXTRA_HOSTS_FILE"
  fi

  : > "$EXTRA_SITE_FILE"
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="$(echo "$line" | xargs)"
    [ -z "$line" ] && continue
    cat >> "$EXTRA_SITE_FILE" <<EOF
${line} {
    reverse_proxy ${PROJ_NAME}-web:80
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
        Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=()"
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        Cross-Origin-Opener-Policy "same-origin"
        -X-Powered-By
        -Server
    }
}
EOF
  done < "$EXTRA_HOSTS_FILE"
  chmod 644 "$EXTRA_SITE_FILE"
}
```

Hook it into `do_redeploy()` after `write_caddy`:

```bash
write_caddy
write_extra_caddy
ensure_dns
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

**Don't put extra hostnames in the platform-host site block label**
(`<name>.terrybot.top, login.acme.com { ... }`). It works, but every
domain add/remove then requires a redeploy + cert reissue. The sidecar
file lets an operator add a new verified domain with two commands:

```bash
echo "login.acme.com" >> /srv/secrets/syntra-custom-domains
/srv/scripts/syntra_dev.sh   # materialises the extras file + reloads Caddy
```

---

## Diagnosing a custom-domain bug — diagnostic checklist

Run these in order. Each layer answers a yes/no about its own state.

| Layer | Test | Healthy |
|---|---|---|
| DNS | `dig +short login.acme.com CNAME` | Returns `<name>.<root-domain>` |
| DNS | `dig +short login.acme.com A` (after CNAME walk) | Returns VPS IP |
| Caddy | `docker exec caddy cat /etc/caddy/sites/<name>-extra-hosts.caddy` | Contains a site block for the host |
| Caddy | `docker exec caddy sh -c "ls /data/caddy/certificates/acme-v02.api.letsencrypt.org-directory/ \| grep <host>"` | Cert exists (may take ~30s after first hit) |
| App | `docker exec <api> wget -qO- "http://127.0.0.1:8080/api/public/branding?host=<host>"` | `{"branded":true,...}` |
| App | `curl -X POST -H 'Content-Type: application/json' -d '{...}' -H "Host: <name>.<root>" https://<name>.<root>/api/auth/login` | Response has `redirectTo:"https://<host>/<path>"` |
| HTTPS | `curl -sI --max-time 15 https://<host>/` | HTTP 200 |
| CORS | `curl -sI -X OPTIONS -H "Origin: https://<host>" -H "Access-Control-Request-Method: POST" https://<name>.<root>/api/auth/login` | `access-control-allow-origin: https://<host>` |

If DNS says yes and Caddy says no → bug A (no site block / cert).
If Caddy says yes and app says no → bug B (no redirectTo).
If HTTPS works but the browser blocks the API call → bug C (CORS allowlist).

---

## Pitfalls (each one bit us at least once)

1. **Caddyfile heredoc regenerates the platform-host file every deploy.**
   The deploy script writes `<name>.caddy` from a bash heredoc, not from
   the repo file. Editing `deploy/caddy/<name>.caddy` in the repo has
   zero effect — the heredoc wins. Keep any per-host customisation in
   the sidecar, not in the heredoc, not in the repo file.
2. **ACME cert provisioning lag on first hit.** A new site block returns
   `tlsv1 alert internal error` for ~30s while LE issues the cert. Retries
   succeed. Don't panic; sleep + retry, or pre-warm with a `curl` loop.
3. **DNS doesn't always need to point at the platform host literally.**
   The customer's CNAME can point at the platform subdomain, which then
   A-records to the VPS IP. The `getPlatformTargets()` helper in
   `lib/domain.ts` reads `REPLIT_DOMAINS` and matches against the
   resolved CNAME chain, not just the IP.
4. **One `company.name` row with `domain_status='pending'` is normal.**
   That's the in-flight state between PUT-domain and POST-verify. Don't
   treat `pending` as a bug; verify the verify endpoint exists and that
   the operator actually called it.
5. **Set-cookie over cross-origin redirect is invisible to the SPA.**
   This codebase uses Bearer tokens in localStorage, not cookies — so the
   cross-origin redirect correctly takes the user to the new origin where
   a fresh localStorage is created. If your stack uses cookies, set
   `SameSite=None; Secure` and `credentials: 'include'` on the fetch,
   OR redirect-then-SSO. Don't mix patterns.
6. **The redirectTo host MUST be in the Caddy sidecar** — even if the
   company's `customDomain` is verified in the DB. Otherwise Caddy
   serves nothing for that hostname and the redirected user lands on a
   404. The `getCustomDomainHosts()` helper gates this via
   `buildCustomDomainUrl()`.
7. **Forgetting to clear the sidecar on teardown** leaves orphan
   Caddy site blocks for domains that no longer serve anything.
   `syntra_dev.sh teardown` should `rm -f` both
   `/srv/caddy/sites/<name>.caddy` and
   `/srv/caddy/sites/<name>-extra-hosts.caddy`.

---

## Worked example: SYNTRA `syntra.cyberslide.net` (2026-07-15)

Symptoms Chris reported:
> "users are not being redirected to their url, all are being served
>  from syntra.terrybot.top"

Diagnostic findings (one curl per layer):

| Layer | Pre-fix state |
|---|---|
| DB | company_id=19 (CYBERSLIDE) has `custom_domain='syntra.cyberslide.net'`, `domain_status='verified'` ✓ |
| API: branding | `GET /api/public/branding?host=syntra.cyberslide.net` → `{branded:true, name:"CYBERSLIDE"}` ✓ |
| DNS | `syntra.cyberslide.net → syntra.terrybot.top (CNAME) → 147.79.18.32` ✓ |
| Caddy | `/srv/caddy/sites/syntra.caddy` declares only `syntra.terrybot.top` ✗ |
| HTTPS | `curl -I https://syntra.cyberslide.net/` → blank/timeout ✗ |

Diagnosis: bug A (no vhost) was the proximate cause. Bug B and C were
also present and would have blocked the redirect even after A was fixed.

Files touched (8, +224/−14):
- `artifacts/api-server/src/lib/domain.ts` — `getCustomDomainHosts`,
  `isKnownCustomDomain`, `buildCustomDomainUrl` (with open-redirect guard).
- `artifacts/api-server/src/routes/auth.ts` — `redirectTo` returned by
  `/login`, `/register` (both flows).
- `artifacts/api-server/src/middlewares/cors.ts` — allowlist now
  merges env, platform targets, custom domains.
- `artifacts/web-app/src/pages/login.tsx`,
  `register.tsx`, `accept-invite.tsx` — honour `redirectTo` via
  `window.location.assign`.
- `deploy/syntra_dev.sh` — `write_extra_caddy()` reads
  `/srv/secrets/syntra-custom-domains`, materialises
  `/srv/caddy/sites/syntra-extra-hosts.caddy`, hooked into
  `do_redeploy` + `teardown`.

Live verification commands (run after webhook redeploy completes):

```bash
# 1. Caddy serves the custom domain (ACME issued)
curl -sI --max-time 30 https://syntra.cyberslide.net/
# Expect: HTTP/2 200 (after ~30s for first cert)

# 2. API reachable from the custom origin (CORS allowlist OK)
curl -sI -X OPTIONS \
  -H "Origin: https://syntra.cyberslide.net" \
  -H "Access-Control-Request-Method: POST" \
  https://syntra.terrybot.top/api/auth/login
# Expect: access-control-allow-origin: https://syntra.cyberslide.net

# 3. Login response includes redirectTo for CYBERSLIDE users
curl -sS -X POST https://syntra.terrybot.top/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<cyberslide-user>","password":"…"}' | jq '{token,redirectTo}'
# Expect: redirectTo == "https://syntra.cyberslide.net/dashboard"
```

Post-deploy ops:

```bash
# Add a new verified custom domain without a redeploy:
echo "login.acme.com" >> /srv/secrets/syntra-custom-domains
/srv/scripts/syntra_dev.sh        # materialise + caddy reload
```