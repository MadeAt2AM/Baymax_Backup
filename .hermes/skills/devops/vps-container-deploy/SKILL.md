---
name: vps-container-deploy
description: Deploy containerised apps to a remote Docker host with per-subdomain DNS and auto-TLS. Use when you need to point a new subdomain (such as app.yourdomain.com) at a fresh app running on a separate VPS — DNS via Cloudflare API, reverse proxy via Caddy in Docker, one project per directory. Trigger on phrases like "deploy app on remote VPS", "create new subdomain", "spin up Docker app on different server", "point hostname to container", "hello-world deploy", "Caddy auto TLS", "let's encrypt on Caddy", "Cloudflare DNS API for A record".
category: devops
version: 1.0.0
---

# Remote Container Deploy with Per-Subdomain DNS

## Overview

Class of work: spin up a brand-new containerised app on a remote VPS, point a fresh subdomain at it, get a real Let's Encrypt cert automatically, and verify it works end-to-end. Targets the exact shape we built this session — a **control plane VPS** that drives deploys, a **dev VPS** that runs Docker, and a **Cloudflare zone** for DNS.

When to reach for this skill:
- "Deploy X on the dev VPS as `x.terrybot.top`"
- "Set up the next app behind a subdomain"
- "Spin up a hello-world on the new VPS"
- Any task that combines `domain → DNS → container → reverse proxy → HTTPS` on a remote host

## Architecture (what we built)

```
┌─────────────────────────────────────────────────────────────┐
│ CONTROL VPS (cyberslide / 147.79.18.59)                     │
│   ~/.hermes/bin/                                             │
│     ├── cf-dns.sh    DNS add/del/list/get via CF API        │
│     ├── deploy.sh    ONE-shot new project deploy            │
│     └── teardown.sh  Remove a deployment                    │
└─────────────────────────────────────────────────────────────┘
                          │ SSH (key-only, NOPASSWD sudo)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ DEV VPS (147.79.18.32)                                       │
│   /srv/caddy/         Caddy stack (80/443, auto-TLS)        │
│     └── sites/<x>.caddy  per-project route block            │
│   /srv/projects/<x>/   per-project docker compose stack      │
└─────────────────────────────────────────────────────────────┘
                          ▲ DNS API (HTTPS)
┌─────────────────────────────────────────────────────────────┐
│ Cloudflare zone (terrybot.top)                              │
│   existing A records PRESERVED — only add/del as needed      │
└─────────────────────────────────────────────────────────────┘
```

## When to Use This Skill vs `secure-web-dashboard`

| Use this skill when... | Use `secure-web-dashboard` instead when... |
|---|---|
| Brand-new app, fresh subdomain | Existing local app to expose |
| Multi-app, one-per-subdomain | Single host to single subdomain |
| Containers on a remote Docker host | Local 9119 dashboard on the same host |
| Caddy in Docker as shared reverse proxy | Nginx (or Caddy) for a single service |
| Want on-demand TLS as new subdomains spin up | One-time cert with Certbot |

## Prerequisites (must be true before this skill applies)

| Requirement | How to verify |
|---|---|
| Docker host with `docker compose` plugin | `docker compose version` reports v2+ |
| SSH key auth from control to dev VPS, NOPASSWD sudo | `ssh deploy@dev-vps "sudo -n whoami"` prints `root` |
| Cloudflare API token with Zone DNS Edit on the target zone | `curl -s -H "Authorization: Bearer $TOK" https://api.cloudflare.com/client/v4/zones?name=$ZONE` |
| Cloudflare Zone ID | Same call returns `result[].id` |
| The target domain must already be added as a Cloudflare zone | DNS lookups resolve for existing records |
| Disk on dev VPS at least 10GB free | `df -h /` — Docker images fill small disks fast. Resize at provider or migrate to a larger volume. |
| Ports 80 + 443 open on dev VPS | `curl http://dev-vps/` should reach the reverse proxy |

## Procedure (one-shot deploy)

Use the helper scripts in `~/.hermes/bin/` on the control VPS. They live at:

- `cf-dns.sh` — Cloudflare DNS CRUD
- `deploy.sh` — full one-shot deploy (calls cf-dns plus SSH to dev VPS)
- `teardown.sh` — reverse a deploy

### 1. `cf-dns.sh <verb> <subdomain> [ip]`

```bash
~/.hermes/bin/cf-dns.sh add my-app               # → my-app.terrybot.top → VPS_IP (default)
~/.hermes/bin/cf-dns.sh add my-app 1.2.3.4        # override IP
~/.hermes/bin/cf-dns.sh del my-app                # remove
~/.hermes/bin/cf-dns.sh list                      # all A records
~/.hermes/bin/cf-dns.sh get my-app                # JSON detail
```

The script reads `CF_API_TOKEN`, `CF_ZONE_ID`, `CF_DOMAIN` from `~/.hermes/.env`. Behaviour notes:

- **`add` is idempotent** — if the record exists, it reports and exits 0 rather than failing
- **`proxied` is always `false` (DNS-only / grey-cloud)** — matches the user's policy. Flip the JSON body in the script if you want orange-cloud for a specific record
- Default IP is hardcoded; either set in script or pass as 2nd arg
- The script lives at `~/.hermes/bin/cf-dns.sh` — copy it to any control host and source its env approach

### 2. `deploy.sh <project-name> [port]`

```bash
~/.hermes/bin/deploy.sh my-app 8080
```

**What it does, in order:**
1. `cf-dns.sh add <project>` — A record
2. SSH to dev VPS, mkdir `/srv/projects/<name>`
3. If `docker-compose.yml` missing, scaffold `Dockerfile` + `app.py` + `docker-compose.yml`
4. SSH to dev VPS, `docker compose up -d --build`
5. SSH to dev VPS, write `/srv/caddy/sites/<name>.caddy` route, `docker exec caddy caddy reload`
6. Poll `https://<name>.<domain>` for HTTP 200 (cert provisioning can take 30 to 60s on first deploy)

**Idempotency guarantees:**
- DNS: cf-dns `add` checks for existing
- Files: scaffold only runs if no `docker-compose.yml`
- Caddy site: file written verbatim every time (last write wins)
- Container: `docker compose up -d --build` is naturally idempotent

**Cost on the wire per deploy:** about 10 SSH round-trips, one DNS API call, one Caddy reload, one cert provisioning event.

### 3. `teardown.sh <project-name>`

```bash
~/.hermes/bin/teardown.sh my-app
```

Reverse — preserves project files (won't rm `/srv/projects/<name>`) so you can inspect logs. Manual `rm -rf` if you want them gone.

## Pitfalls and Debugging

### A. Caddy — `auto_https on` is invalid syntax

Caddy v2 rejects `auto_https on` with this error:

```
Error: adapting config using caddyfile: parsing caddyfile tokens for 'auto_https':
auto_https must be one of 'off', 'disable_redirects', 'disable_certs', or 'ignore_loaded_certs'
```

`auto_https` is **on by default**. If you want to disable cert issuance for a specific site, use `auto_https off` at the site block level, NOT the global options. **Drop the directive entirely from global options** — it produces silent restart loops.

### B. Caddy site glob empty means Caddy resets every HTTP request

If `import /etc/caddy/sites/*.caddy` matches zero files, Caddy has no site blocks, and every HTTP request gets `Connection reset by peer`. Tests:

```bash
ls /srv/caddy/sites/                  # must have one or more .caddy files
docker logs caddy 2>&1 | grep -i error  # clear logs = config OK
```

This will surface as `curl: (35) Recv failure: Connection reset by peer` when testing before any site block is added. Add a placeholder file and reload to test the pipeline.

### C. Caddy requires socket restart after sshd style config changes

`systemctl reload caddy` reloads the **service**, but on Ubuntu 24.04 socket-activated services, you also need:

```bash
systemctl restart caddy.socket
sleep 1
```

before config changes propagate to a freshly spawned listener. Symptoms: new config in file but old config in effect.

### D. Cloud-init drop-in re-enables password auth on Ubuntu cloud images

Ubuntu cloud images ship `/etc/ssh/sshd_config.d/50-cloud-init.conf` containing `PasswordAuthentication yes`. The main config often has `Include /etc/ssh/sshd_config.d/*.conf` — drop-ins sort alphabetically, so `50-*` beats `60-cloudimg-settings.conf`. **Always check both files** when hardening SSH:

```bash
ls /etc/ssh/sshd_config.d/
cat /etc/ssh/sshd_config.d/*.conf
sshd -T | grep -E "^(passwordauthentication|permitrootlogin)"
```

The `sshd -T` (live config) is the source of truth for what the running daemon is using — not the file content.

### E. Disk-too-small detection on fresh VPS

A fresh VPS often ships with a tiny root volume (we saw 3.5GB). Installing Docker plus first image pull fails with `no space left on device`. **Detect before installing:**

```bash
df -h / | awk 'NR==2 {print $4}'    # free space
```

Threshold: at least 10GB free before installing Docker. If smaller:
1. Grow the underlying disk in the provider panel
2. From the dev VPS: `growpart /dev/sda 1 && resize2fs /dev/sda 1` — no reboot, takes seconds
3. Then proceed with Docker install

See [references/online-partition-resize.md](references/online-partition-resize.md) for the full procedure.

### F. Cloudflare MCP server requires OAuth browser flow

`https://mcp.cloudflare.com/mcp` returns HTTP 401 unless you go through the OAuth dance in a browser (a `curl GET` returns a real `www-authenticate: Bearer realm="OAuth"` challenge). **Skip it — use `cf-dns.sh`** for DNS operations. The OAuth flow needs interactive browser context we don't have from CLI/gateway sessions. The script covers all operations we'd use the MCP for — create, delete, list A records.

### G. SSH to dev VPS — deploy.sh runs locally, NOT on dev VPS

`deploy.sh` lives on the **control** VPS (cyberslide). It uses SSH to invoke Docker on the dev VPS. Do NOT run it from the dev VPS itself — the `web` Docker network exists on dev VPS but not on control. **Confirm you're on the control plane** by checking the hostname before invoking. Common mistake: SSH'd to dev VPS, then ran the deploy. It fails with `network web declared as external, but could not be found`.

### H. Let's Encrypt cert provisioning takes 30 to 60s on first hit

`deploy.sh` polls for HTTPS 200 with a 90s budget — sufficient for normal ACME flow. If you're debugging post-deploy and curl returns `HTTP 000` or a cert error, the cert likely isn't issued yet. Check:

```bash
docker logs caddy 2>&1 | grep -iE 'acme|certificate|cert'
```

Look for `ACME account... registering with ACME server` and `certificate obtained successfully` events.

## Maintenance

| Task | Command |
|---|---|
| List deployed apps | `cf-dns.sh list` plus `ls /srv/projects/` on dev VPS |
| Check a project's logs | `ssh dev-vps "docker logs <project>-app"` |
| Rebuild after code change | Edit `/srv/projects/<name>/` then `ssh dev-vps "cd /srv/projects/<name> && docker compose up -d --build"` |
| Add a new subdomain, no container | `cf-dns.sh add foo` — Caddy won't serve anything until you also write a site block |
| Force Caddy to re-scan | `ssh dev-vps "docker exec caddy caddy reload --config /etc/caddy/Caddyfile"` |
| Disk on dev VPS | `ssh dev-vps "df -h /"` — alert if under 10% free |

## References

- [Caddy pitfalls — config that breaks silently](references/caddy-pitfalls.md)
- [Cloudflare DNS utility — behaviour notes, edge cases](references/cf-dns-utility.md)
- [Online partition resize — when fresh VPS disk is too small](references/online-partition-resize.md)
- [Hardening SSH on Ubuntu 24.04 cloud images](references/ubuntu-ssh-hardening.md)

## Scripts (templates)

Copy these to `~/.hermes/bin/` when bootstrapping a new control VPS:

- [templates/cf-dns.sh](templates/cf-dns.sh) — Cloudflare DNS CRUD
- [templates/deploy.sh](templates/deploy.sh) — one-shot deploy
- [templates/teardown.sh](templates/teardown.sh) — reverse a deploy
- [templates/Caddyfile](templates/Caddyfile) — global Caddy config (imports per-site files)
- [templates/caddy-docker-compose.yml](templates/caddy-docker-compose.yml) — the Caddy stack

## Attribution

Built from a real session in July 2026 — bootstrapped a dev VPS from scratch, hit the small-disk / cloud-init-password / Caddy-auto-https-trap walls, recovered from each, shipped a working `https://<app>.terrybot.top` with a real Let's Encrypt cert on the first try after the fixes.
