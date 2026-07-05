# Reverse Proxy Cookie Stripping — Debugging Guide

## The Problem
External reverse proxy (Caddy on control VPS) was stripping `Domain=payntra.terrybot.top` from `Set-Cookie` headers during logout, causing cookie to persist in browser despite successful API response.

## Architecture
```
Client (browser)
  → External Caddy (control VPS / Cloudflare tunnel) — terminates TLS
    → Nginx (dev VPS :80/443) — serves dashboard.terrybot.top
      → payntra-app container (:3000) — Fastify backend
```

## Evidence
- Response header: `via: 1.1 Caddy` (no local Caddy container found)
- Direct container test: `Domain=payntra.terrybot.top` present in `Set-Cookie`
- Public URL test: `Domain=` missing, cookie not cleared

## Root Cause
External Caddy default behavior may strip/modify `Set-Cookie` headers from upstream.

## Fix Options

### Option 1: Configure External Caddy to Preserve Cookies
```caddy
# In external Caddyfile
payntra.terrybot.top {
    reverse_proxy nginx-dev-vps:443 {
        # Pass Set-Cookie headers unchanged
        header_down -Set-Cookie  # Removes any modification
        # OR explicitly allow
        header_down Set-Cookie {upstream}
    }
}
```

### Option 2: Configure Nginx to Not Modify Cookies
```nginx
# In Nginx vhost for payntra.terrybot.top
location / {
    proxy_pass http://payntra-app:3000;
    proxy_pass_header Set-Cookie;  # Explicitly pass through
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Option 3: Remove Domain from Backend Cookie (Less Secure)
Set cookie without explicit domain in Fastify — browser uses request host.
```typescript
// In config.ts cookieOptions()
return {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    // domain: env.COOKIE_DOMAIN,  // REMOVE THIS
    path: '/',
    maxAge: 60 * 60 * 24 * 30,
};
```
Trade-off: Cookie sent to all subdomains of terrybot.top (less secure).

## Verification Script
```bash
#!/bin/bash
# test-cookie-preservation.sh
# Run after any proxy config change

APP_URL="https://payntra.terrybot.top"

echo "=== Testing logout cookie ==="
curl -X POST "$APP_URL/api/auth/logout" -v 2>&1 | grep -i "set-cookie"

echo -e "\n=== Expect to see: ==="
echo "payntra_token=; Domain=payntra.terrybot.top; Path=/; Expires=...; Secure; SameSite=Lax"
```

## Related Files
- `/root/projects/payntra/server/src/config.ts` — cookie options (domain included)
- `/root/projects/payntra/server/src/routes/auth.ts` — logout endpoint with clearCookie
- `deployment-checklist` skill — post-deploy cookie verification step