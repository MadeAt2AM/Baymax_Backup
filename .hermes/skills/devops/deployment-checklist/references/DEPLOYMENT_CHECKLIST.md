# Deployment Checklist — Payntra (Template)

## Pre-Deploy Checks

### 1. Code & Tests
- [ ] All server unit tests pass (`cd server && npm test`)
- [ ] All client unit tests pass (`cd client && npm test`)
- [ ] Playwright e2e tests pass against staging (`npx playwright test`)
- [ ] TypeScript typecheck passes (`npm run typecheck` in both server/client)
- [ ] No `any` types introduced (grep for `any` in new code)
- [ ] ESLint/Prettier clean

### 2. Docker & Build
- [ ] `docker compose build` succeeds locally
- [ ] Multi-stage Dockerfile builds correctly (builder → runner)
- [ ] No `node_modules` in final image (check `docker history`)
- [ ] Build args/secrets not leaked in image layers

### 3. Network & MTU (CRITICAL — Past Incident)
- [ ] Host eth0 MTU known: `ip link show eth0 | grep mtu`
- [ ] Docker network MTU matches host: `docker network inspect <net> | grep mtu`
- [ ] Container eth0 MTU matches: `docker exec <app> ip link show eth0`
- [ ] SMTP TLS handshake works from container: `docker exec <app> openssl s_client -starttls smtp -connect mail.cyberslide.net:587`

### 4. Secrets & Config
- [ ] `.env` present on VPS with all required vars:
  - `JWT_SECRET` (32+ chars, base64)
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`
  - `DATABASE_URL` (postgres://user:pass@db:5432/payntra)
  - `COOKIE_DOMAIN=payntra.terrybot.top`
  - `NODE_ENV=production`
- [ ] No secrets in git history (check `git log --all --oneline --grep=secret`)
- [ ] Caddyfile has correct domain: `payntra.terrybot.top`

### 5. Database
- [ ] Migrations applied: `docker exec payntra-db psql -U payntra -d payntra -f /migrations/up.sql`
- [ ] Schema matches Prisma/SQL files (no drift)
- [ ] Backup taken before deploy: `pg_dump -U payntra payntra > backup_$(date +%F).sql`

## Deploy Execution

### GitHub Webhook Flow
1. [ ] Push to `main` branch
2. [ ] GitHub webhook fires to `http://147.79.18.32:9000/webhook`
3. [ ] Webhook runs `project_dev.sh redeploy` on VPS
4. [ ] Docker pulls new image, rebuilds, restarts
4. [ ] Caddy reloads (auto via config watch or manual `docker exec caddy caddy reload`)

### Manual Fallback
```bash
ssh root@147.79.18.32
cd /root/projects/payntra
git pull origin main
./project_dev.sh redeploy
```

## Post-Deploy Smoke Tests (Run in Order)

### 1. Infrastructure
- [ ] `docker ps` — all containers healthy (app, db, caddy)
- [ ] `docker logs payntra-app --tail 50` — no ERROR/panic
- [ ] `docker exec payntra-db pg_isready` — accepting connections

### 2. Network & SMTP (CRITICAL)
- [ ] `./scripts/verify-network.sh payntra-net`
- [ ] All checks pass (MTU match, SMTP TLS, DB connectivity)

### 3. Application Endpoints
- [ ] `curl -fsS https://payntra.terrybot.top/health` → 200 OK
- [ ] `curl -fsS https://payntra.terrybot.top/login` → HTML loads
- [ ] `curl -fsS https://payntra.terrybot.top/forgot-password` → HTML loads

### 4. Auth Flow
- [ ] Sign up new account → email received → verify link works
- [ ] Sign in → cookie set (HTTPOnly, Secure, SameSite=Lax, domain=payntra.terrybot.top)
- [ ] Forgot password → reset email received → link works → new password works

### 5. Core Feature: Ledger
- [ ] Create ledger for current month → auto-rollover from templates
- [ ] Add custom item → appears in table
- [ ] Toggle PAID/PENDING → optimistic UI update → persists after refresh
- [ ] Add note → persists after refresh
- [ ] Delete item → 204 → removed from list → 404 on second delete
- [ ] Switch months → data isolated per month

### 6. Settings / Profile
- [ ] Change email → verification email sent
- [ ] Change password → old password required → new password works
- [ ] Logout → cookie cleared → redirect to login

### 7. Responsive Layout
- [ ] Mobile (375px): stacked cards, hamburger nav
- [ ] Tablet (768px): sidebar collapsible
- [ ] Desktop (1440px): high-density table, sticky headers
- [ ] Dark/light theme toggle persists

## Rollback Procedure

If smoke tests fail:
```bash
ssh root@147.79.18.32
cd /root/projects/payntra
git log --oneline -5  # find last good commit
git revert HEAD       # or git reset --hard <good-sha>
./project_dev.sh redeploy
# OR: docker tag payntra-app:latest payntra-app:broken && docker tag payntra-app:<good-sha> payntra-app:latest && docker compose up -d
```

## Post-Deploy Documentation
- [ ] Update `PROJECT_INDEX.md` with new version/deploy date
- [ ] Note any config changes in `CHANGELOG.md`
- [ ] If MTU/network changed: document in `NETWORK_TROUBLESHOOTING.md`

## Contacts
- **VPS**: root@147.79.18.32 (Hetzner, Helsinki)
- **DNS**: terrybot.top → Cloudflare (payntra.terrybot.top A → 147.79.18.32)
- **SMTP**: mail.cyberslide.net:587 (STARTTLS, support@madeat2am.in)
- **Caddy**: Auto-TLS via Let's Encrypt
- **Monitoring**: `docker stats`, `journalctl -u docker`, Caddy access logs