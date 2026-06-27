---
name: secure-web-dashboard
description: Expose a local web dashboard via Nginx with HTTPS, HTTP Basic Auth, Let's Encrypt, and Systemd persistence. Includes TUI support and correct Host-header forwarding to prevent "Invalid Host header" errors.
category: devops
version: 1.0
---

# Secure Web Dashboard with Nginx, HTTP Basic Auth, Let's Encrypt, and Systemd

## Overview
This skill provides a repeatable process to expose a local web dashboard (Hermes Agent on port 9119) via a domain name with:
- HTTPS using Let's Encrypt (Certbot)
- HTTP Basic Auth protection
- Correct Host-header forwarding to avoid **"Invalid Host header"** errors during backend validation
- Systemd service for dashboard persistence across reboots
- TUI (Terminal User Interface) support enabled

## When to Use
- You have a locally-bound web service (e.g., `hermes dashboard --port 9119 --host 127.0.0.1`)
- You own a domain pointing to the server's public IP
- You want secure, password-protected HTTPS access with TUI support

## Prerequisites
- Root or sudo access on a Ubuntu/Debian-like system
- `hermes` CLI installed and in PATH
- Domain DNS A record pointing to the server's public IP
- Ports 80 and 443 open in firewall
- (Optional) A working email for Let's Encrypt notifications

## Context (auto-injected)
Domain used: `dashboard.terrybot.top`
Dashboard port: `9119`
Dashboard host: `127.0.0.1`
Auth username: `chrisspeaks`
Auth password: `Cris0037`
TUI: enabled

---

## Procedure

### 1. Install required packages

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx apache2-utils
```

`apache2-utils` provides `htpasswd` for HTTP Basic Auth.

### 2. Create HTTP Basic Auth credentials

```bash
sudo htpasswd -c -b /etc/nginx/.htpasswd chrisspeaks Cris0037
```

To change the password later (without overwriting the file):
```bash
sudo htpasswd -b /etc/nginx/.htpasswd chrisspeaks <newpassword>
```

### 3. Start the dashboard locally

The dashboard must run on `127.0.0.1:9119` so Nginx can proxy to it. Use the `--no-open` flag to prevent browser auto-launch, and `--tui` to enable the embedded terminal UI:

```bash
hermes dashboard --port 9119 --host 127.0.0.1 --no-open --tui &
```

Verify it's reachable locally:
```bash
curl -s http://127.0.0.1:9119 | head -3
# Should return: <!doctype html>
```

### 4. Obtain Let's Encrypt certificate

Run Certbot with the Nginx plugin (non-interactive). Replace `dashboard.terrybot.top` with your domain and `chrisvinclaw@gmail.com` with your email:

```bash
sudo certbot --nginx -d dashboard.terrybot.top --non-interactive --agree-tos --email chrisvinclaw@gmail.com
```

Certbot will:
- Obtain a certificate and save it to `/etc/letsencrypt/live/dashboard.terrybot.top/`
- Modify (or create) an Nginx site config
- Set up automatic renewal via a systemd timer

Test certificate renewal:
```bash
sudo certbot renew --dry-run
```

### 5. Configure Nginx reverse proxy

**Critical:** The Hermes backend validates the `Host` header and rejects anything unexpected. You must send a single `Host: 127.0.0.1:9119` header — NOT two Host headers (which causes backend rejection).

Create `/etc/nginx/sites-available/dashboard.terrybot.top`:

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

    # HTTP Basic Auth
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:9119;
        proxy_http_version 1.1;

        # Single Host header — backend expects 127.0.0.1:9119
        proxy_set_header Host 127.0.0.1:9119;

        # Pass real client IP
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Forward Authorization so backend XHR calls don't re-prompt
        proxy_set_header Authorization $http_authorization;

        # Clear hop-by-hop headers
        proxy_set_header Connection "";
        proxy_set_header Proxy-Connection "";
    }
}
```

Enable the site and reload Nginx:
```bash
sudo ln -sf /etc/nginx/sites-available/dashboard.terrybot.top /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default   # remove default site if it conflicts
sudo nginx -t
sudo systemctl reload nginx
```

Test the full stack:
```bash
curl -k -u chrisspeaks:Cris0037 -s https://dashboard.terrybot.top/ | head -3
# Should return: <!doctype html>
```

### 6. Create Systemd service for persistence

Create `/etc/systemd/system/hermes-dashboard.service`:

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

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-dashboard.service
```

Check status:
```bash
sudo systemctl status hermes-dashboard.service
```

View logs:
```bash
journalctl -u hermes-dashboard -f
```

### 7. Final verification

From a browser, navigate to `https://dashboard.terrybot.top`:
- You should see a login dialog (username: `chrisspeaks`, password: `Cris0037`)
- After successful login, the Hermes dashboard loads
- The embedded TUI tab should be accessible

Test with curl:
```bash
curl -k -u chrisspeaks:Cris0037 -s https://dashboard.terrybot.top/api/status | python3 -m json.tool
```

---

## Maintenance

| Task | Command |
|------|---------|
| Restart dashboard | `sudo systemctl restart hermes-dashboard.service` |
| View logs | `journalctl -u hermes-dashboard -f` |
| Update password | `sudo htpasswd -b /etc/nginx/.htpasswd chrisspeaks <newpassword>` |
| Reload Nginx | `sudo systemctl reload nginx` |
| Check cert renewal | `sudo certbot renew --dry-run` |
| Enable after reboot | `sudo systemctl enable hermes-dashboard.service` |

---

## Pitfalls & Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| **"Invalid Host header"** | Two `Host` headers sent to backend | Use only `proxy_set_header Host 127.0.0.1:9119;` (single header) — remove any duplicate `$host` header |
| **502 Bad Gateway** | Dashboard not listening on 127.0.0.1:9119 | `ps aux | grep dashboard` to verify; `sudo systemctl restart hermes-dashboard.service` |
| **Repeated login prompts** | Authorization header not forwarded | Ensure `proxy_set_header Authorization $http_authorization;` is present in location block |
| **502 after reboot** | Service not enabled | `sudo systemctl enable --now hermes-dashboard.service` |
| **Certificate mismatch** | Self-signed cert instead of Let's Encrypt | Run Certbot or verify site config points to `/etc/letsencrypt/live/<domain>/...` |
| **Port 9119 already in use** | Conflicting process | `ss -tlnp | grep 9119` then kill or change port |
| **TUI not accessible** | `--tui` flag missing from ExecStart | Add `--tui` to the service's `ExecStart` line and `sudo systemctl daemon-reload && systemctl restart hermes-dashboard` |

---

## References
- Nginx proxy module: <https://nginx.org/en/docs/http/ngx_http_proxy_module.html>
- Certbot Nginx plugin: <https://certbot.eff.org/instructions>
- Systemd service manual: <https://www.freedesktop.org/software/systemd/man/systemd.service.html>