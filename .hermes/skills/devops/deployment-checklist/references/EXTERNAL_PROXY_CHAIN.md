# External Reverse Proxy Chain — Payntra Deployment

## Discovered Architecture
```
User Browser
    ↓ HTTPS (port 443)
External Caddy (Control VPS / Cloudflare Tunnel) — terminates TLS, adds `via: 1.1 Caddy`
    ↓ HTTP/HTTPS
Nginx (Dev VPS :80/443) — runs on host, serves dashboard.terrybot.top
    ↓ HTTP
payntra-app container (:3000) — Fastify backend
```

## Key Findings
1. **No local Caddy container** — `/srv/caddy/sites/` doesn't exist, `docker ps` shows no Caddy
2. **Nginx only has `dashboard.terrybot.top` vhost** — no `payntra.terrybot.top` config
3. **External Caddy strips `Domain=` from `Set-Cookie`** — logout works in container but not via public URL
4. **Project deployed via `project_dev.sh`** which expects Caddy container but none exists

## Required Fixes (Priority Order)

### 1. Add Nginx vhost for `payntra.terrybot.top`
```nginx
# /etc/nginx/sites-available/payntra.terrybot.top
server {
    listen 80;
    listen [::]:80;
    server_name payntra.terrybot.top;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name payntra.terrybot.top;

    ssl_certificate /etc/letsencrypt/live/payntra.terrybot.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/payntra.terrybot.top/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://172.19.0.2:3000;  # payntra-app container IP on web network
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass_header Set-Cookie;  # CRITICAL: preserve cookie headers
    }
}
```

### 2. Obtain TLS Certificate
```bash
certbot --nginx -d payntra.terrybot.top
```

### 3. Configure External Caddy to Pass Cookies
```caddy
# On control VPS Caddyfile
payntra.terrybot.top {
    reverse_proxy dev-vps-ip:443 {
        header_down -Set-Cookie  # Don't modify upstream Set-Cookie
    }
}
```

### 4. Update `project_dev.sh` Deploy to Write Nginx Config
The deploy script should generate the Nginx vhost instead of Caddy site block for this project, OR ensure Caddy container runs locally.

## Verification After Fix
```bash
# Test cookie preservation end-to-end
curl -X POST https://payntra.terrybot.top/api/auth/logout -v 2>&1 | grep -i "set-cookie"
# MUST show: Domain=payntra.terrybot.top

# Test full auth flow
# 1. Sign up
# 2. Login → cookie set
# 3. Access /ledger/2026-07 → works
# 4. Logout → redirect to login
# 5. Reload → NOT logged in (cookie cleared)
```

## Related Skills
- `docker-network-troubleshooting` — MTU, SMTP, reverse proxy cookie issues
- `deployment-checklist` — post-deploy smoke tests including cookie verification