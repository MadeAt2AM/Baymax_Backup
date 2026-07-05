---
name: deployment-checklist
description: "Pre-deployment and post-deployment verification checklist for web applications — covers networking, secrets, migrations, smoke tests, and rollback"
category: devops
tags: [deployment, checklist, ci-cd, verification, smoke-test, rollback]
---

# Deployment Checklist — Web Applications

## Pre-Deploy (Before Any `docker compose up` / Push)

### Infrastructure & Networking
- [ ] **Host MTU recorded** — `ip link show eth0 | grep mtu` → documented in PROJECT_INDEX.md
- [ ] **Docker network MTU matches host** — `driver_opts: com.docker.network.driver.mtu: "<HOST_MTU>"` in compose
- [ ] **All services on explicit custom network** — no service uses implicit `default` bridge
- [ ] **Database service on same network as app** — verified in compose file
- [ ] **External dependencies reachable** — SMTP host, payment gateway, object storage, etc. resolvable from host

### Secrets & Configuration
- [ ] **`.env` file exists and complete** — no placeholder values
- [ ] **`env_file: .env` declared on EVERY service** that needs it (app, worker, scheduler, db migrations)
- [ ] **No secrets in compose file** — only `${VAR}` references
- [ ] **JWT secret ≥ 32 bytes** — generated via `openssl rand -hex 32`
- [ ] **Database password ≠ default** — rotated from `postgres` / `password`

### Docker Image Integrity (NEW - Critical Lesson)
- [ ] **Verify built artifact before restart** — After `docker compose build`, run:
  ```bash
  docker exec <app> cat /app/dist/routes/auth.js | grep -A 10 "logout"
  ```
  Confirm cookie fix (or other changes) is present in the image
- [ ] **Use `--no-cache --pull` for deploys** — `docker compose build --no-cache --pull app`
- [ ] **Force recreate service** — `docker compose up -d --force-recreate app` after build
- [ ] **Never trust cached layers** — Always verify the built container contains your changes

### Reverse Proxy / Caddy Configuration (NEW - Critical Lesson)
- [ ] **Identify reverse proxy** — Is it Caddy, Nginx, Traefik? Running as container or host service?
- [ ] **Proxy preserves `Set-Cookie` headers** — Default Caddy/Nginx may strip or modify cookie attributes
- [ ] **Cookie domain matches** — If backend sets `Domain=payntra.terrybot.top`, proxy must not override
- [ ] **Test cookie clearing end-to-end** — `curl -X POST https://app.domain.com/api/auth/logout -v` must show `Domain=payntra.terrybot.top` in response
- [ ] **HTTPS termination at proxy** — Backend sees HTTP, proxy handles TLS (affects `secure` cookie flag)
- [ ] **External proxy chain documented** — See `references/EXTERNAL_PROXY_CHAIN.md` for Payntra architecture

### Database & Migrations
- [ ] **Migration script versioned** — `migrations/001_initial.sql`, `002_add_x.sql`, etc.
- [ ] **Migration runs in CI / predeploy step** — not on app startup (race condition risk)
- [ ] **Rollback script exists** for each migration (or `DOWN` SQL)
- [ ] **Backup taken before deploy** — `pg_dump` / volume snapshot

### Build & Image
- [ ] **Multi-stage Dockerfile** — build stage separate from runtime
- [ ] **Non-root user in final image** — `USER node` / `USER app`
- [ ] **Healthcheck defined** — `HEALTHCHECK CMD curl -f http://localhost:3000/health || exit 1`
- [ ] **Image tagged with git SHA** — `myapp:git-<sha>` + `myapp:latest`

### Docker Image Integrity (NEW - Critical Lesson)
- [ ] **Verify built artifact before restart** — After `docker compose build`, run:
  ```bash
  docker exec <app> cat /app/dist/routes/auth.js | grep -A 10 "logout"
  ```
  Confirm cookie fix (or other changes) is present in the image
- [ ] **Use `--no-cache --pull` for deploys** — `docker compose build --no-cache --pull app`
- [ ] **Force recreate service** — `docker compose up -d --force-recreate app` after build
- [ ] **Never trust cached layers** — Always verify the built container contains your changes

---

## Post-Deploy Smoke Tests (Run Immediately After Deploy)

### 1. Health & Connectivity
```bash
# App health
curl -f https://app.domain.com/health

# DB connectivity from app
docker exec <app> pg_isready -h db -U $POSTGRES_USER

### 4. Auth Flow
- [ ] Sign up new account → email received → verify link works
- [ ] Sign in → cookie set (HTTPOnly, Secure, SameSite=Lax, domain=payntra.terrybot.top)
- [ ] Forgot password → reset email received → link works → new password works

### 5. Cookie Security (NEW - Critical Lesson)
- [ ] **Logout clears cookie with domain** — Direct container test:
  ```bash
  docker exec payntra-app node -e "
  const Fastify = require('fastify');
  const cookie = require('@fastify/cookie');
  const app = Fastify();
  app.register(cookie, {});
  app.ready().then(() => {
    const opts = { httpOnly: true, secure: true, sameSite: 'lax', domain: 'payntra.terrybot.top', path: '/', maxAge: 2592000 };
    app.setCookie('payntra_token', 'test', opts);
    app.clearCookie('payntra_token', { 
      path: '/', 
      domain: 'payntra.terrybot.top', 
      secure: true, 
      sameSite: 'lax' 
    });
  });
  ```
  Should show clearCookie with domain attribute
- [ ] **Logout via API** — `curl -X POST https://payntra.terrybot.top/api/auth/logout -v` includes `Domain=payntra.terrybot.top` in Set-Cookie header
- [ ] **After logout, reload does NOT restore session** — Confirms cookie fully cleared

### 6. Critical User Flows (Automated or Manual)
- [ ] **Logout clears cookie with domain** — Direct container test:
  ```bash
  docker exec payntra-app node -e "
  const Fastify = require('fastify');
  const cookie = require('@fastify/cookie');
  const app = Fastify();
  app.register(cookie, {});
  app.ready().then(() => {
    const opts = { httpOnly: true, secure: true, sameSite: 'lax', domain: 'payntra.terrybot.top', path: '/', maxAge: 2592000 };
    app.setCookie('payntra_token', 'test', opts);
    app.clearCookie('payntra_token', { 
      path: '/', 
      domain: 'payntra.terrybot.top', 
      secure: true, 
      sameSite: 'lax' 
    });
  });
  ```
  Should show clearCookie with domain attribute
- [ ] **Logout via API** — `curl -X POST https://payntra.terrybot.top/api/auth/logout -v` includes `Domain=payntra.terrybot.top` in Set-Cookie header
- [ ] **After logout, reload does NOT restore session** — Confirms cookie fully cleared

### 6. Critical User Flows (Automated or Manual)
- [ ] **Auth flow:** Register → verify email → login → access protected route
- [ ] **Password reset:** Request → receive email → click link → set new password → login
- [ ] **Core CRUD:** Create → Read → Update → Delete on primary entity
- [ ] **File upload** (if applicable) → S3 / local storage → serve back

### 3. Observability
- [ ] **Logs streaming** — `docker logs -f app` shows no ERROR/CRITICAL
- [ ] **Metrics endpoint** — `/metrics` returns Prometheus format (if applicable)
- [ ] **Alerting test** — fire a test alert (disk, CPU, error rate) → reaches on-call

---

## Rollback Procedure (Documented Per Project)

```bash
# 1. Tag current broken image
docker tag myapp:latest myapp:broken-<timestamp>

# 2. Deploy previous known-good tag
docker tag myapp:git-<previous-sha> myapp:latest
docker compose up -d --force-recreate app

# 3. Run smoke tests
# 4. If DB migration ran: execute DOWN migration
# 5. Post-mortem within 24h
```

## Common Framework Pitfalls

### Fastify Cookie `clearCookie` Domain Requirement
When using HTTPOnly cookies with explicit `domain` set (e.g., `payntra.terrybot.top`), `reply.clearCookie()` **must include the same domain, secure, and sameSite options** or the browser will not delete the cookie.

```typescript
// WRONG - cookie persists after logout
reply.clearCookie(COOKIE_NAME, { path: cookieOpts.path });

// CORRECT - matches setCookie options exactly
reply.clearCookie(COOKIE_NAME, {
  path: cookieOpts.path,
  domain: cookieOpts.domain,
  secure: cookieOpts.secure,
  sameSite: cookieOpts.sameSite,
});
```

This caused logout to appear to work (redirect to login) but session persisted on reload.

---

## Project Index Entry (Add to PROJECT_INDEX.md)

```markdown
## Deployment Metadata
- **Host MTU:** 1400
- **Docker Network:** payntra-net (MTU 1400)
- **SMTP:** mail.cyberslide.net:587 STARTTLS
- **DB:** postgres:16 on payntra-net
- **Healthcheck:** GET /health
- **Rollback Tag:** payntra:git-<last-known-good-sha>
```