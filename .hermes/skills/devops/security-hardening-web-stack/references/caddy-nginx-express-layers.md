# Caddy + nginx + Express — Three-Layer Hardening Reference

Deep-dive with copy-pasteable code for every layer of the hardening
stack. Use as the source of truth when wiring up a new public deploy
or reviewing an existing one.

## Layer 1 — Caddy site block

Drop into `/srv/caddy/sites/<name>.caddy`. The `header { }` block emits
every security header on every response from this site.

```caddyfile
<name>.terrybot.top {
    reverse_proxy <name>-web:80

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
```

**Critical:** if your deploy script (`write_caddy()` in the bash helper)
regenerates this file on every deploy, **it must emit the hardened block,
not a minimal `reverse_proxy`-only block.** Bake the hardened block into
the deploy script so re-deploys never regress.

```bash
# In deploy script:
write_caddy() {
  cat > "$Caddy_FILE" <<EOF
${PROJ_NAME}.${DOMAIN} {
    reverse_proxy ${PROJ_NAME}-web:80
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        # ... full set above ...
    }
}
EOF
}
```

Reload after writes: `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`.

## Layer 2 — nginx `add_header` per location

The SPA container's nginx serves BOTH static SPA and reverse-proxies `/api/*`.
Each `location {}` block redefines headers from scratch — server-level
`add_header` does NOT inherit.

```nginx
server {
    listen 80;
    server_name _;

    # API proxy — re-declare all security headers here
    location /api/ {
        proxy_pass http://api:8080/api/;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        client_max_body_size 20M;

        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        # Tight CSP for API responses — no scripts
        add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none'" always;
    }

    # Static SPA — same set, looser CSP for Vite-bundled inline scripts
    location ~* \.(js|css|woff2?|ttf|eot|svg|ico|png|jpg|jpeg|gif|webp)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;

        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'" always;
    }

    # SPA fallback — index.html for client-side routing
    location / {
        try_files $uri $uri/ /index.html;

        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'" always;
    }
}
```

**Note:** `add_header ... always` makes nginx emit the header even on error
responses (4xx, 5xx). Without `always`, error responses get the default
nginx error page with no headers.

## Layer 3 — Express middlewares

### CORS allowlist

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

`ALLOWED_ORIGINS` env (comma-separated, set in `/srv/secrets/<name>.env`):
```
ALLOWED_ORIGINS=https://syntra.terrybot.top,https://app.acme.com
```

### Trust proxy + body cap + x-powered-by off

```typescript
// app.ts
app.set("trust proxy", 1);  // one hop (Caddy in front)
app.disable("x-powered-by");

app.use(express.json({ limit: "256kb" }));
app.use(express.urlencoded({ extended: true, limit: "256kb" }));
```

### Security headers middleware

```typescript
// middlewares/security-headers.ts
import type { Request, Response, NextFunction, RequestHandler } from "express";

export function securityHeaders(): RequestHandler {
  return (_req: Request, res: Response, next: NextFunction) => {
    res.setHeader(
      "Content-Security-Policy",
      "default-src 'none'; frame-ancestors 'none'",
    );
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("X-Frame-Options", "DENY");
    res.setHeader("Referrer-Policy", "no-referrer");
    res.setHeader("Permissions-Policy", "geolocation=(), microphone=(), camera=()");
    res.setHeader("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
    next();
  };
}
```

### Auth rate-limit

```typescript
// middlewares/rate-limit.ts
import rateLimit from "express-rate-limit";
import { normalizeEmail } from "../lib/email-normalize";

/**
 * Per-account login bucket. Without an explicit `keyGenerator` the limiter
 * silently falls back to per-IP buckets, which means two different accounts
 * sharing the same egress IP will lock each other out on the 6th combined
 * failure. Always read the identifier from the body.
 */
export function loginRateLimitKey(rawEmail: unknown, clientIp: string): string {
  if (typeof rawEmail === "string" && rawEmail.trim()) {
    return normalizeEmail(rawEmail);
  }
  return `ip:${clientIp}`;
}

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
  keyGenerator: (req) => loginRateLimitKey(req.body?.email, req.ip || "unknown"),
  message: { error: "Too many attempts for this account. Please try again in 15 minutes." },
});
```

Wire into routes:
```typescript
import { loginIpLimiter, loginEmailLimiter } from "../middlewares/rate-limit";

router.post("/login", loginIpLimiter, loginEmailLimiter, async (req, res) => { ... });
```

### Generic 500 error handler

```typescript
app.use((err, _req, res, _next) => {
  logger.error(err);  // full error to logs
  res.status(500).json({ error: "Internal server error" });  // generic to client
});
```

**Never** echo `err.message`. Can include DB connection strings, file paths,
library internals — high-value recon for attackers.

## The Pnpm + Multi-Stage Dockerfile Trap (CRITICAL)

When adding a runtime npm dep (e.g. `express-rate-limit`) to a
`pnpm-workspace` monorepo with a multi-stage Dockerfile, you must update
THREE places — the build will fail silently without each one:

| Where | What | Why |
|---|---|---|
| `artifacts/<svc>/package.json` `dependencies` | Add the dep | Build stage resolves it during esbuild |
| **Root `pnpm-lock.yaml`** | Regenerate via `pnpm install --no-frozen-lockfile` | Dockerfile's `pnpm install --frozen-lockfile` fails without this |
| `Dockerfile.<svc>` runtime `FROM ... AS deps` stage | Add to the minimal package.json that's `npm install --production`'d | Runtime stage only installs the named list, not the pnpm tree |

**Symptom:** webhook rebuild fails with `Could not resolve "<pkg>"` from
esbuild. Fix: regenerate the lockfile + update the runtime deps stage +
commit both.

```bash
# 1. Add to package.json
cd /srv/projects/<app>
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

# 3. Update Dockerfile runtime deps stage
# FROM node:20-bookworm-slim AS deps
# RUN echo '{"name":"...","dependencies":{"nodemailer":"^9.0.3","express-rate-limit":"^7.4.1"}}' \
#   > package.json && npm install --production --no-fund --no-audit

# 4. Commit + push (webhook redeploys)
```

**Two-stage check:** if the build succeeds but the runtime container
crashes with `Cannot find module '<pkg>'`, the runtime deps stage was
not updated.

## Verification Snippets

```bash
DOMAIN="syntra.terrybot.top"

# All headers on root
curl -sSI "https://$DOMAIN/" | grep -iE \
  "strict-transport|x-frame|x-content|content-security|referrer|permissions-policy|cross-origin"

# Headers on /api/
curl -sSI "https://$DOMAIN/api/healthz" | grep -iE \
  "strict-transport|x-frame|x-content|content-security|referrer|permissions-policy"

# CORS — random origin REJECTED
curl -sSI -H "Origin: https://evil.example.com" \
  -X OPTIONS "https://$DOMAIN/api/auth/login" \
  | grep -i "access-control-allow-origin" || echo "OK: wildcard CORS not active"

# CORS — allowed origin ACCEPTED
curl -sSI -H "Origin: https://$DOMAIN" \
  -X OPTIONS "https://$DOMAIN/api/auth/login" \
  | grep -i "access-control-allow-origin"

# Rate-limit — 11th attempt in 15 min returns 429
for i in $(seq 1 11); do
  curl -sS -o /dev/null -w "%{http_code} " -X POST \
    "https://$DOMAIN/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"ratelimit@test.com","password":"bad"}'
done
echo
```

A clean post-deploy check looks like:

```
HTTP/2 200
strict-transport-security: max-age=31536000; includeSubDomains
x-content-type-options: nosniff
x-frame-options: DENY
content-security-policy: default-src 'self'; ...
referrer-policy: no-referrer
permissions-policy: geolocation=(), microphone=(), camera=(), payment=()
cross-origin-opener-policy: same-origin
```