---
name: deploy-app-to-dev-vps
description: "Deploy a new (or replacement) app to the dev VPS at 147.79.18.32 behind the existing Caddy reverse proxy. Covers the full lifecycle: source preparation, mirror to MadeAt2AM org, teardown, first-pull, schema migration, seed data, comprehensive validation, webhook auto-redeploy, and live verification. SYNTRA v1 + v2 (Jul 2026) are the worked examples."
---

# Deploy an app to the dev VPS (147.79.18.32)

The dev VPS hosts Payntra, SYNTRA, baymax-pipeline-probe behind a single Caddy
container. Each app gets its own subdomain (`<name>.terrybot.top`), its own
Docker compose stack, and its own webhook route. This skill is the playbook for
adding a new app or replacing an existing one.

## The infrastructure (do not recreate — reuse)

| Component | Path on host | Purpose |
|---|---|---|
| Caddy container | `caddy` (docker) | Reverse proxy; reloads on `/etc/caddy/sites/*.caddy` changes via bind mount from host `/srv/caddy/sites` |
| Caddy vhost files | `/srv/caddy/sites/<name>.caddy` | One file per project; auto-imported by `Caddyfile` glob |
| Project directory | `/srv/projects/<name>/` | Cloned repo + live docker-compose |
| Secret env file | `/srv/secrets/<name>.env` | Materialized into `/srv/projects/<name>/.env` on first deploy only — manual edits to `/srv/projects/<name>/.env` survive redeploys |
| Webhook receiver | `/etc/webhook/hooks.json` (`github-push-<name>` entry) | Receives GitHub push events on port 9000, runs `syntra_dev.sh redeploy` |
| Deploy helper | `/srv/scripts/syntra_dev.sh` | Reads `GH_TOKEN` from `/srv/scripts/.gh-token`, runs `docker compose up -d --build`, writes caddy block, reloads Caddy |
| CF DNS env | `/srv/scripts/.cf-env` | Cloudflare API token + zone ID, sourced by deploy helper for idempotent DNS |
| Network | external `web` (Docker bridge) | Shared with Caddy. Has Caddy + payntra-app + baymax-pipeline-probe-app already attached |
| Private DB network | `<name>_<name>-net` (e.g. `syntra_syntra-net`) | MTU 1400 to match Hetzner eth0; carries DB traffic only |

DO NOT:
- Modify `/srv/scripts/project_dev.sh` for a new project — it's used by payntra/probe. Add a project-specific deploy helper like `syntra_dev.sh` instead.
- Bounce the Caddy container for config changes — use `docker exec caddy caddy reload`.
- Touch the `web` network's bridge MTU — it's already 1400 via `/etc/docker/daemon.json`.

## Step-by-step: deploy a new app

### 1. Decide repo topology

Two options:
- **A. Mirror to MadeAt2AM**: clone from chrisvincodes/* (or any account), push
  to `MadeAt2AM/<name>_VPS`. Lets the existing webhook infrastructure
  (`github-push-<name>` matches `repository.name == "<name>_VPS"`) keep
  working without changes. **Preferred when source lives outside MadeAt2AM.**
- **B. Direct deploy**: webhook entry matches the repo name directly. Less
  indirection but a new repo entry per project.

For Chris's workflow, **always use Option A** — he prefers the MadeAt2AM
mirror pattern. See `references/chris-deploy-workflow.md`.

### 2. Compose file adaptations

Source repos are usually Replit-targeted (Alpine + rollup-musl exclusion).
Switch base images to Debian-slim:

```dockerfile
# deploy/docker/Dockerfile.api  (and Dockerfile.web, Dockerfile.migrate)
FROM node:20-bookworm-slim AS builder
# ... pnpm install, build ...
FROM node:20-bookworm-slim AS runner
# bookworm-slim lacks BusyBox tools — install wget for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends wget ca-certificates && rm -rf /var/lib/apt/lists/*
```

The Alpine-musl exclusion in `pnpm-workspace.yaml` (line `rollup>@rollup/rollup-linux-x64-musl: "-"`)
breaks Vite builds. Use bookworm (glibc) for the entire build chain.

Standard compose topology:
```yaml
services:
  postgres: { networks: [private] }
  api:      { networks: [private, web] }
  web:      { networks: [private, web] }   # web uses shared `web` external net
networks:
  private: { name: <name>_<name>-net, driver_opts: { "com.docker.network.driver.mtu": "1400" } }
  web:     { name: web, external: true }
```

**Critical alias declaration** on the web service (see skill
`caddy-service-dns-aliases`):
```yaml
  web:
    networks:
      web:
        aliases: [<name>-web, <name>-app]
```

### 3. Host-side hooks (new project only)

If Option A: the existing `github-push-syntra` webhook entry already matches
the new repo (e.g. `SYNTRA_VPS`). No changes needed. The deploy script
`/srv/scripts/syntra_dev.sh` already knows the repo name.

For a brand-new project, append to `/etc/webhook/hooks.json`:
```json
{
  "id": "github-push-<name>",
  "execute-command": "/srv/scripts/<name>_dev.sh",
  "pass-arguments-to-command": [{ "source": "string", "name": "redeploy" }],
  "trigger-rule": {
    "and": [
      { "match": { "type": "payload-hmac-sha256", "secret": "<shared-secret>", "parameter": { "source": "header", "name": "X-Hub-Signature-256" } } },
      { "match": { "type": "value", "value": "refs/heads/main", "parameter": { "source": "payload", "name": "ref" } } },
      { "match": { "type": "value", "value": "<repo-name>", "parameter": { "source": "payload", "name": "repository.name" } } }
    ]
  }
}
```
Hot-reload is automatic (`-hotreload` flag on webhook daemon).

### 4. First-pull

```bash
ssh dev-vps 'cd /tmp && GH_TOKEN="$(cat /srv/scripts/.gh-token)" \
  /srv/scripts/run_syntra_deploy.sh first-pull'
# Or directly:
ssh dev-vps 'GH_TOKEN=... /srv/scripts/<name>_dev.sh first-pull'
```

This clones the repo, materializes `/srv/secrets/<name>.env` → `.env`, runs
`docker compose up -d --build`, writes `/srv/caddy/sites/<name>.caddy`,
ensures Cloudflare DNS record, and reloads Caddy.

**Always run the migration step explicitly** after first-pull — `syntra_dev.sh`
brings containers up but does NOT auto-run drizzle-kit push:
```bash
ssh dev-vps 'cd /srv/projects/<name> && docker compose run --rm migrate'
```

### 5. Seed data

Postgres `crypt(pw, gen_salt('bf', 12))` produces `$2a$12$...` hashes that
bcryptjs accepts. See `references/seeding-patterns.md` for full template.

Critical gotchas:
- `companies.name` is NOT unique in this schema → idempotent INSERTs for users
  under a company MUST use `SELECT ... FROM companies WHERE name='X' ORDER BY id LIMIT 1`
- `users.email` IS unique → `ON CONFLICT (email) DO UPDATE` is safe
- After `DELETE` from `users`, the sequence continues forward — user IDs may
  not match a hard-coded test value. Always query `GET /api/users` to get
  live IDs before tests

### 6. Validate

Run `scripts/validate_app.sh` against the live URL (see the script template).
Aim for full pass on every API group: public, auth, platform/admin, white-label
branding, custom-domain verify, team, workplaces, shifts CRUD + suggest,
availability, leave, invitations, presets, **shift offers/swaps/replacements
(v2)**, **notifications**, **iCal** (note: v2 generates client-side, no
server endpoint), **SMTP test**, role-based access denials, public auth
endpoints.

The script uses a `req()` helper that writes body to a side-channel file
because `BODY=` inside `req()` (called via `code=$(req ...)`) runs in a
subshell — see comments in the script template.

### 7. Live verify + webhook end-to-end

```bash
# Live HTTP
curl -sS -o /dev/null -w "root => %{http_code}\n" https://<name>.<domain>/
curl -sS -o /dev/null -w "healthz => %{http_code}\n" https://<name>.<domain>/api/healthz

# Browser smoke test (admin login + dashboard renders)

# Webhook end-to-end: push a no-op commit
cd /root/.hermes/projects/<name>/deploy-mirror
echo "# webhook verify $(date -u)" >> README.md
git add README.md && git commit -m "chore: webhook verify" --no-verify
git push origin main

# Watch the webhook fire
sleep 8
ssh dev-vps 'tail -n 6 /var/log/webhook.log | grep -E "triggered|executing"'
ssh dev-vps 'cat /srv/projects/<name>/.baymax-last-deploy'
```

## Known gotchas (full list)

1. **MTU 1400** — Hetzner eth0 is 1400. Build with daemon.json setting OR
   custom network `driver_opts.mtu: "1400"`. Symptom: `apt-get update` returns
   "Some index files failed to download" mid-build. See skill
   `caddy-service-dns-aliases`.
2. **DNS aliases on shared `web` network** — `syntra-web` does NOT resolve
   unless declared as `networks.web.aliases`. Same skill.
3. **`drizzle-kit push` image is cached** even when source changes — rebuild
   migrate explicitly before running: `docker compose build migrate && docker
   compose run --rm migrate`. Symptom: schema appears stale after
   `drizzle-kit` config or schema changes.
4. **bookworm-slim lacks `wget`** — install in runner stage. Alpine had it
   via BusyBox; Debian-slim doesn't.
5. **Pnpm musl exclusion** in repos targeting Replit — use bookworm-slim
   for VPS, or remove the exclusion. Musl binary is needed for Vite rollup.
6. **Caddy bind-mount** at `/srv/caddy/sites` is HOT — `caddy reload` picks
   up new files without restarting.
7. **ACME cert provisioning** — first hit returns `tlsv1 alert internal
   error` for ~30s while LE issues the cert. Retries succeed.
8. **`companies.name` is not unique** — idempotent user seed must use
   `ORDER BY id LIMIT 1`.
9. **Web container healthcheck shows `unhealthy`** — fix with `127.0.0.1`
   instead of `localhost` (Alpine BusyBox wget resolves `localhost` to
   `::1` (IPv6) first; nginx only listens on `0.0.0.0`). Patch the
   Dockerfile.web healthcheck to `wget -qO- http://127.0.0.1/index.html`.
10. **Pnpm-workspace dep trap (CRITICAL — multi-stage Dockerfile)** — adding
    a runtime npm dep (e.g. `express-rate-limit`) to `artifacts/<svc>/package.json`
    is NOT ENOUGH. You need ALL THREE:
    1. Add to `package.json` `dependencies` (so the build stage resolves it)
    2. Regenerate the root `pnpm-lock.yaml` via `pnpm install
       --no-frozen-lockfile` in the monorepo root — the Dockerfile's
       `pnpm install --frozen-lockfile` will fail without it
    3. Add to the runtime deps stage in the Dockerfile (the small
       `FROM ... AS deps` that runs `npm install --production` from a
       generated minimal package.json) — the build stage uses pnpm to
       pull everything, but the runtime stage only installs the named
       list, so the new dep must be in that list too

    Symptom: webhook rebuild fails with
    `Could not resolve "<pkg>"` from esbuild. Fix: regenerate the lockfile
    + update the runtime deps stage + commit both. See
    `references/security-hardening-patterns.md` for the worked example.
11. **nginx `add_header` does NOT inherit from `server {}` to `location {}`** —
    security headers declared in the outer `server {}` block are dropped
    by every `location {}` block that defines its own headers. For
    reverse-proxied `/api/` routes, re-declare every security header
    inside `location /api/ {}`, otherwise the proxied API responses go
    out without HSTS / X-Frame-Options / CSP.
12. **Wildcard `cors()` is HIGH-severity** — `app.use(cors())` with no
    options allows ANY origin to call the API from a browser. Replace
    with explicit allowlist (see `references/security-hardening-patterns.md`
    for the pattern + `ALLOWED_ORIGINS` env-driven list).
13. **`trust proxy = 1` for rate-limit** — Express sits behind Caddy, so
    `req.ip` is `127.0.0.1` unless you `app.set('trust proxy', 1)`. Without
    it, per-IP rate-limit fails open (everyone shares one bucket) and
    brute-force protection is bypassed.

## Verification checklist before declaring done

- [ ] `https://<name>.<domain>/` returns 200
- [ ] `https://<name>.<domain>/api/healthz` returns `{"status":"ok"}`
- [ ] All seed users can log in and reach their role-appropriate UI
- [ ] `validate_app.sh` returns 0 FAIL
- [ ] Custom-domain (if applicable) round-trip works:
  PUT domain → status:pending → POST verify → status:verified
- [ ] SMTP test endpoint returns 2xx
- [ ] Role-based access denials return 403 (staff can't create workplaces, etc.)
- [ ] GitHub webhook end-to-end: no-op commit → webhook log shows
  "triggered" + "executing" → `.baymax-last-deploy` updates
- [ ] Neighbour projects (payntra, etc.) still return 200 — daemon MTU
  restart or compose recreation shouldn't disturb them
- [ ] Security headers present on every response type (root, /api/*, static):
  `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`,
  `Content-Security-Policy`, `Referrer-Policy`, `Permissions-Policy`.
  See `references/security-hardening-patterns.md` for the curl checks.

## Related

- **Skill: `caddy-service-dns-aliases`** — deep-dive on the DNS-alias + MTU
  + Caddy bind-mount mechanics. Read this before debugging 502s or build
  failures.
- **Skill: `security-hardening-web-stack`** — class-level skill covering
  the three-layer security-header pattern, CORS allowlist, rate-limit,
  body-size cap, and OWASP Top 10 baseline. Apply this BEFORE the first
  public deploy, not as an afterthought.
- **Reference: `references/seeding-patterns.md`** — bcrypt-via-Postgres-crypt
  template, idempotent seed SQL, user-id resolution pattern.
- **Reference: `references/chris-deploy-workflow.md`** — repo-mirror pattern,
  autonomous-mode expectations, reporting style.
- **Reference: `references/security-hardening-patterns.md`** — full pattern
  for Caddy + nginx + Express security headers, wildcard CORS removal,
  Caddy site-block template, and the curl checks to verify hardening.
- **Script: `scripts/validate_app.sh`** — 80-assertion validation template
  covering every API group. Copy and adapt the path/method/payload lines.