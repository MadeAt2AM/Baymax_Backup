---
name: secure-web-dashboard
description: Expose a local Hermes dashboard via Nginx with HTTPS, HTTP Basic Auth, Let's Encrypt, and Systemd persistence. Includes TUI support, correct Host/Connection header forwarding, and the critical nginx Authorization header fix for SPA auth.
category: devops
version: 2.1
---

# Secure Web Dashboard with Nginx, HTTP Basic Auth, Let's Encrypt, and Systemd

## Overview

This skill provides a repeatable process to expose a local Hermes dashboard (port 9119) via a domain name with:
- HTTPS using Let's Encrypt (Certbot)
- HTTP Basic Auth protection via nginx `auth_basic`
- Correct header forwarding to avoid **"Invalid Host header"** and **WebSocket 401** errors
- Systemd service for dashboard persistence across reboots
- TUI (Terminal User Interface) support

## When to Use

- You have a locally-bound web service (`hermes dashboard --port 9119 --host 127.0.0.1`)
- You own a domain pointing to the server's public IP
- You want password-protected HTTPS access with TUI and WebSocket support

## Prerequisites

- Root or sudo on Ubuntu/Debian
- `hermes` CLI installed and in PATH
- Domain DNS A record pointing to the server's public IP
- Ports 80 and 443 open in firewall
- (Optional) email for Let's Encrypt renewal notices

---

## Procedure

### 1. Install packages

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx apache2-utils
```

### 2. Create HTTP Basic Auth credentials

```bash
sudo htpasswd -c -b /etc/nginx/.htpasswd chrisspeaks Cris0037
```

> **Critical:** Use `-c` only the FIRST time (creates file). Running `-c` again WIPES the file. To change password later: `sudo htpasswd -b /etc/nginx/.htpasswd chrisspeaks <newpassword>`

### 3. Start dashboard locally

```bash
hermes dashboard --port 9119 --host 127.0.0.1 --no-open --tui &
```

Verify:
```bash
curl -s http://127.0.0.1:9119 | head -3
# Expected: <!doctype html>
```

### 4. Obtain Let's Encrypt certificate

```bash
sudo certbot --nginx -d dashboard.terrybot.top \
  --non-interactive --agree-tos --email chrisvinclaw@gmail.com
```

Certbot auto-creates the nginx site config. Test renewal:
```bash
sudo certbot renew --dry-run
```

### 5. Configure Nginx reverse proxy

**Overwrite the Certbot-generated config** with this complete, tested config:

```nginx
# HTTP -> HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name dashboard.terrybot.top;
    return 301 https://$host$request_uri;
}

# HTTPS reverse proxy with Basic Auth
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name dashboard.terrybot.top;

    ssl_certificate /etc/letsencrypt/live/dashboard.terrybot.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dashboard.terrybot.top/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # HTTP Basic Auth — browser caches this and sends on every subsequent request
    auth_basic "Hermes";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:9119;
        proxy_http_version 1.1;

        # CRITICAL: Hermes uvicorn's _is_accepted_host checks Host header
        # against bound_host (127.0.0.1). It REJECTS the port suffix —
        # "Host: 127.0.0.1:9119" != bound "127.0.0.1". Must strip port.
        # Also rewrite Origin — Hermes checks origin against bound_host too.
        proxy_set_header Host 127.0.0.1;
        proxy_set_header Origin "http://127.0.0.1";

        # Real client IP
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CRITICAL: nginx's auth_basic CONSUMES the Authorization header.
        # We MUST strip it before forwarding so the backend only sees the
        # SPA's own X-Hermes-Session-Token header for API auth.
        proxy_set_header Authorization "";

        # WebSocket upgrade — auth_basic is bypassed in the nested location
        proxy_set_header Connection "upgrade";
        proxy_set_header Proxy-Connection "keep-alive";
    }

    # All API routes — backend owns auth via X-Hermes-Session-Token
    # CRITICAL: Must come before the WS-specific block.
    # Routes like /api/plugins/kanban/* (kanban board), /api/status, /api/sessions
    # do NOT match the WS regex, so without this block they fall through to
    # server-level auth_basic and get 401ed on every request — causing repeated
    # browser password dialogs even after a valid session token was obtained.
    location ~ ^/api/ {
        proxy_pass http://127.0.0.1:9119;
        proxy_http_version 1.1;

        # Strip port — Hermes uvicorn rejects "Host: 127.0.0.1:9119"
        proxy_set_header Host 127.0.0.1;
        proxy_set_header Origin "http://127.0.0.1";

        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Strip Authorization to prevent backend seeing Basic Auth
        proxy_set_header Authorization "";

        # WebSocket upgrade headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Proxy-Connection "keep-alive";

        # Disable auth_basic for all API routes — backend validates session token
        auth_basic off;
    }

    # WebSocket upgrade requests hit this nested location FIRST.
    # auth_basic is disabled here so nginx does NOT intercept the upgrade.
    # The backend itself validates the ?token= query param via HMAC.
    # Without this, nginx's auth_basic intercepts the WS upgrade at the
    # access phase BEFORE proxy_pass — the browser's WebSocket doesn't carry
    # Basic Auth so nginx returns its own 401 before the request ever reaches
    # uvicorn. This is why Connection: Upgrade alone was insufficient.
    location ~ ^/api/(ws|pty|events|pub)$ {
        proxy_pass http://127.0.0.1:9119;
        proxy_http_version 1.1;

        # CRITICAL: Strip port from both headers — Hermes uvicorn's
        # _is_accepted_host rejects "Host: 127.0.0.1:9119" and
        # origin check rejects "http://127.0.0.1:9119"
        proxy_set_header Host 127.0.0.1;
        proxy_set_header Origin "http://127.0.0.1";

        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Strip Authorization to prevent backend seeing Basic Auth
        proxy_set_header Authorization "";

        # WebSocket upgrade headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Proxy-Connection "keep-alive";

        # Disable auth_basic for this location — backend owns WS auth via ?token=
        auth_basic off;
    }
}
```

Enable and reload:
```bash
sudo ln -sf /etc/nginx/sites-available/dashboard.terrybot.top /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Test:
```bash
curl -k -u chrisspeaks:Cris0037 -s https://dashboard.terrybot.top/ | head -3
```

### 6. Create Systemd service

> **NOTE — Update behavior:** `hermes update` intentionally kills the dashboard after refreshing code ("Stopping N dashboard process(es)...") and prints *"Restart the dashboard when you're ready"* but does NOT restart it automatically. After every `hermes update`, always restart the dashboard:
> ```bash
> sudo systemctl restart hermes-dashboard.service
> ```

```ini
[Unit]
Description=Hermes Agent Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/usr/local/lib/hermes-agent/venv/bin/hermes dashboard --port 9119 --host 127.0.0.1 --no-open --tui
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-dashboard.service
```

### 7. Final verification

```bash
# Public endpoint
curl -k -u chrisspeaks:Cris0037 -s https://dashboard.terrybot.top/api/status | python3 -m json.tool

# Protected endpoint (session token via browser's SPA JS)
# Visit https://dashboard.terrybot.top in browser, login with chrisspeaks/Cris0037
# The SPA automatically sends X-Hermes-Session-Token header from window.__HERMES_SESSION_TOKEN__

# WebSocket test (direct to backend — use this to isolate WS issues)
# IMPORTANT: Host header must NOT include port — Hermes uvicorn rejects
# "Host: 127.0.0.1:9119". Use just "Host: 127.0.0.1".
TOKEN=$(curl -s http://127.0.0.1:9119/ | grep -oP 'window\.__HERMES_SESSION_TOKEN__=\K[^;]+' | tr -d '"')
python3 -c "
import socket, base64, ssl
key = base64.b64encode(b'test1234test1234').decode()
sock = socket.create_connection(('127.0.0.1', 9119))
req = f'GET /api/ws?token={open(\"/dev/stdin\").read() if False else \"$TOKEN\"} HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
sock.send(req.encode())
print(sock.recv(4096).decode()[:200])
"
```

---

## Maintenance

| Task | Command |
|------|---------|
| Restart dashboard | `sudo systemctl restart hermes-dashboard.service` |
| View logs | `journalctl -u hermes-dashboard -f` |
| Update password | `sudo htpasswd -b /etc/nginx/.htpasswd chrisspeaks <newpassword>` |
| Reload Nginx | `sudo systemctl reload nginx` (for routine config changes) |\n| **Restart Nginx** | `sudo systemctl restart nginx` — **required after any WebSocket/header-related config change**; `reload` leaves old workers running with stale config |\n| Check cert renewal | `sudo certbot renew --dry-run` |
| Restart everything | `sudo systemctl restart hermes-dashboard nginx` |

---

## Pitfalls & Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| **"Invalid Host header"** | Backend receives wrong Host value | Use `proxy_set_header Host 127.0.0.1;` (no port) — Hermes uvicorn rejects `Host: 127.0.0.1:9119`. Port 9119 is the local bound port; the Host header should only carry the address. The `proxy_pass` directive handles port routing |
| **502 Bad Gateway** | Dashboard not running | `sudo systemctl restart hermes-dashboard`. **Most common trigger: `hermes update`** — it stops the dashboard after code refresh and never restarts it. Check `tail /root/.hermes/logs/hermes-update.log` for timestamp. Always restart the service after updates. |
| **Repeated login prompts / 401 on XHR calls** | Nginx forwarding `Authorization: Basic` to backend — conflicts with session token auth | Add `proxy_set_header Authorization "";` — the SPA sends its own `X-Hermes-Session-Token` header; nginx must not pass the consumed Basic Auth through |
| **WebSocket 4401 "Auth failed"** | `Connection` header stripped, or token mismatch in query param | Must use `proxy_set_header Connection "upgrade";` (NOT `""`). WS auth uses `?token=<session>` query param, not headers. SPA appends token correctly to WS URLs |
| **WebSocket 403 through nginx, Hermes logs "origin_mismatch"** | Hermes uvicorn's `_is_accepted_host` rejects `Host: 127.0.0.1:9119` (port included) — only `bound_host` (`127.0.0.1`) without port is accepted. Origin header (`http://127.0.0.1:9119`) also mismatches | Strip port from BOTH `Host` AND `Origin` in all three location blocks: `proxy_set_header Host 127.0.0.1;` and `proxy_set_header Origin "http://127.0.0.1";` (no `:9119`). **Then `systemctl restart nginx`** — `reload` leaves old workers with stale config; only `restart` guarantees all workers pick up WS header changes |
| **WS works direct but fails through nginx after config change** | `nginx reload` updates config but existing workers keep old config — only new requests may hit new workers | Always `systemctl restart nginx` after WebSocket-related config changes, not just `reload` |
| **API route returns HTML instead of JSON (e.g. `/api/status` returns SPA shell)** | `location ~ ^/api/` block missing — request fell through to default proxy which served the HTML SPA for a non-existent route | Add the broad `location ~ ^/api/ { auth_basic off; }` block before the WS-specific block |
| **Repeated login prompts after valid basic-auth login** | API routes (plugins, sessions, kanban board) hit nginx's `auth_basic` before the backend session-token check — browser gets 401 on XHR, re-prompts for Basic Auth | Add `location ~ ^/api/ { auth_basic off; }` before the WS block — backend owns session-token auth for all `/api/*` routes |
| **TUI not accessible** | `--tui` flag missing | Add `--tui` to `ExecStart` and `sudo systemctl daemon-reload && systemctl restart hermes-dashboard` |
| **Intermittent 401s even with correct password** | Duplicate htpasswd entries for same user | `sudo cat /etc/nginx/.htpasswd` — should have exactly one entry per user. Regenerate with `sudo htpasswd -c -b /etc/nginx/.htpasswd chrisspeaks Cris0037` |
| **WS works direct but fails through nginx** | nginx not forwarding `Connection: Upgrade` | Must use `proxy_set_header Connection "upgrade";` — bare `upgrade` value, not `$http_upgrade` |
| **WS still 401 through nginx after Connection: upgrade fix** | nginx `auth_basic` intercepts the WS upgrade at access phase before `proxy_pass` — browser WebSocket doesn't carry Basic Auth so nginx returns its own 401 | Add `location ~ ^/api/(ws|pty|events|pub)$` with `auth_basic off;` — backend validates `?token=` via HMAC, not nginx |

---

## References

- [Hermes update + dashboard restart procedure](references/update-cron-dashboard-restart.md) — the update-kills-dashboard problem, correct cron sequence, EADDRINUSE fix
- [Auth Architecture deep-dive](references/auth-architecture.md) — full two-layer auth flow, header stripping rationale, WebSocket token handling, and htpasswd duplication pitfall
- [Nginx proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Certbot Nginx plugin](https://certbot.eff.org/instructions)
- [Systemd service manual](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
