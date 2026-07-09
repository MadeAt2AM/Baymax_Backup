# SYNTRA VPS deploy — full session record (2026-07-08)

Reference runbook for the class of deploy where the **GitHub repo name differs from the subdomain**. The shared `project_dev.sh` script on the dev VPS assumes `repo == subdomain`. When those diverge, you need a per-project deploy script and a second webhook hook entry.

This document captures the entire path so the next session doesn't have to rediscover it.

## Topology that resulted

```
MadeAt2AM/SYNTRA_VPS        ──► webhook :9000 ──► /srv/scripts/syntra_dev.sh redeploy
   (repo, "VPS" suffix)                                        │
                                                               ▼
                                          /srv/projects/syntra/  ← cloned & reset on each push
                                          ├─ docker-compose.yml   ← custom (private MTU=1400 net + shared `web` net)
                                          ├─ .env                 ← seeded from /srv/secrets/syntra.env on first deploy
                                          ├─ deploy/syntra_dev.sh ← helper script also committed in repo
                                          ├─ deploy/hooks.json    ← template for the dev VPS hook entry
                                          ├─ deploy/seed_demo_users.sh
                                          └─ deploy/docker/Dockerfile.{api,web,migrate}  ← Debian-slim build (Alpine-musl breaks rollup)

syntra.terrybot.top  ──►  Caddy (on shared `web` Docker network)
                          │
                          └── reverse_proxy syntra-web:80

syntra_postgres  ◄───private MTU=1400 network (syntra_syntra-net)──►  syntra_api
syntra_api       ◄───private MTU=1400 network (syntra_syntra-net)──►  syntra_postgres
syntra_api       ◄───shared `web` network────────────────────────────►  Caddy
syntra_web       ◄───shared `web` network────────────────────────────►  Caddy
```

## What we committed to `MadeAt2AM/SYNTRA_VPS`

- **`docker-compose.yml`** — split private MTU=1400 net + shared external `web` net; web container has alias `syntra-app` on both nets; no host port mapping on web (Caddy talks container-direct on the `web` network).
- **`deploy/docker/Dockerfile.api|web|migrate`** — Debian-slim base images (not Alpine). Original Alpine-targeted Dockerfiles excluded `@rollup/rollup-linux-x64-musl` for Replit, which broke alpine-musl builds.
- **`deploy/syntra_dev.sh`** — per-project deploy helper. Subcommands: `first-pull` / `redeploy` / `status` / `teardown`. Hardcoded `PROJ_NAME=syntra`, `REPO_NAME=SYNTRA_VPS`. Sources `/srv/scripts/.cf-env` for DNS creation.
- **`deploy/seed_demo_users.sh`** — Postgres-side user seeder using pgcrypto crypt().
- **`deploy/hooks.json`** — template for the dev VPS hook entry (the SYNTRA-specific one).

## What we set on the dev VPS

- **`/etc/docker/daemon.json`** — global MTU=1400 (had to set this for build-time apt to work on Hetzner). All containers restarted briefly.
- **`/etc/webhook/hooks.json`** — added a second hook entry `github-push-syntra` matching `repository.name == "SYNTRA_VPS"`. Original `github-push` hook narrowed to only `payntra` + `baymax-pipeline-probe` so SYNTRA pushes don't double-fire.
- **`/etc/webhook/webhook.env`** — holds `CF_API_TOKEN`, `CF_ZONE_ID`, `CF_DOMAIN` so the webhook daemon's hook invocations can create DNS records.
- **`/srv/scripts/syntra_dev.sh`** — installed from the deploy dir; chmod 755.
- **`/srv/scripts/.cf-env`** — same CF env as above, sourced by the deploy script.
- **`/srv/scripts/.gh-token`** — already present from Payntra setup; SYNTRA reuses it.
- **`/srv/secrets/syntra.env`** — the actual env file with secrets. Seeded into `/srv/projects/syntra/.env` on first deploy.
- **`/srv/caddy/sites/syntra.caddy`** — written by the script with `reverse_proxy syntra-web:80`.

## Cloudflare

- **A record `syntra.terrybot.top → 147.79.18.32`** added via direct CF API call (proxy=false, mirroring payntra).

## Test users seeded

| email | role | company_id | status |
|---|---|---|---|
| platform@demo.com | platform_admin | - | active |
| admin@demo.com | admin | 1 (Demo Co) | active |
| manager@demo.com | manager | 1 (Demo Co) | active |
| staff@demo.com | employee | 1 (Demo Co) | active |

All with bcrypt `$2a$12$...` hashes via `crypt('Test123!', gen_salt('bf', 12))`.

## Live verification status at end of session

| check | result |
|---|---|
| containers healthy | confirmed via `docker ps` — postgres + api + web all healthy |
| schema applied | confirmed — all 9 tables present matching UAT dump |
| test users seeded | confirmed — 4 rows with bcrypt hashes |
| HTTPS round-trip | NOT YET confirmed at session end |
| GitHub webhook | NOT YET registered on SYNTRA_VPS repo |
| Push-to-redeploy loop | NOT YET closed end-to-end |

## Pitfalls we hit (all rolled into SKILL.md)

1. **AJ** — `cd` after `git fetch` in the redeploy branch of the deploy script
2. **AK** — repo name != subdomain requires a per-project deploy script + a second hook entry
3. **AL** — Hetzner MTU=1400 needs Docker daemon.json global fix, not just per-network
4. **AM** — Debian-slim lacks wget; install it or use Node-based healthcheck
5. **AN** — bcrypt-compatible hashes via Postgres `crypt(pw, gen_salt('bf', 12))`

## Replay-this-deploy checklist

```bash
# 0. Pre-flight (VPS)
ssh dev-vps 'cat /etc/docker/daemon.json'   # mtu=1400 must be set
ssh dev-vps 'docker network inspect web --format "{{.Containers}}"'  # Caddy present

# 1. Local
git clone https://github.com/MadeAt2AM/SYNTRA_VPS.git source && cd source
# (the deploy/docker/ Dockerfiles + syntra_dev.sh + hooks.json + seed_demo_users.sh are already committed)

# 2. Create /srv/secrets/syntra.env with the project secrets on the VPS
ssh dev-vps "mkdir -p /srv/secrets"
# Write POSTGRES_PASSWORD, SESSION_SECRET, APP_BASE_URL, CONTACT_SMTP_*
# via scp or write_file locally then scp to /srv/secrets/syntra.env

# 3. Install syntra_dev.sh on the VPS
scp deploy/syntra_dev.sh dev-vps:/srv/scripts/syntra_dev.sh
ssh dev-vps 'chmod 755 /srv/scripts/syntra_dev.sh'

# 4. Wire CF env (if not already set)
ssh dev-vps "cat > /srv/scripts/.cf-env <<EOF
CF_API_TOKEN=$CF_API_TOKEN
CF_ZONE_ID=$CF_ZONE_ID
CF_DOMAIN=$CF_DOMAIN
EOF
chmod 600 /srv/scripts/.cf-env"

# 5. Wire webhook env (so the systemd-managed webhook daemon sees CF_*)
ssh dev-vps "cat > /etc/webhook/webhook.env <<EOF
CF_API_TOKEN=$CF_API_TOKEN
CF_ZONE_ID=$CF_ZONE_ID
CF_DOMAIN=$CF_DOMAIN
EOF
chmod 600 /etc/webhook/webhook.env"

# 6. Add the per-project hook entry to /etc/webhook/hooks.json
#    (see deploy/hooks.json in the repo for the template; or
#     `ssh dev-vps 'cat /etc/webhook/hooks.json.bak'` to start from the last known-good)
ssh dev-vps 'cp /etc/webhook/hooks.json /etc/webhook/hooks.json.bak'
# Append the new entry from deploy/hooks.json to the existing /etc/webhook/hooks.json

# 7. Add DNS record (do this BEFORE first-pull so webhook-driven DNS creation has something to fall back on)
CF_TOKEN=... CF_ZONE_ID=... CF_DOMAIN=...
curl -sS -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records" \
  -H "Authorization: Bearer ${CF_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{\"type\":\"A\",\"name\":\"syntra.${CF_DOMAIN}\",\"content\":\"147.79.18.32\",\"ttl\":60,\"proxied\":false}"

# 8. First-pull
ssh dev-vps 'GH_TOKEN=$(cat /srv/scripts/.gh-token) bash /tmp/run_first_pull.sh'
# (run_first_pull.sh is a local helper that exports GH_TOKEN and runs syntra_dev.sh first-pull)

# 9. Run migrations
ssh dev-vps 'cd /srv/projects/syntra && docker compose run --rm migrate'

# 10. Seed demo users
ssh dev-vps '/srv/scripts/syntra_seed_demo_users.sh'

# 11. Verify HTTPS
curl -sI https://syntra.terrybot.top/api/healthz
curl -sI https://syntra.terrybot.top/

# 12. Register webhook on GitHub (web UI: Settings > Webhooks > Add)
#    Payload URL: http://147.79.18.32:9000/hooks/github-push-syntra
#    Content type: application/json
#    Secret: <same secret as the original github-push hook>
#    Events: Just the push event
#    Active: ✓

# 13. End-to-end verify (push a no-op commit)
echo "// $(date)" >> deploy/.deploy_test
git commit -am "deploy: no-op smoke test"
git push vps main
sleep 30
ssh dev-vps 'tail -5 /var/log/webhook.log'
ssh dev-vps 'cd /srv/projects/syntra && git log --oneline -3'
curl -sI https://syntra.terrybot.top/api/healthz
```

## Why this matters as a reference doc

SYNTRA was the first deploy where:

1. The deploy repo's name (`SYNTRA_VPS`) didn't match the subdomain (`syntra`).
2. The app needed a multi-container compose (postgres + api + web) with shared network topology.
3. The base image needed to swap Alpine → Debian-slim for build compatibility.
4. The MTU had to be fixed at the daemon level (not per-network).

Each of those is a class of deviation that will recur as more apps ship. This reference doc captures the working end state and the exact commands to recreate it, so the next deploy that hits any of these deviations can move faster.