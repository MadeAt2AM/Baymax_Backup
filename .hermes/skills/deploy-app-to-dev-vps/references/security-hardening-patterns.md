# Security Hardening Patterns (Caddy + nginx + Express)

Class-level reference for hardening a public web app deployed on the dev VPS.
Captures the three-layer header pattern, wildcard CORS removal, rate-limit,
and body-size cap, with copy-pasteable snippets and verification commands.

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

**All three layers emit the same headers.** This is intentional defense in
depth: if any layer is misconfigured or bypassed (debug access, direct
container port, future proxy swap), the others still hold.

## Caddy Site Block (drop into `/srv/caddy/sites/<name>.caddy`)

```caddyfile
<name>.terrybot.top {
    reverse_proxy <name>-web:80

    header {
        # Force HTTPS for 1 year incl subdomains
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        # Prevent MIME-type sniffing
        X-Content-Type-Options "nosniff"
        # Prevent clickjacking
        X-Frame-Options "DENY"
        # No referrer sent by default
        Referrer-Policy "no-referrer"
        # Disable dangerous browser APIs we don't use
        Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=()"
        # CSP — same-origin only; no inline scripts except styles
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        # Cross-origin isolation
        Cross-Origin-Opener-Policy "same-origin"
        # Strip server fingerprints
        -X-Powered-By
        -Server
    }
}
```

**Critical:** if your `write_caddy()` function in the deploy script
overwrites this file on every deploy, **it must emit the hardened block,
not a minimal `reverse_proxy`-only block.** Bake the hardened block
into the deploy script so re-deploys never regress.

## nginx: `add_header` Inherits NOT (per-location gotcha)

`add_header` declared in the outer `server {}` block is **dropped** by every
`location {}` block that defines its own `add_header`. Per nginx docs,
child location blocks redefine headers from scratch — they do NOT inherit.

This matters because the SPA container's nginx serves BOTH the static SPA
and reverse-proxies `/api/*`. If you put `add_header X-Frame-Options "DENY"`
in `server {}` but `location /api/ {}` has its own `add_header` (e.g. for
CSP), the X-Frame-Options is dropped from `/api/*` responses.

**Fix: declare every header inside every location block.**

```nginx
server {
    listen 80;
    server_name _;

    location /api/ {
        proxy_pass http://api:8080/api/;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Re-declare ALL security headers here — do not rely on server {}
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none'" always;
    }

    location / {
        try_files $uri $uri/ /index.html;
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        # ... same set ...
    }
}
```

## Express: CORS Allowlist (kill the wildcard)

```typescript
// middlewares/cors.ts
import cors from "cors";

export function buildCors(): ReturnType<typeof cors> {
  const fallback = ["https://<name>.terrybot.top"];
  const fromEnv = (process.env["ALLOWED_ORIGINS"] ?? "")
    .split(",").map(s => s.trim()).filter(Boolean);
  const allowed = fromEnv.length > 0 ? fromEnv : fallback;

  return cors({
    origin: (origin, cb) => {
      if (!origin) return cb(null, true);                // same-origin / curl
      if (allowed.includes(origin)) return cb(null, true);
      return cb(new Error(`Origin ${origin} not allowed by CORS`));
    },
    credentials: false,                                  // we use Bearer tokens
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
    maxAge: 600,
  });
}
```

Then in `app.ts`:
```typescript
import { buildCors } from "./middlewares/cors";
app.use(buildCors());
```

**Why this matters:** `app.use(cors())` with no options allows ANY origin.
Combined with the JWT-in-localStorage auth, a malicious page could attempt
to read responses if it could plant headers on a victim. This is HIGH
severity for any public-facing API.

## Express: `trust proxy` for Rate-Limit

```typescript
// app.ts
app.set("trust proxy", 1);  // trust one hop (Caddy in front)
```

Without this, `req.ip` is `127.0.0.1` (the Caddy container) — rate-limit
treats ALL traffic as coming from one IP, defeating per-IP brute-force
protection. `1` means "trust one proxy hop" — never trust
`X-Forwarded-For` from the public internet directly.

## Express: Body Size Cap + Generic Error Messages

```typescript
app.use(express.json({ limit: "256kb" }));
app.use(express.urlencoded({ extended: true, limit: "256kb" }));

app.disable("x-powered-by");

// Global error handler — never leaks err.message
app.use((err, _req, res, _next) => {
  logger.error(err);
  res.status(500).json({ error: "Internal server error" });
});
```

`express.json()` with no limit allows multi-MB JSON bodies that exhaust
memory. 256 KB is generous for normal API payloads and defeats the
worst-case DoS. The generic 500 prevents stack traces, DB connection
strings, and file paths from leaking to clients.

## Express: Auth Rate-Limit (express-rate-limit)

```typescript
// middlewares/rate-limit.ts
import rateLimit from "express-rate-limit";

export const loginIpLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: "Too many login attempts. Please try again in 15 minutes." },
});

export const loginEmailLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: "Too many attempts for this account." },
});
```

Wire into routes:
```typescript
router.post("/login", loginIpLimiter, loginEmailLimiter, async (req, res) => { ... });
```

Two layers defeats both brute-force (same IP) and credential-stuffing
(different IPs targeting the same email).

## The CRITICAL Pnpm + Multi-Stage Dockerfile Trap

When you add a runtime npm dependency (e.g. `express-rate-limit`) to a
`pnpm-workspace` monorepo with a multi-stage Dockerfile, the dep won't be
in the final image unless you update THREE places:

| Where | What | Why |
|---|---|---|
| `artifacts/<svc>/package.json` `dependencies` | Add the dep | Build stage resolves it during esbuild |
| **Root `pnpm-lock.yaml`** | Regenerate via `pnpm install --no-frozen-lockfile` in monorepo root | Dockerfile's `pnpm install --frozen-lockfile` will fail without this |
| `Dockerfile.<svc>` runtime `FROM ... AS deps` stage | Add to the minimal package.json that's `npm install --production`'d | Runtime stage only installs the named list, NOT the pnpm tree |

**Symptom if you miss any:** webhook rebuild fails with
`Could not resolve "<pkg>"` from esbuild, OR the runtime image has the dep
in `node_modules/` but the build-time resolver can't find it.

**Recovery:**
```bash
# 1. Add dep to package.json (manually or via pnpm add)
cd /srv/projects/<app>  # or your local clone
python3 -c "
import json
p = 'artifacts/api-server/package.json'
with open(p) as f: d = json.load(f)
d['dependencies']['express-rate-limit'] = '^7.4.1'
with open(p, 'w') as f: json.dump(d, f, indent=2)
"

# 2. Regenerate lockfile (one-time, not in Dockerfile)
docker run --rm -v "$PWD:/workspace" -w /workspace node:20-bookworm-slim \
  bash -c "corepack enable && corepack prepare pnpm@10 --activate && pnpm install --no-frozen-lockfile"

# 3. Add to Dockerfile runtime deps stage:
#    FROM node:20-bookworm-slim AS deps
#    RUN echo '{"name":"...","dependencies":{"nodemailer":"...","express-rate-limit":"^7.4.1"}}' \
#      > package.json && npm install --production --no-fund --no-audit

# 4. Commit and push (webhook redeploys)
```

## Verification Commands

After deploying hardened config, run these from anywhere:

```bash
DOMAIN="syntra.terrybot.top"

# All security headers present?
curl -sSI "https://$DOMAIN/" | grep -iE "strict-transport|x-frame|x-content|content-security|referrer|permissions-policy"

# HSTS specifically (must be 1 year + includeSubDomains)
curl -sSI "https://$DOMAIN/" | grep -i strict-transport-security

# CSP on /api/ responses
curl -sSI "https://$DOMAIN/api/healthz" | grep -i content-security-policy

# CORS — random origin should be REJECTED (no Access-Control-Allow-Origin)
curl -sSI -H "Origin: https://evil.example.com" \
  -X OPTIONS "https://$DOMAIN/api/auth/login" \
  | grep -i "access-control-allow-origin" || echo "OK: wildcard CORS not active"

# CORS — allowed origin should be ACCEPTED
curl -sSI -H "Origin: https://$DOMAIN" \
  -X OPTIONS "https://$DOMAIN/api/auth/login" \
  | grep -i "access-control-allow-origin"

# Rate-limit on login — should return 429 after 10 attempts in 15 min
for i in $(seq 1 12); do
  curl -sS -o /dev/null -w "%{http_code} " -X POST \
    "https://$DOMAIN/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"ratelimit@test.com","password":"bad"}'
done
echo ""  # expect last 2 to be 429
```

A clean post-deploy check looks like:

```bash
curl -sSI https://syntra.terrybot.top/ | head -20
# Expect: HTTP/2 200, then:
#   strict-transport-security: max-age=31536000; includeSubDomains
#   x-content-type-options: nosniff
#   x-frame-options: DENY
#   content-security-policy: default-src 'self'; ...
#   referrer-policy: no-referrer
#   permissions-policy: geolocation=(), microphone=(), camera=(), payment=()
#   cross-origin-opener-policy: same-origin
```

## Common Mistakes

- **Forget to update `Dockerfile.<svc>` runtime deps stage** — only
  updating `package.json` and `pnpm-lock.yaml` leaves the runtime
  image without the dep. The error message is the same as the missing
  lockfile update; check both.
- **`app.use(cors())` with no options** — wildcard, allows any origin.
  Replace with the allowlist pattern above.
- **`add_header` only in `server {}`** — dropped by every `location {}`
  block that has its own `add_header`. Re-declare per location.
- **No `app.set('trust proxy', 1)`** — rate-limit fails open (everyone
  shares one bucket).
- **`app.use(express.json())` with no limit** — DoS surface.
- **`err.message` echoed in 500 responses** — leaks DB strings, file
  paths, stack traces. Use generic `"Internal server error"`.

## Related

- `deploy-app-to-dev-vps/SKILL.md` gotchas #10-#13 cover the deployment-side
  of these patterns.
- `caddy-service-dns-aliases` — reverse-proxy / network layer.
- `docker-network-troubleshooting` — MTU issues that block the build before
  hardening can be tested.
- `deployment-checklist` — pre/post-deploy verification gates.