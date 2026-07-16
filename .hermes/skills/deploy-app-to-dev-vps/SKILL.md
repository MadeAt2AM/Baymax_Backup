---
name: deploy-app-to-dev-vps
description: "Deploy a new (or replacement) app to the dev VPS at 147.79.18.32 behind the existing Caddy reverse proxy. Covers the full lifecycle: source preparation, mirror to MadeAt2AM org, teardown, first-pull, schema migration, seed data, comprehensive validation, webhook auto-redeploy, live verification, and the three-layer custom-domain / white-label routing pattern. SYNTRA v1 + v2 + custom-domain fix (Jul 2026) are the worked examples."
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
| **Custom-domain sidecar** | `/srv/secrets/<name>-custom-domains` | One hostname per line; materialised into `/srv/caddy/sites/<name>-extra-hosts.caddy` by the deploy script. See `references/custom-domain-routing.md`. |
| Webhook receiver | `/etc/webhook/hooks.json` (`github-push-<name>` entry) | Receives GitHub push events on port 9000, runs `syntra_dev.sh redeploy` |
| Deploy helper | `/srv/scripts/<name>_dev.sh` | Reads `GH_TOKEN` from `/srv/scripts/.gh-token`, runs `docker compose up -d --build`, writes caddy blocks (platform + extras), reloads Caddy. **This file lives on the VPS only — it is NOT auto-synced from `deploy/<name>_dev.sh` in the repo. See gotcha #26.** |
| CF DNS env | `/srv/scripts/.cf-env` | Cloudflare API token + zone ID, sourced by deploy helper for idempotent DNS |
| Network | external `web` (Docker bridge) | Shared with Caddy. Has Caddy + payntra-app + baymax-pipeline-probe-app already attached |
| Private DB network | `<name>_<name>-net` (e.g. `syntra_syntra-net`) | MTU 1400 to match Hetzner eth0; carries DB traffic only |

DO NOT:
- Modify `/srv/scripts/project_dev.sh` for a new project — it's used by payntra/probe. Add a project-specific deploy helper like `<name>_dev.sh` instead.
- Bounce the Caddy container for config changes — use `docker exec caddy caddy reload`.
- Touch the `web` network's bridge MTU — it's already 1400 via `/etc/docker/daemon.json`.
- Hardcode verified custom-domain hostnames into the platform-host Caddy site block. Always go through `/srv/secrets/<name>-custom-domains` so operators can add/remove a domain without a redeploy.

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
14. **`.ts` file containing JSX does not compile** — esbuild keys JSX
    parsing off the file extension, not the tsconfig. A hook or
    component written as `use-auth.ts` that returns
    `<AuthContext.Provider>...` will fail with `Expected ">" but found
    "value"` because esbuild treats it as plain TypeScript. **Rename to
    `.tsx` for any file with JSX.** Symptom: build fails with that
    message at the line of the first JSX element. Same applies to
    `route.ts`, `middleware.ts`, etc.
15. **`.pnpm-store` must be gitignored before any `pnpm install`** —
    When you run `pnpm install --no-frozen-lockfile` to regenerate the
    lockfile (gotcha #10), pnpm populates `.pnpm-store/` with ~5,000
    content-addressable files. If `.gitignore` doesn't have
    `.pnpm-store`, a `git add -A` will try to stage them all. Add to
    `.gitignore` BEFORE running pnpm install. If you forget, recover
    with `git rm -r --cached .pnpm-store` and recommit.
16. **CORS `cb(new Error(...))` bubbles to global handler → 500** —
    In `middlewares/cors.ts`, returning `cb(new Error(...))` for a
    disallowed origin makes Express's global error handler return
    HTTP 500 (because the generic 500 handler catches the Error). That's
    misleading (the request never reached a handler) and can leak info
    if the error handler isn't generic. Use `cb(null, false)` instead —
    cors() skips adding CORS headers, browsers see no
    `Access-Control-Allow-Origin` and block the response. Client gets a
    clean CORS error; server returns whatever the route returns. See
    `references/security-hardening-patterns.md`.
17. **CSP from multiple layers is intersected by the browser** — When
    BOTH Caddy and nginx emit `Content-Security-Policy` headers, the
    browser intersects them. If nginx sets `script-src 'self'` and
    Caddy sets `script-src 'self' 'unsafe-inline'`, the effective
    policy is `'self'` only (more restrictive wins). This silently
    breaks Vite-built bundles that need `'unsafe-inline'` for inline
    styles. **Either** set `unsafe-inline` in BOTH layers **or**
    remove it from BOTH. Verify with `curl -sI` on every response type.
18. **SPA blank-screen hardening pattern** — Three defensive moves to
    guarantee a user never sees a blank white screen on a SPA:
    a. Wrap the entire app in a top-level React `<ErrorBoundary>` that
       catches unhandled render errors and shows a recovery card
       ("Reload page" / "Clear cache & retry") with the error message.
    b. Wrap every `localStorage.getItem/setItem/removeItem` call in
       `try/catch`. Safari Private Mode, some browser extensions, and
       cookie-disabled contexts throw on storage access.
    c. When `useGetMe()` returns an error (typically 401 from a stale
       JWT — common after `SESSION_SECRET` rotation), automatically
       wipe `auth_token` + `must_change_password` from localStorage
       and reset React state. Otherwise the spinner hangs forever.
19. **Email column lookups are case-sensitive in Postgres** —
    `eq(users.email, value)` matches only exact-case rows, so
    `Platform@syntra.com` and `platform@syntra.com` are treated as
    different identities. Login fails with 401 if the user types the
    wrong case against a lowercase DB row. **Two-layer defense:**
    (a) normalize input on the application side with
    `normalizeEmail(v)` → `v.trim().toLowerCase()`, and (b) compare
    with `lower(email_column) = lower($1)` on the DB side via a
    single `emailEq(column, value)` helper. The DB-side `lower()`
    catches legacy mixed-case rows that pre-date normalization.
    Apply to every endpoint that matches on email: login, register,
    forgot-password, password-reset, invitations, user create,
    admin invite, etc. Pattern + worked example:
    `references/case-insensitive-email.md`.
20. **Echo-once plaintext + form.reset() trap** — When a flow
    generates a transient value (a temp password, a share token,
    a one-time code) that the UI must display for the operator to
    copy, the API MUST echo that plaintext once in the 201 response
    (e.g. `tempPassword` in the body) — because the UI's success-state
    panel runs AFTER `form.reset()` wipes the form values that held
    the plaintext. Reading from form state leaves the eye-toggle and
    copy button blank. **Pair this with:** never re-serve the
    plaintext from any GET endpoint (it must be bcrypt-hashed in the
    DB), and keep the copy function tolerant of clipboard-permission
    denials (fall back to `document.execCommand('copy')` on
    non-secure contexts, surface a toast on failure rather than
    failing silently, add `select-all` to the display so manual
    selection works).
21. **`git stash` + `git stash drop` can silently lose working-tree
    edits** — If you stash a subset of changes to "clean the diff"
    before committing, then drop the stash without `git stash pop`,
    any file you edited OUTSIDE that subset ALSO disappears if the
    stash happened to record a non-obvious dependency (e.g. an
    import + a mount line that were in different commits of your
    stashed chunk). Symptom: commit lands, build/typecheck pass
    locally, but the route is missing at runtime. **Defensive habit:**
    before `git stash drop`, run `git stash show -p stash@{0} --stat`
    and `git diff HEAD -- <suspect-file>` to confirm everything you
    need is either in the working tree OR staged. For multi-file
    edits where you really need a partial stash, prefer
    `git stash push -- <files>` with explicit paths so the stash
    contains only what you intend to set aside.
22. **"Bundle imports the file but the route is missing at runtime"
    is a router-mount bug, not a build bug** — When esbuild bundles
    a server, an imported-but-unmounted module is still present in
    the output JS as long as something references it. So you cannot
    tell "is this route registered?" by grepping for the file name.
    **Verify with the mount-pattern grep:**
    ```bash
    docker exec <api> sh -c "grep -oE 'use\\(\\s*[\"\\'][^\"\\']+[\"\\'],\\s*[a-zA-Z_]+' /app/dist/index.mjs | sort -u"
    ```
    Every line should correspond to a `router.use(...)` in your
    source. If a new route is missing from this list, the bug is
    upstream (mount line never made it into the source you pushed —
    usually a git stash / rebase / amend mishap), NOT in esbuild.
23. **`docker compose build` is incremental — use `--no-cache` when
    the prior build succeeded but source changed and you need a
    guaranteed fresh bundle** — esbuild and pnpm caches survive
    rebuilds. If you pushed a fix to the bundle source and
    `docker compose up -d --build` reports `DONE 0.1s` (no actual
    work), the running container still has the old bundle. Force
    a clean rebuild with `--no-cache`. Pair with
    `docker compose up -d --force-recreate` to ensure the container
    is restarted with the new image, not just the same image relabeled.
24. **Local `vite build` / `tsc` OOM-throttled on this host — skip
    and trust the VPS Docker pipeline** — the local dev VM runs under
    a memory cgroup that throttles high-memory processes into
    `D` (uninterruptible disk-wait) state on `mem_cgroup_handle_over_high`
    (visible in `/proc/<pid>/wchan`). Symptom: `npx vite build` or
    `npx tsc --noEmit` hangs indefinitely with no stdout output and
    cannot be cleanly SIGKILL'd. **Don't waste a tool-call budget
    fighting it.** Trust that the project's `build.mjs` (esbuild) and
    the Docker-in-VPS build pipeline will catch any real compile error.
    Validate by pushing to the webhook and watching
    `docker compose logs --build`.
25. **Custom-domain routing requires THREE coordinated fixes — and "the
    skill says it was done" ≠ "the code matches the skill"** — bug
    reports of the form "my custom domain doesn't work / users are
    served from the platform URL" almost always have all three layers
    broken at once:
    (a) **Caddy vhost missing** — `/srv/caddy/sites/<name>.caddy` only
        declares the platform host. No site block for the custom
        hostname → Caddy can't issue a cert, request hangs.
    (b) **API auth response has no `redirectTo`** — even with (a)
        fixed, users entering via the platform URL never get bounced
        to their company's own URL because the API never tells the
        client to.
    (c) **CORS allowlist is hardcoded** — `middlewares/cors.ts` only
        allows the platform origin. Browsers calling from the custom
        origin fail CORS preflight even if (a) and (b) are fixed.
    Diagnose with one curl per layer, then patch all three. See
    `references/custom-domain-routing.md` for the full pattern and
    the SYNTRA fix walkthrough.
    **Drift warning (Jul 2026):** the SYNTRA v1 deploy (2026-07-15)
    shipped with layer (a) wired and the documentation claiming all
    three layers were live — but the code for (b) and (c) had never
    landed (the doc was written before the implementation). When a
    custom-domain bug is reported on a project where the docs say
    "fixed", still run the per-layer curl probe. `cat
    /srv/caddy/sites/<name>-extra-hosts.caddy` for (a), `curl -X POST
    /api/auth/login` for (b) (look for `redirectTo` in the response),
    and `curl -X OPTIONS -H "Origin: https://<host>"` for (c). Trust
    the runtime, not the docs.
26. **`deploy/<name>_dev.sh` ≠ `/srv/scripts/<name>_dev.sh`** — the
    deploy helper script lives in TWO places. The repo has
    `deploy/<name>_dev.sh` (or `deploy/syntra_dev.sh`) which is the
    source-controlled version. The webhook daemon calls
    `/srv/scripts/<name>_dev.sh` on the VPS, which was placed there
    once via `sudo cp deploy/<name>_dev.sh /srv/scripts/` (see
    `VPS_DEPLOYMENT.md`). **Editing and pushing the repo copy has
    zero effect on the live webhook.** Symptoms: you add a new
    function, push, the redeploy runs the old script, the new
    function never executes. Fix: `scp deploy/<name>_dev.sh
    dev-vps:/srv/scripts/<name>_dev.sh && ssh dev-vps 'chmod +x
    /srv/scripts/<name>_dev.sh'` AFTER every change to the repo
    copy. Same applies to any other file in `/srv/scripts/`. **Until
    the deploy helper itself is also bind-mounted or git-tracked at
    `/srv/scripts/`, this is a manual propagation step.** Verify
    after by `ssh dev-vps 'grep -c <your-new-fn>
    /srv/scripts/<name>_dev.sh'` returning >0.
27. **`/srv/secrets/<name>.env` IS the source of truth for env vars,
    NOT `docker-compose.yml`'s `env_file:` declaration** — Compose's
    `env_file:` key bind-mounts that host file into the container;
    the `environment:` block can override individual keys but the
    base set of variables the container sees comes from the file.
    **Adding a new env var requires editing `/srv/secrets/<name>.env`
    on the VPS, not just the compose file in the repo.** The deploy
    script copies this file to `/srv/projects/<name>/.env` only on
    first deploy (subsequent deploys reuse the existing `.env` so
    manual secrets tweaks survive). Symptom: you push a code change
    that reads `process.env.NEW_VAR`, redeploy, the container still
    has no `NEW_VAR` because the `.env` was never refreshed. Three
    fixes, in order of preference:
    (a) `echo 'NEW_VAR=value' >> /srv/secrets/<name>.env && rm -f
        /srv/projects/<name>/.env && bash /srv/scripts/<name>_dev.sh
        redeploy` — removes `.env` so the next deploy re-materialises
        it from the updated secrets file.
    (b) `bash /srv/scripts/<name>_dev.sh redeploy` after editing
        secrets — but ONLY if you ALSO `rm .env` first, otherwise
        the cp is skipped.
    (c) Drop a temporary marker into `.env` yourself (`ssh dev-vps
        'echo NEW_VAR=value >> /srv/projects/<name>/.env'`) — quick
        but it gets clobbered on next first-deploy.
    Verify with `ssh dev-vps 'docker exec <api> env | grep NEW_VAR'`.
28. **Kernel-scheduler overload — recognise it, stop fighting it, hand
    off via a STATUS doc OR push via GitHub Data API** — on the local
    dev VM (not the VPS), every shell command can hang for 2–5
    minutes because the host is in a swap-thrash state from many LSP
    `tsserver.js` processes each holding ~600 MB resident + heavy
    compile output in /proc's swap pressure. Signature: `free -h`
    shows swap fully consumed (2.0/2.0 GB), `ps --sort=-%mem` shows
    5+ `tsserver.js` entries at the top, and `uptime` reports load
    average > 10. Even `echo $$`, `git log -1`, and a single
    `git add <file>` time out.
    When this happens: **first check whether HTTPS to `api.github.com`
    still works** (`urllib.request.urlopen("https://api.github.com/",
    timeout=10)` — typically <2s response time). If it does, you can
    bypass the wedged local `git` entirely by pushing via the GitHub
    Data API (blob → tree → commit → ref). See the
    `github-data-api-direct-push` skill for the working Python
    template; the gotcha here is the "Update is not a fast forward"
    retry loop when a parallel commit lands while you're building
    yours. **Use this path** instead of giving up — it succeeds in
    seconds when the kernel is jammed but HTTPS is fine.
    Only when both local `git` AND HTTPS are wedged should you fall
    back to the STATUS-doc handoff: verify file-on-disk (every edited
    path's `os.path.getsize()` matches the expected post-edit size —
    proves the writes landed in BOTH `source/` and the deploy-mirror
    worktree), then write a STATUS doc with: (a) every file modified
    + a one-line description of the change, (b) the exact `git add`
    and `git commit -m ...` commands to run from a healthy shell,
    (c) the live-verification curl one-liners. Use
    `templates/ship-handoff.md` as the template. The next session
    (or Chris from a healthier shell) can pick up the docs and finish
    the ship in under a minute. **Never fabricate the success
    report** ("pushed ✓") when the underlying command actually timed
    out.
29. **Webhook 504 timeout ≠ build failure** — the webhook daemon on
    port 9000 runs `<name>_dev.sh redeploy` synchronously, but the
    docker build + caddy reload typically takes 30–90s. GitHub caps
    webhook responses at 10s, so every delivery is reported as
    `status=504, duration=10s` even when the build eventually
    succeeds. **Verify by probing the served behaviour, not by
    reading the webhook delivery status.**
    Concrete signals of "build completed":
    - SPA bundle: `curl -sI https://<name>.<root>/` → new asset hash
      in the HTML (`<script src="/assets/index-<newhash>.js">`).
      Then `curl -s https://<name>.<root>/assets/index-<newhash>.js |
      grep <new-symbol>` to confirm the new code is actually in the
      bundle (esbuild minifies function names — search for distinctive
      strings like `data-testid` values or new component names instead
      of the original function names).
    - API behaviour: hit the new endpoint or check that an old
      endpoint's response shape changed (new query parameter handling,
      new field in JSON response). Behavioural diff is more reliable
      than the webhook delivery log.
    - Order checks: `?includeInactive=true` returning DESC order
      proves a new code path with `.orderBy(...)` is live; old code
      without orderBy returns insertion order. Use order diffs as a
      code-version fingerprint.
    If after 90–120s the served bundle / API behaviour has NOT
    changed, then the build genuinely failed. SSH to the VPS (or read
    `/var/log/webhook.log` via the GitHub API if you can't) to find
    the actual error.
30. **Lifecycle tests on a live DB are rate-limited by the public
    IP** — `loginIpLimiter` / `loginEmailLimiter` (see skill
    `security-hardening-web-stack`, the `trust proxy = 1` and
    `loginEmailLimiter keyGenerator` pitfalls) return `429 Too many
    attempts` after a handful of `/auth/login` hits from the same
    egress IP. The verifier on this host shares
    one egress IP, so any "create test tenant → login as its owner →
    assert response" round-trip will trip the limiter within 3-5
    requests. **Call the API from inside the API container** to bypass
    both the IP and the email limiter — the container's local
    traffic doesn't pass through Caddy or hit the limiter middleware:
    ```bash
    ssh dev-vps 'docker exec -e EMAIL=... -e PW=... <api_container> \
      node -e "fetch(\"http://127.0.0.1:8080/api/auth/login\",\
        {method:\"POST\",headers:{\"Content-Type\":\"application/json\"},\
         body:JSON.stringify({email:process.env.EMAIL,password:process.env.PW})})\
        .then(async r => console.log(r.status + \"|\" + await r.text()))"'
    ```
    For full lifecycle scripts (create → activate → deactivate →
    hard-delete), mint a short-lived JWT inside the container so the
    test never hits `/auth/login` at all. Look up the seed platform
    admin's user id from the DB (`docker exec <pg_container> psql -U
    <user> -d <db> -Atc "SELECT id FROM users WHERE role =
    'platform_admin' ORDER BY id LIMIT 1"`) and replace the hard-coded
    `userId:5` with that value. Same `SECRET` value as in
    `/srv/secrets/<name>.env`:
    ```bash
    ssh dev-vps 'docker exec -e SECRET="$(docker exec <api> \
      printenv SESSION_SECRET)" -e ADMIN_ID="$(docker exec <pg> psql -U \
      <user> -d <db> -Atc \"SELECT id FROM users WHERE role='\''platform_admin'\'' \
      ORDER BY id LIMIT 1\")" <api> node -e "
      const enc = b => Buffer.from(b).toString(\"base64url\");
      const h = enc(JSON.stringify({alg:\"HS256\",typ:\"JWT\"}));
      const p = enc(JSON.stringify({userId:Number(process.env.ADMIN_ID),
        companyId:null,role:\"platform_admin\",
        exp:Math.floor(Date.now()/1000)+3600}));
      const sig = enc(require(\"crypto\").createHmac(\"sha256\",
        process.env.SECRET).update(\`${h}.${p}\`).digest());
      console.log(\`${h}.${p}.${sig}\`)"'
    ```
    Then run the test from the same `docker exec` and `curl` to
    `https://<name>.terrybot.top` (or wherever) with that token. Pair
    the script with a `trap cleanup EXIT` that hard-deletes the
    disposable tenant even if any intermediate step fails. Verify
    afterwards with `ssh dev-vps 'docker exec <pg> psql -U <user> -d
    <db> -Atc "SELECT count(*) FROM companies WHERE name LIKE '\''Baymax
    Lifecycle %'\''"` returns 0.
    **Always deliver the lifecycle script via base64 over ssh** to
    avoid heredoc quoting disasters — single-quote-in-quote-in-quote
    errors silently truncate the script and you end up with a
    half-formed `trap` that drops the cleanup, leaving orphan test
    data in the live database. `python3 -c "import base64;
    print(base64.b64encode(open('/dev/stdin','rb').read()).decode())"`
    on the host, then `printf '%s' '<b64>' | base64 -d | bash` on the
    VPS. See `references/live-lifecycle-tests.md` for the full
    pattern.
31. **`fetchPlatform<void>` for HTTP 204 endpoints** — the SPA's
    `fetchPlatform<T>` helper in `artifacts/web-app/src/lib/<app>-api.ts`
    calls `res.json()` unconditionally. DELETE endpoints that return
    204 (no body) blow up on the client with a `SyntaxError: Unexpected
    end of JSON input`. **Two-line fix in the helper:**
    ```ts
    if (res.status === 204) return undefined as T;
    return res.json();
    ```
    Then declare the mutation's `mutationFn` return as
    `Promise<void>` (or use the `fetchPlatform<void>` shape, depending
    on the codebase's convention). Hard-delete and any other
    "204 No Content" endpoint needs both — the server-side route must
    return 204 AND the client helper must tolerate the empty body.
    When you add the first 204 endpoint, audit every existing
    `fetchPlatform` caller for the same failure mode.
32. **Clean-room checkout before surgical fixes** — when the existing
    `/root/.hermes/projects/<name>/deploy-mirror` worktree has staged
    or unstaged changes from a previous procedure (look for `MM` or
    large `M` counts in `git status --short`), do NOT mix new edits
    into it. Clone fresh instead:
    `git clone --depth=1 https://github.com/MadeAt2AM/<name>_VPS.git
    /root/.hermes/projects/<name>/<feature-folder>`. This gives you a
    clean tree for surgical changes, avoids spurious diffs, and
    doesn't risk losing unrelated in-progress work. After the
    surgical change ships, the dirty worktree can be cleaned up by
    the next session. **Don't `git checkout --` or `git restore .`
    the dirty tree** — that's how you destroy untracked edits from
    another procedure.
33. **`patch` tool collapses on duplicate near-identical blocks** —
    `artifacts/api-server/src/routes/auth.ts` has TWO
    `db.select().from(users).where(emailEq(users.email, email)).limit(1)`
    blocks (one in `/register`'s invitation flow, one in `/login`)
    with identical whitespace. A `patch` with the small surrounding
    context matches BOTH and rejects with "Found 2 matches".
    Solution: include enough context lines to disambiguate
    (e.g. the surrounding `if (!user)` or `const valid = await
    bcrypt.compare(...)` line), or fall back to `execute_code` +
    `Path.read_text()` + `Path.write_text()` with an exact `count==1`
    assertion. The first failed patch attempt at 60s already counted
    against the budget; the second attempt silently matched the wrong
    block in some codebases. **Always print which line numbers
    matched before writing** — `text.splitlines()` + a print loop is
    one line of code and saves an entire rebuild cycle.
35. **`node:test` / `node:assert/strict` typecheck noise in fresh
    checkouts** — a new `test/foo.test.ts` file in
    `artifacts/<svc>/test/` will trip `tsc --noEmit` with
    `Cannot find name 'node:test'` and `Cannot find name
    'node:assert/strict'`. `@types/node` IS installed (it's a
    catalog dep) but the test file is OUTSIDE the api-server's
    `tsconfig.json` `include: ["src"]`. Two fixes, in order:
    (a) Don't gate on typecheck — run the test directly with
    `pnpm exec esbuild test/foo.test.ts --bundle --platform=node
    --format=esm --outfile=/tmp/foo.test.mjs && node --test
    /tmp/foo.test.mjs`. The bundle ignores tsconfig include
    boundaries; the test runs fine and you get the TDD red/green
    signal.
    (b) Once the test is green, add `"test"` to the `include` array
    in `artifacts/<svc>/tsconfig.json` so the typecheck pipeline sees
    it permanently. Don't do this for throwaway tests — only for
    tests you're shipping to the repo.
36. **`Invalid credentials` can mean `Invalid credentials` OR
    `Too many attempts`** — when a user reports they cannot log in,
    do NOT immediately reset their password. Diagnostic order:
    1. **Read the actual response** — `429 {"error":"Too many
       attempts for this account..."}` means the limiter is the
       problem, not the password. `401 {"error":"Invalid
       credentials"}` is the only signal that the bcrypt hash is
       actually wrong.
    2. **Probe the stored hash** from the DB to confirm password
       correctness without hitting the API:
       ```bash
       ssh dev-vps 'docker exec <pg> psql -U <user> -d <db> -Atc \
         "SELECT email, crypt('\''<pw>'\'', password_hash)=password_hash \
          FROM users WHERE lower(email)=lower('\''<email>'\'')"'
       ```
       `t` = password matches, `f` = different password (then reset
       with the same `crypt()` expression in an `UPDATE`).
    3. **Probe the limiter** by attempting a different, never-used
       account from the same network. If the second account also
       returns `429`, the IP bucket is the problem — not the user's
       password. The default `loginEmailLimiter` keys by client IP
       unless a `keyGenerator` is supplied; fix is in
       `security-hardening-web-stack` gotcha 3a.
    4. **Reset only when the hash check returned `f`**. If the
       password was correct and the limiter was blocking them,
       resetting the password does nothing — the in-memory limiter
       bucket is still active until the container restarts or 15
       minutes pass.

## Verification checklist before declaring done

- [ ] `https://<name>.<domain>/` returns 200
- [ ] `https://<name>.<domain>/api/healthz` returns `{"status":"ok"}`
- [ ] Every verified custom-domain host returns 200 (HTTPS via ACME-issued cert)
- [ ] All seed users can log in and reach their role-appropriate UI
- [ ] `validate_app.sh` returns 0 FAIL
- [ ] Custom-domain round-trip works:
  PUT domain → status:pending → POST verify → status:verified
- [ ] Post-login cross-origin redirect works: a user with a verified
  custom domain, logging in via `https://<name>.<domain>/login`, lands
  on `https://<custom-domain>/dashboard` after submit (and the
  API response includes `redirectTo`).
- [ ] SMTP test endpoint returns 2xx
- [ ] Role-based access denials return 403 (staff can't create workplaces, etc.)
- [ ] GitHub webhook end-to-end: no-op commit → webhook log shows
  "triggered" + "executing" → `.baymax-last-deploy` updates
- [ ] After editing `deploy/<name>_dev.sh` in the repo, ALSO
  `scp` it to `/srv/scripts/<name>_dev.sh` on the VPS — the two
  files drift otherwise (gotcha #26). Verify with `ssh dev-vps
  'grep -c <new-fn> /srv/scripts/<name>_dev.sh'`.
- [ ] After adding a new env var to compose `environment:`, ALSO
  append it to `/srv/secrets/<name>.env` on the VPS and `rm -f
  /srv/projects/<name>/.env` so the next deploy re-materialises it
  (gotcha #27). Verify with `ssh dev-vps 'docker exec <api> env |
  grep <NEW_VAR>'`.
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
- **Reference: `references/case-insensitive-email.md`** — `normalizeEmail`
  + `emailEq` helpers, the two-layer defense rationale, and a
  retrofit checklist for every endpoint that matches on email.
- **Script: `scripts/validate_app.sh`** — 80-assertion validation template
  covering every API group. Copy and adapt the path/method/payload lines.
- **Script: `scripts/protocol-verify.sh`** — wire-protocol verification
  for non-JSON endpoints (calendar feeds, RSS, webhooks, CSV exports).
  Asserts Content-Type / Content-Disposition / body markers / CRLF line
  endings / revocation lifecycle. Use for any endpoint that returns
  structured text/binary instead of JSON.
- **Reference: `references/custom-domain-routing.md`** — the three-layer
  white-label pattern (Caddy sidecar + post-auth cross-origin redirect +
  CORS allowlist driven by a single source-of-truth helper). **Required
  reading before adding custom-domain / per-tenant hostname support to
  any app on this VPS.**
- **Template: `templates/extra_hosts_caddy_snippet.sh`** — drop-in shell
  snippet for `<name>_dev.sh` that materialises the per-host sidecar
  from `/srv/secrets/<name>-custom-domains`. Pairs with the new
  reference above.
- **Script: `scripts/verify-custom-domain.sh`** — 8-step live verification
  (DNS CNAME → Caddy vhost → HTTPS → API branding → login-bounce →
  login-no-bounce → platform-admin-no-bounce → CORS preflight). Run
  after every new custom-domain addition. Adapt the env vars at the
  top, then `bash scripts/verify-custom-domain.sh` against the VPS.
- **Reference: `references/live-lifecycle-tests.md`** — running
  lifecycle verification (create → activate → deactivate →
  hard-delete) on the live dev database without tripping the
  `loginIpLimiter` / `loginEmailLimiter` rate limit. Mint a short-lived
  JWT inside the API container with the same `SESSION_SECRET` so the
  test never hits `/auth/login` from the public IP. Pairs with
  gotcha #30.
- **Template: `templates/ship-handoff.md`** — copy-paste skeleton for the
  STATUS doc you write when the local VM is in kernel-scheduler overload
  and you can't push. Captures the "what was edited", "how to ship
  when the host recovers", and "live verification" sections. See
  gotcha #28 for when to use this.
- **Skill: `github-data-api-direct-push`** — the bypass-git push path
  used when the local `git` binary is wedged but HTTPS to
  `api.github.com` still works. Pairs with gotcha #28 as the
  first-choice escalation before falling back to a STATUS doc.
- **Skill: `vps-ram-pressure`** — covers the underlying "every shell
  command stalls for minutes" symptom that triggers gotcha #28 in
  this skill. See "The every-command-stalls symptom" in that skill
  for the diagnostic checklist and the recovery path (kill / cap the
  top RSS hogs to free swap pressure).