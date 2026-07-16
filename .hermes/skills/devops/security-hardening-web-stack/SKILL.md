---
name: security-hardening-web-stack
description: "OWASP Top 10 baseline hardening for a public web app — security headers at three layers (Caddy + nginx + Express), wildcard CORS removal with ALLOWED_ORIGINS allowlist, auth-endpoint rate-limit, body-size cap, generic 500 messages, and verification curl checks. Use when hardening a new public deploy, when an audit flags missing headers / wildcard CORS / brute-force exposure, or when running a security review. Triggers on 'security headers', 'CORS allowlist', 'rate limit login', 'OWASP baseline', 'Caddy HSTS CSP', 'express helmet', 'security audit', 'harden the stack', 'cors() is leaking'."
---

# Security Hardening — Web Stack Baseline

A class-level reference for hardening any public-facing web app to the OWASP
Top 10 (2021) baseline. Captures the three-layer header pattern (Caddy +
nginx + Express), wildcard CORS removal, auth rate-limiting, body-size cap,
and the curl commands to verify hardening post-deploy.

For deployment-specific wiring (custom domain env, Hetzner MTU, webhook
auto-redeploy), see `deploy-app-to-dev-vps`. This skill is the **policy
and pattern reference**; that skill is the **workflow reference**.

## The Three-Layer Hardening Model

```
Client
  │
  ▼
┌──────────────────────────────────────┐
│  Caddy (TLS 1.3 + Let's Encrypt)     │ ← headers emitted HERE
└────────────────┬─────────────────────┘
                 │
┌────────────────▼─────────────────────┐
│  nginx (per-location headers)        │ ← headers emitted HERE
└────────────────┬─────────────────────┘
                 │
┌────────────────▼─────────────────────┐
│  Express (defense in depth)          │ ← headers emitted HERE
└──────────────────────────────────────┘
```

**All three layers emit the same headers.** Intentional defense in depth —
if any layer is misconfigured or bypassed (debug port, direct container
access, future proxy swap), the others still hold.

## Mandatory Headers (OWASP baseline)

| Header | Value | Purpose |
|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS for 1 year |
| `X-Content-Type-Options` | `nosniff` | Block MIME sniffing |
| `X-Frame-Options` | `DENY` | Block clickjacking |
| `Referrer-Policy` | `no-referrer` | No referrer sent |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=(), payment=()` | Disable unused browser APIs |
| `Content-Security-Policy` | `default-src 'self'; ...` | Block XSS, restrict origins |
| `Cross-Origin-Opener-Policy` | `same-origin` | Cross-origin isolation |
| `-X-Powered-By` | (strip) | Remove framework fingerprint |
| `-Server` | (strip at proxy) | Remove server fingerprint |

For SPA responses, CSP needs to allow `script-src 'self' 'unsafe-inline'`
(Vite-built bundles inject inline scripts). For `/api/*` responses, CSP
should be `default-src 'none'; frame-ancestors 'none'` (no scripts at all).

## Critical Gotchas (one-line version — read references for details)

1. **`add_header` doesn't inherit from `server {}` to `location {}`** in
   nginx. Re-declare per location block. See `references/caddy-nginx-express-layers.md`.
2. **`app.use(cors())` with no options** allows ANY origin. Replace with
   the allowlist pattern. HIGH severity for any public API.
3. **No `app.set('trust proxy', 1)`** behind a proxy → rate-limit per-IP
   fails open (everyone shares one bucket).
3a. **`loginEmailLimiter` defaults to IP-keyed buckets** if no
   `keyGenerator` is supplied. The `max: 5` reads as "5 attempts per
   account" but is in fact "5 attempts per IP for that account's IP" —
   and worse, a different account's 6th failure from the same IP will
   cause this account to be locked out by the limiter that's supposed
   to be protecting that account. Always pass a `keyGenerator` that
   reads from the request body (normalized) and falls back to the IP
   only when the identifier is unavailable:
   ```ts
   keyGenerator: (req) => loginRateLimitKey(req.body?.email, req.ip || "unknown")
   ```
   Symptom: "users can't log in from the base URL after a few attempts,
   even with the right password." Verify with two consecutive bad logins
   for different accounts from the same egress IP — only the IP-shared
   limiter is wrong if the second account's failure 429s the first.
4. **`express.json()` with no limit** is a DoS surface. 256 KB is generous
   for normal payloads.
5. **Generic 500 messages** — never echo `err.message`. Can include DB
   connection strings, file paths, library internals.
6. **Pino log serializer strips body/headers/query** — credentials never
   reach logs. Keep this default.

## Verification (post-deploy)

After applying the hardening, run these curl checks. Expect every header
to be present on every response type (root, `/api/*`, static).

```bash
DOMAIN="<name>.terrybot.top"

# Headers present on root
curl -sSI "https://$DOMAIN/" | grep -iE \
  "strict-transport|x-frame|x-content|content-security|referrer|permissions-policy"

# Headers present on /api/
curl -sSI "https://$DOMAIN/api/healthz" | grep -iE \
  "strict-transport|x-frame|x-content|content-security|referrer|permissions-policy"

# CORS — random origin REJECTED (no Access-Control-Allow-Origin)
curl -sSI -H "Origin: https://evil.example.com" \
  -X OPTIONS "https://$DOMAIN/api/auth/login" \
  | grep -i "access-control-allow-origin" || echo "OK: wildcard CORS not active"

# CORS — allowed origin ACCEPTED
curl -sSI -H "Origin: https://$DOMAIN" \
  -X OPTIONS "https://$DOMAIN/api/auth/login" \
  | grep -i "access-control-allow-origin"

# Rate-limit — 11th login attempt within 15 min returns 429
for i in $(seq 1 11); do
  curl -sS -o /dev/null -w "%{http_code} " -X POST \
    "https://$DOMAIN/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"ratelimit@test.com","password":"bad"}'
done
echo
```

Full hardening pattern + Caddy site block + nginx config + Express
middleware + the pnpm-multi-stage Dockerfile trap → see
`references/caddy-nginx-express-layers.md`.

OWASP Top 10 audit template (severity ratings, per-finding remediation
status) → `references/owasp-audit-template.md`.

## Related

- `deploy-app-to-dev-vps` — workflow skill. Gotchas #10–#13 cover the
  deploy-side of these patterns (pnpm-lock trap, add_header gotcha,
  wildcard CORS, trust proxy).
- `references/caddy-nginx-express-layers.md` — copy-pasteable code
  for each layer + the Caddy site block template.
- `references/owasp-audit-template.md` — full audit template (top 10
  categories, severity legend, finding-status column).
- `deployment-checklist` — pre/post-deploy verification gates that
  should reference this skill.
- `docker-network-troubleshooting` — if builds hang before you can
  verify hardening (MTU issue blocks the build, not the headers).