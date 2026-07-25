# Port Conflicts & Image Transfer on the Dev VPS

When deploying a new app to the dev VPS, two recurring problems waste time:
(1) a stale process or container holds port 80/443, blocking Caddy from
starting, and (2) building a large image on the dev VPS over a throttled
SSH link takes 10+ minutes when it took 3 minutes locally.

## 1. Port conflict resolution

### Diagnose before acting
```bash
# What's on 80/443?
ss -tlnp | grep -E ':80|:443'
# Example output:
# LISTEN 0  511  0.0.0.0:80  0.0.0.0:*  users:(("nginx",pid=278744,fd=5))
# LISTEN 0  511  0.0.0.0:443 0.0.0.0:*  users:(("nginx",pid=278744,fd=7))

# Which containers expose those ports?
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E '80|443'
```

### Common culprits
- **Stale nginx** — left over from a previous deploy or a different project.
  ```bash
  sudo pkill -9 nginx
  ```
- **Old Caddy container** — a standalone `caddy` container (not managed by
  the project's compose) that was started manually.
  ```bash
  docker rm -f caddy
  ```
- **Project web container exposing 80/443** — the web Dockerfile uses Caddy
  which listens on 80/443 internally. If the compose `ports:` maps those
  to the host, they conflict with the host-level Caddy. Fix: only map
  `127.0.0.1:8080:8080` (the web container's Caddyfile listens on :8080
  only), and let the host-level Caddy reverse-proxy to it.

### Restart Caddy after clearing the port
```bash
sudo systemctl restart caddy
sudo systemctl status caddy --no-pager  # should show "active (running)"
```

## 2. Docker image transfer (avoid slow builds on the dev VPS)

When the dev VPS SSH link is throttled (common on Hetzner + Hermes host
bridge), building a 2 GB image with `apt-get` + `pip install` can take
10+ minutes. Instead, build locally and transfer the image as a tarball.

### Build locally
```bash
# On the Hermes host
docker build -f apps/api/Dockerfile -t competitors-api:0.1.0 .
docker build -f apps/web/Dockerfile -t competitors-web:0.1.0 .
```

### Save as tarballs
```bash
docker save competitors-api:0.1.0 > /tmp/competitors-api.tar
docker save competitors-web:0.1.0 > /tmp/competitors-web.tar
```

### Transfer via rsync (faster than scp for large files)
```bash
rsync -a /tmp/competitors-api.tar dev-vps:/tmp/competitors-api.tar
rsync -a /tmp/competitors-web.tar dev-vps:/tmp/competitors-web.tar
```

### Load on the dev VPS
```bash
ssh dev-vps 'docker load -i /tmp/competitors-api.tar'
ssh dev-vps 'docker load -i /tmp/competitors-web.tar'
```

### Tag and use
```bash
ssh dev-vps 'docker tag competitors-api:test competitors-api:0.1.0'
ssh dev-vps 'docker tag competitors-web:test competitors-web:0.1.0'
# Update docker-compose.yml to use image: competitors-api:0.1.0
# (add image: directive so compose doesn't try to rebuild)
```

### When to use this pattern
- Image is >500 MB (API images with ML deps are typically 1.5–2 GB)
- Dev VPS SSH link is throttled (<1 MB/s)
- The Dockerfile has no remote build cache configured
- You've already verified the build works locally

## 3. DNS propagation timing

Cloudflare A-records typically propagate within 10–30 seconds, but the
first HTTPS request after creation may return a 525 (SSL handshake failed)
because Caddy hasn't issued the ACME cert yet. The cert is issued on first
hit and becomes valid within ~30 seconds. Retry with a sleep loop:

```bash
# Wait for HTTPS to be ready after creating a DNS record
for i in $(seq 1 10); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 https://competitors.terrybot.top/api/healthz 2>/dev/null)
  if [ "$CODE" = "200" ]; then
    echo "HTTPS ready after ${i} attempts"
    break
  fi
  echo "Attempt $i: HTTP $CODE — retrying..."
  sleep 5
done
```