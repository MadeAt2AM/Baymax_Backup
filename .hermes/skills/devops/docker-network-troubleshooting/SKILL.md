---
name: docker-network-troubleshooting
description: "Diagnose and fix Docker network MTU mismatches, SMTP/TLS handshake failures, and container-to-container connectivity issues"
category: devops
tags: [docker, networking, mtu, smtp, tls, postgresql, troubleshooting]
---

# Docker Network MTU & Connectivity Troubleshooting

## The Core Lesson

**Docker's default bridge network uses MTU 1500. If your host interface (eth0, ens3, etc.) has MTU < 1500 (common on cloud VPS: 1400, 1450, 1460), TLS handshakes and large packets will silently fragment and drop.**

# Docker Network MTU & Connectivity Troubleshooting

## The Core Lesson

**Docker's default bridge network uses MTU 1500. If your host interface (eth0, ens3, etc.) has MTU < 1500 (common on cloud VPS: 1400, 1450, 1460), TLS handshakes and large packets will silently fragment and drop.**

This manifests as:
- SMTP `STARTTLS` hanging after `220 Ready` (TLS ClientHello > 1500 bytes fragments)
- PostgreSQL connections timing out (`EAI_AGAIN`, connection refused)
- HTTPS API calls timing out intermittently
- `apt update` / `npm install` hanging inside containers

## Root Cause Checklist — Check These FIRST

### 1. Host MTU
```bash
ip link show eth0 | grep mtu
# or
cat /sys/class/net/eth0/mtu
```
**Expected:** Match this value in Docker network.

### 2. Docker Network MTU
```bash
docker network inspect <network_name> | grep -i mtu
```
**Must match host MTU exactly.**

### 3. Container Interface MTU
```bash
docker exec <container> ip link show eth0 | grep mtu
```
**Must match host MTU.**

### 4. Services on Correct Network
```bash
docker network inspect <network_name> | jq '.[0].Containers'
```
**Every container that talks to each other MUST be on the same custom network.** Default `bridge` network is isolated from custom networks.

## The Fix Pattern

```yaml
# docker-compose.yml
networks:
  app-net:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: "1400"  # MATCH HOST MTU

services:
  app:
    networks: [app-net]
    env_file: .env  # CRITICAL: was missing - load env vars
  db:
    networks: [app-net]  # CRITICAL: db must be on same network
    env_file: .env
```

Then:
```bash
docker compose down
docker network rm <project>_app-net  # Force recreate with new MTU
docker compose up -d
```

## Docker Image Cache Pitfall — CRITICAL

**Problem:** `docker compose build` with cached layers can serve stale code even after source changes.

**Symptoms:**
- Code changes (e.g., logout cookie fix) appear in local build but not in running container
- `docker exec <app> cat /app/dist/routes/auth.js` shows old code
- `--no-cache` sometimes still uses cached intermediate layers

**Fix Pattern:**
```bash
# 1. Full clean rebuild
docker compose build --no-cache --pull app

# 2. Verify artifact BEFORE restart
docker exec <app> cat /app/dist/routes/auth.js | grep -A 10 "logout"

# 3. Only then restart
docker compose up -d --force-recreate app
```

**Root cause:** Docker layer caching skips `COPY server/ ./` if file timestamps/metadata appear unchanged, or intermediate builder stages are reused. Always verify the built artifact inside the container before declaring deploy done.

## SMTP-Specific Debugging Order

When `nodemailer` / `sendmail` / `postfix` hangs on `STARTTLS`:

| Step | Command | What It Tells You |
|------|---------|-------------------|
| 1. TCP reachability | `nc -zv <host> 587` | Port open? Firewall? |
| 2. TLS handshake | `openssl s_client -starttls smtp -connect <host>:587 -servername <host>` | Hangs at `CONNECTED`? → **MTU issue** |
| 3. From container | `docker exec <app> nc -zv <host> 587` | Container egress works? |
| 4. From container TLS | `docker exec <app> openssl s_client ...` | Confirms MTU inside container |
| 5. Check MTU | `docker exec <app> ip link show eth0` | Container MTU ≠ Host MTU? |

**If Step 2 or 4 hangs after `CONNECTED(00000003)` → MTU mismatch. Full stop.**

### New Lesson: External Reverse Proxy Chain (Critical)

In this deployment, the reverse proxy chain was:
```
Client → External Caddy (control VPS / Cloudflare) → Nginx (dev VPS :80/443) → payntra-app container (:3000)
```

**The external Caddy was stripping `Domain=payntra.terrybot.top` from `Set-Cookie` headers**, causing logout to fail on public URL while working locally.

**Debugging steps for proxy chain issues:**
1. `curl -I https://app.domain.com` → check `via:` header (shows proxy software)
2. Test cookie end-to-end: `curl -X POST https://app.domain.com/api/auth/logout -v` → verify `Set-Cookie` includes `Domain=`
3. If `via: 1.1 Caddy` appears but you don't run Caddy locally → external proxy exists
4. Configure external proxy to pass `Set-Cookie` unchanged (Caddy: `header_down -Set-Cookie` or Nginx: `proxy_pass_header Set-Cookie`)

## PostgreSQL-Specific Debugging

When app logs show `EAI_AGAIN db` or `connection refused`:

| Check | Command |
|-------|---------|
| Same network? | `docker network inspect <net> \| jq '.[0].Containers'` — both containers listed? |
| DNS resolution | `docker exec <app> getent hosts db` — returns IP? |
| Port reachable | `docker exec <app> nc -zv db 5432` |
| PG env vars | `docker exec <app> env \| grep -i postgres` — correct host/port? |

## Docker Image Cache Pitfall — CRITICAL

**Problem:** `docker compose build` with cached layers can serve stale code even after source changes.

**Symptoms:**
- Code changes (e.g., logout cookie fix) appear in local build but not in running container
- `docker exec <app> cat /app/dist/routes/auth.js` shows old code
- `--no-cache` sometimes still uses cached intermediate layers

**Fix Pattern:**
```bash
# 1. Full clean rebuild
docker compose build --no-cache --pull app

# 2. Verify artifact BEFORE restart
docker exec <app> cat /app/dist/routes/auth.js | grep -A 10 "logout"

# 3. Only then restart
docker compose up -d --force-recreate app
```

**Root cause:** Docker layer caching skips `COPY server/ ./` if file timestamps/metadata appear unchanged, or intermediate builder stages are reused. Always verify the built artifact inside the container before declaring deploy done.

## New Lesson: External Reverse Proxy Chain (Critical)

In this deployment, the reverse proxy chain was:
```
Client → External Caddy (control VPS / Cloudflare) → Nginx (dev VPS :80/443) → payntra-app container (:3000)
```

**The external Caddy was stripping `Domain=payntra.terrybot.top` from `Set-Cookie` headers**, causing logout to fail on public URL while working locally.

**Debugging steps for proxy chain issues:**
1. `curl -I https://app.domain.com` → check `via:` header (shows proxy software)
2. Test cookie end-to-end: `curl -X POST https://app.domain.com/api/auth/logout -v` → verify `Set-Cookie` includes `Domain=`
3. If `via: 1.1 Caddy` appears but you don't run Caddy locally → external proxy exists
4. Configure external proxy to pass `Set-Cookie` unchanged (Caddy: `header_down -Set-Cookie` or Nginx: `proxy_pass_header Set-Cookie`)

## Prevention Checklist (Add to Every New Project)

- [ ] **Before first `docker compose up`:** Run `ip link show eth0` on host, note MTU
- [ ] **In `docker-compose.yml`:** Define custom network with `driver_opts: com.docker.network.driver.mtu: "<HOST_MTU>"`
- [ ] **Every service:** Explicitly declare `networks: [custom-net]` — no implicit default network
- [ ] **CI/CD gate:** Add a smoke test that hits an external TLS endpoint (SMTP, HTTPS API) from inside the app container
- [ ] **Document:** Record host MTU in project README / PROJECT_INDEX.md
- [ ] **Verify built container artifact** — See Docker Image Cache Pitfall above

## Related Skills
- `deployment-checklist` — add MTU verification to pre-deploy gates
- `deployment-checklist` — add Docker image verification step
- `deployment-checklist` — add Fastify cookie domain requirement
- `postgresql-operations` — cross-reference container networking prerequisites

## PostgreSQL-Specific Debugging

When app logs show `EAI_AGAIN db` or `connection refused`:

| Check | Command |
|-------|---------|
| Same network? | `docker network inspect <net> \| jq '.[0].Containers'` — both containers listed? |
| DNS resolution | `docker exec <app> getent hosts db` — returns IP? |
| Port reachable | `docker exec <app> nc -zv db 5432` |
| PG env vars | `docker exec <app> env \| grep -i postgres` — correct host/port? |

## Docker Image Cache Pitfall — CRITICAL

**Problem:** `docker compose build` with cached layers can serve stale code even after source changes.

**Symptoms:**
- Code changes (e.g., logout cookie fix) appear in local build but not in running container
- `docker exec <app> cat /app/dist/routes/auth.js` shows old code
- `--no-cache` sometimes still uses cached intermediate layers

**Fix Pattern:**
```bash
# 1. Full clean rebuild
docker compose build --no-cache --pull app

# 2. Verify artifact BEFORE restart
docker exec <app> cat /app/dist/routes/auth.js | grep -A 10 "logout"

# 3. Only then restart
docker compose up -d --force-recreate app
```

**Root cause:** Docker layer caching skips `COPY server/ ./` if file timestamps/metadata appear unchanged, or intermediate builder stages are reused. Always verify the built artifact inside the container before declaring deploy done.

## New Lesson: External Reverse Proxy Chain (Critical)

In this deployment, the reverse proxy chain was:
```
Client → External Caddy (control VPS / Cloudflare) → Nginx (dev VPS :80/443) → payntra-app container (:3000)
```

**The external Caddy was stripping `Domain=payntra.terrybot.top` from `Set-Cookie` headers**, causing logout to fail on public URL while working locally.

**Debugging steps for proxy chain issues:**
1. `curl -I https://app.domain.com` → check `via:` header (shows proxy software)
2. Test cookie end-to-end: `curl -X POST https://app.domain.com/api/auth/logout -v` → verify `Set-Cookie` includes `Domain=`
3. If `via: 1.1 Caddy` appears but you don't run Caddy locally → external proxy exists
4. Configure external proxy to pass `Set-Cookie` unchanged (Caddy: `header_down -Set-Cookie` or Nginx: `proxy_pass_header Set-Cookie`)

## Prevention Checklist (Add to Every New Project)

- [ ] **Before first `docker compose up`:** Run `ip link show eth0` on host, note MTU
- [ ] **In `docker-compose.yml`:** Define custom network with `driver_opts: com.docker.network.driver.mtu: "<HOST_MTU>"`
- [ ] **Every service:** Explicitly declare `networks: [custom-net]` — no implicit default network
- [ ] **CI/CD gate:** Add a smoke test that hits an external TLS endpoint (SMTP, HTTPS API) from inside the app container
- [ ] **Document:** Record host MTU in project README / PROJECT_INDEX.md
- [ ] **Verify built container artifact** — See Docker Image Cache Pitfall above

## Related Skills
- `deployment-checklist` — add MTU verification to pre-deploy gates
- `deployment-checklist` — add Docker image verification step
- `deployment-checklist` — add Fastify cookie domain requirement
- `postgresql-operations` — cross-reference container networking prerequisites
# 1. Full clean rebuild
docker compose build --no-cache --pull app

# 2. Verify artifact BEFORE restart
docker exec <app> cat /app/dist/routes/auth.js | grep -A 10 "logout"

# 3. Only then restart
docker compose up -d --force-recreate app
```

**Root cause:** Docker layer caching skips `COPY server/ ./` if file timestamps/metadata appear unchanged, or intermediate builder stages are reused. Always verify the built artifact inside the container before declaring deploy done.

## Docker Image Cache Pitfall — CRITICAL

**Problem:** `docker compose build` with cached layers can serve stale code even after source changes.

**Symptoms:**
- Code changes (e.g., logout cookie fix) appear in local build but not in running container
- `docker exec <app> cat /app/dist/routes/auth.js` shows old code
- `--no-cache` sometimes still uses cached intermediate layers

**Fix Pattern:**
```bash
# 1. Full clean rebuild
docker compose build --no-cache --pull app

# 2. Verify artifact BEFORE restart
docker exec <app> cat /app/dist/routes/auth.js | grep -A 10 "logout"

# 3. Only then restart
docker compose up -d --force-recreate app
```

**Root cause:** Docker layer caching skips `COPY server/ ./` if file timestamps/metadata appear unchanged, or intermediate builder stages are reused. Always verify the built artifact inside the container before declaring deploy done.

## New Lesson: External Reverse Proxy Chain (Critical)

In this deployment, the reverse proxy chain was:
```
Client → External Caddy (control VPS / Cloudflare) → Nginx (dev VPS :80/443) → payntra-app container (:3000)
```

**The external Caddy was stripping `Domain=payntra.terrybot.top` from `Set-Cookie` headers**, causing logout to fail on public URL while working locally.

**Debugging steps for proxy chain issues:**
1. `curl -I https://app.domain.com` → check `via:` header (shows proxy software)
2. Test cookie end-to-end: `curl -X POST https://app.domain.com/api/auth/logout -v` → verify `Set-Cookie` includes `Domain=`
3. If `via: 1.1 Caddy` appears but you don't run Caddy locally → external proxy exists
4. Configure external proxy to pass `Set-Cookie` unchanged (Caddy: `header_down -Set-Cookie` or Nginx: `proxy_pass_header Set-Cookie`)

## Prevention Checklist (Add to Every New Project)

- [ ] **Before first `docker compose up`:** Run `ip link show eth0` on host, note MTU
- [ ] **In `docker-compose.yml`:** Define custom network with `driver_opts: com.docker.network.driver.mtu: "<HOST_MTU>"`
- [ ] **Every service:** Explicitly declare `networks: [custom-net]` — no implicit default network
- [ ] **CI/CD gate:** Add a smoke test that hits an external TLS endpoint (SMTP, HTTPS API) from inside the app container
- [ ] **Document:** Record host MTU in project README / PROJECT_INDEX.md
- [ ] **Verify built container artifact** — See Docker Image Cache Pitfall above

## Related Skills
- `deployment-checklist` — add MTU verification to pre-deploy gates
- `postgresql-operations` — cross-reference container networking prerequisites