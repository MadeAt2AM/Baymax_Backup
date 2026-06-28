# Nginx Reverse Proxy for Remotion Studio

Use this when port 3000 is blocked by the cloud firewall and you need to expose Remotion Studio via HTTPS on a public URL.

## Prerequisites

- Nginx installed
- Domain pointing to this host (or use the host IP with HTTP)
- SSL cert (Let's Encrypt recommended)

## Basic HTTP proxy (no domain, just host IP)

```nginx
server {
    listen 80;
    server_name <host-ip>;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## HTTPS with Let's Encrypt (domain required)

```nginx
server {
    listen 443 ssl;
    server_name remotion.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Steps to apply

1. Write the config to `/etc/nginx/sites-available/remotion`
2. Symlink: `ln -s /etc/nginx/sites-available/remotion /etc/nginx/sites-enabled/`
3. Test: `nginx -t`
4. Reload: `nginx -s reload`
5. Give the user `https://remotion.yourdomain.com` (or `https://<host-ip>` if using IP with valid cert)

## Remotion Studio as a background process

Remotion Studio must keep running for the link to stay live. Start it with:

```bash
cd /root/my-video && CHROME_BIN=/snap/bin/chromium nohup npx remotion studio > /root/.hermes/logs/remotion-studio.log 2>&1 &
echo $! > /root/.hermes/logs/remotion-studio.pid
```

Check if running:
```bash
ss -tlnp | grep 3000
```
