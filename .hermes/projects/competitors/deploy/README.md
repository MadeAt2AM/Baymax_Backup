# Competitors Intelligence — deployment

This directory holds the **production-shape** deployment:

- `docker-compose.yml` — Postgres + API + Web + Whisper worker
- `Caddyfile` — host-level reverse proxy for `competitors.terrybot.top`
- `.env.example` — environment variables template
- `deploy.sh` — one-shot deploy script
- `cloudflare.tfvars.example` — Cloudflare DNS records

## One-shot deploy

```bash
# 1. Copy the env file and fill in real values.
cp deploy/.env.example deploy/.env
$EDITOR deploy/.env

# 2. Bootstrap the dev VPS toolchain (one-time).
bash scripts/setup_dev_vps.sh

# 3. Bootstrap the OpenCLI session (one-time, interactive).
bash scripts/bootstrap_dev_session.sh

# 4. Deploy.
bash deploy/deploy.sh
```

## What the deploy does

1. **Builds** the API image and the Web image.
2. **Starts** Postgres; waits for it to be healthy.
3. **Starts** the API and the Web containers.
4. **Runs** Alembic migrations (`alembic upgrade head`).
5. **Reloads** the host Caddy to pick up the Caddyfile.
6. **Smoke-tests** the deployment by hitting `/api/healthz` over the public URL.

## Persistent directories on the dev VPS

- `/srv/competitors-private/postgres/` — Postgres data (mounted into the container).
- `/srv/competitors-private/opencli-profile/` — OpenCLI site-session (mode 0700).
- `/srv/competitors-private/audio/` — downloaded Instagram reels (input for the Whisper worker).
- `/srv/competitors-private/bundles/` — publish bundles (output; ingested by the API importer).

These are created into Docker volumes by the compose file. The host bind-mounts in the deploy are optional.

## Topologies

| Service | Where | Why |
|---------|-------|-----|
| Postgres | dev VPS (container) | Single source of truth for the dashboard. |
| API | dev VPS (container) | Reverse-proxied by Caddy. |
| Web | dev VPS (container) | Static Vite bundle served by Caddy. |
| Whisper worker | dev VPS (container, profile=transcription) | Runs in the same container image as the API; profile-gated so it doesn't run by default. |
| Faster-Whisper model | dev VPS (CPU, tiny model) | 446 ms / 1 s audio. Models cached in `/root/.cache/huggingface/`. |
| OpenCLI | dev VPS (host, /usr/bin/opencli) | The host binary is mounted into the container. |
| Hermes host | orchestrator only | Triggers pipeline runs via cron + the API. |

## DNS

`competitors.terrybot.top` is an A record proxied through Cloudflare to `147.79.18.32`. Cloudflare terminates TLS on the edge; Caddy handles TLS for the origin host.

## Smoke test

After `deploy.sh`, the API responds at:

```
$ curl -fsS https://competitors.terrybot.top/api/healthz
{"status":"ok","version":"0.1.0",...}
```

If the dashboard login page renders at `https://competitors.terrybot.top/`, the deployment is healthy.
