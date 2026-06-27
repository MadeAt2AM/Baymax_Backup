# Baymax Backup — Full Restoration Guide

> **Generated:** 2026-06-27 12:00 AM SGT  
> **Last Updated:** 2026-06-27  
> **Backup Repo:** https://github.com/MadeAt2AM/Baymax_Backup

---

## Overview

This document is regenerated every 24 hours by a cron job and contains a complete snapshot of the current VPS environment. Follow it step-by-step to restore Baymax on a fresh VPS identical to this one.

---

## System Profile

| Property | Value |
|---|---|
| OS | Ubuntu 24.04 LTS (Noble) |
| Kernel | 6.8.0-117-generic |
| Architecture | x86_64 |
| User | root |
| Hostname | (check with `hostname`) |
| Timezone | Asia/Singapore (SGT, UTC+8) |
| UFW Firewall | Inactive |

---

## Installed System Packages (Key Items)

```bash
# Core runtime
python3.12          3.12.3-1ubuntu0.13
python3.12-dev     3.12.3-1ubuntu0.13
python3-venv       3.12.3-0ubuntu2.1
nodejs             v22.22.3
npm                10.9.8
git                1:2.43.0-1ubuntu7.3
gh                 2.45.0-1ubuntu0.3
curl               8.5.0-2ubuntu10.9
wget               1.21.4-1ubuntu4.1
jq                 1.7.1-3ubuntu0.24.04.2
ripgrep            14.1.0-1
tmux               3.4-1ubuntu0.1

# Python package managers
uv                 0.11.15 (x86_64-unknown-linux-gnu)

# Docker & containers
docker-ce           5:29.5.2-1~ubuntu.24.04~noble
docker-ce-cli      5:29.5.2-1~ubuntu.24.04~noble
containerd.io       2.2.3-1~ubuntu.24.04~noble
docker-buildx-plugin 0.34.0-1~ubuntu.24.04~noble
docker-compose-plugin 5.1.4-1~ubuntu.24.04~noble

# Web servers & certs
nginx              1.24.0-2ubuntu7.13
certbot            2.9.0-1
python3-certbot    2.9.0-1
python3-certbot-nginx 2.9.0-1

# Multimedia / rendering
ffmpeg             7:6.1.1-3ubuntu5

# Editors & tools
vim                2:9.1.0016-1ubuntu7.16
nano               7.2-2ubuntu0.2
htop               3.3.0-4build1
rsync              3.2.7-1ubuntu1.5

# Ubuntu Pro (active)
ubuntu-pro-client  37.2ubuntu~24.04
```

---

## Running Services (Systemd)

```bash
hermes-dashboard.service   ✅ running
hermes-gateway.service     ✅ running
docker.service             ✅ running
containerd.service         ✅ running
nginx.service              ✅ running
cron.service               ✅ running
ssh.service                ✅ running
systemd-resolved           ✅ running
fwupd.service              ✅ running
```

**All service definitions are stored in this repo at:**
```
.systemd/
```

---

## Listening Ports

| Port | Service |
|---|---|
| 22 | SSH |
| 53 | systemd-resolved |
| 80 | Nginx (HTTP) |
| 443 | Nginx (HTTPS) |
| 8080 | SearXNG |
| 8787 | Prometheus/node_exporter |
| 9100 | Prometheus metrics |
| 9119 | Unknown (check with `ss -tlnp`) |
| 127.0.0.1:9119 | localhost metrics |

---

## Docker Containers

```bash
# Active containers:
searxng            searxng/searxng:latest     Port 8080
searxng-redis      redis:7-alpine              Port 6379 (linked to searxng)

# Docker compose files:
.docker-compose/
```

---

## Hermes Configuration

### Config File
`/root/.hermes/config.yaml`

**Current model:** `MiniMax-M2.7` via `minimax` provider  
**Fallback providers:**
- `openrouter` (openrouter/owl-alpha, nvidia/nemotron-3-super-120b-a12b, z-ai/glm-5.1)
- `nvidia` (bytedance/seed-oss-36b-instruct, qwen/qwen3-coder-480b-a35b-instruct, stepfun-ai/step-3.5-flash)

**Toolsets enabled:** `hermes-cli`

**Personalities:** default, helpful, concise, technical, creative, teacher, kawaii, catgirl, pirate, shakespeare, surfer, noir

### Environment File
`/root/.hermes/.env`

**Secrets in this file (MUST RESTORE FIRST):**
```
TERMINAL_MODAL_IMAGE=nikolaik/python-nodejs:python3.11-nodejs20
TERMINAL_TIMEOUT=60
TERMINAL_LIFETIME_SECONDS=300
BROWSERBASE_PROXIES=true
BROWSERBASE_ADVANCED_STEALTH=false
BROWSER_SESSION_TIMEOUT=300
BROWSER_INACTIVITY_TIMEOUT=120
EMAIL_ADDRESS=baymax@madeat2am.in
EMAIL_PASSWORD=(***)
EMAIL_IMAP_HOST=mail.cyberslide.net
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=mail.cyberslide.net
EMAIL_SMTP_PORT=465
EMAIL_POLL_INTERVAL=10
EMAIL_ALLOWED_USERS=baymax@madeat2am.in
EMAIL_HOME_ADDRESS=baymax@madeat2am.in
WEB_TOOLS_DEBUG=false
VISION_TOOLS_DEBUG=false
MOA_TOOLS_DEBUG=false
IMAGE_TOOLS_DEBUG=false
GITHUB_TOKEN=(***) — GitHub PAT for MadeAt2AM org
MINIMAX_API_KEY=(***)
TELEGRAM_BOT_TOKEN=870087***o4HU
TELEGRAM_ALLOWED_USERS=1283992553
TELEGRAM_HOME_CHANNEL=-1003825565541
TELEGRAM_GATEWAY_NOTIFY_CHANNEL=-1003300736345
TELEGRAM_GATEWAY_NOTIFY_CHANNEL_NAME="Gateway Notifications"
OPENROUTER_API_KEY=(***)
NVIDIA_API_KEY=(***)
HONCHO_API_KEY=(***)
WIKI_PATH=/root/wiki
```

### Auth File
`/root/.hermes/auth.json` — credential pool for all providers

### Memory
`/root/.hermes/memories/` — persistent session memory (enabled)

### Skills Location
`/root/.hermes/skills/` — all skill definitions

### Plugins
`/root/.hermes/plugins/hermes-achievements/` — active plugin

### SOUL / Personality
`/root/.hermes/SOUL.md` — Baymax identity definition

---

## Project Directories

```
/root/projects/
├── CYBERSLIDE_Dokploy_Skill.md
├── 147-agents-video/
├── browser-search/           ← SearXNG + Docker
├── example_project/
├── hermes-skills-reel/
├── hermes-skills-reel-v2/
├── hf-mini-test/
├── madeat2am-brand/
├── secure-web-dashboard/
└── test-project/

/root/browser-search/         ← SearXNG deployment (git-tracked)
```

---

## Cron Jobs (Scheduled)

**Active:**
- Dreaming Sequence: 6 AM SGT daily (job_id: fab47f7704ba)
- Morning Brief: 8 AM SGT daily (job_id: afb02a1433cf)

**Cron configuration location:** `/root/.hermes/cron/`

---

## NPM / Node Setup

- Node.js: v22.22.3
- npm: 10.9.8
- Global node_modules: **empty** (no global packages installed)
- Hermes node modules: `/root/.hermes/node/` (857 MB — backed up)

---

## Python Environment

- Default Python: 3.12.3 (system)
- Hermes venv: `/root/.hermes/.venv/` (Python 3.12)
- UV managed pythons available: 3.11, 3.13, 3.14, 3.15

---

## Network / Firewall

- UFW: inactive
- Firewall managed via cloud provider security groups (VPS provider)
- No iptables rules set locally

---

## Installed CLI Tools (bin paths)

```bash
/usr/bin/gh                          GitHub CLI 2.45.0
/usr/local/bin/                      (custom installs)
/root/.local/bin/                    (custom installs)
/root/.hermes/bin/                   Hermes binary
```

---

## Directory Sizes (for reference)

| Path | Size | Notes |
|---|---|---|
| `/root/.hermes/node/` | 857 MB | Hermes node modules — backed up |
| `/root/.npm/` | 1.2 GB | NPM cache — NOT backed up |
| `/root/browser-search/node_modules/` | 17 MB | Backed up |
| `/root/.cache/` | varies | NOT backed up |
| `/root/.hermes/cache/` | varies | NOT backed up |
| `/root/.hermes/sessions/` | varies | NOT backed up |

---

## 🔧 STEP-BY-STEP RESTORATION PROCEDURE

### Phase 0 — Fresh VPS Requirements

- Ubuntu 24.04 LTS (fresh install)
- Root access
- Minimum 40 GB disk
- GitHub account with access to `MadeAt2AM/Baymax_Backup`

---

### Phase 1 — System Preparation

```bash
# 1. Update system
apt-get update && apt-get upgrade -y

# 2. Install core packages (if not already present)
apt-get install -y \
  python3.12 python3.12-dev python3.12-venv \
  python3-pip git curl wget jq ripgrep tmux \
  nginx certbot python3-certbot python3-certbot-nginx \
  docker.io docker-compose \
  ffmpeg vim nano htop rsync \
  ufw

# 3. Install gh CLI
apt-get install -y gh

# 4. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

---

### Phase 2 — Clone the Backup Repo

```bash
# Clone to /root (or your preferred location)
cd /root
git clone https://github.com/MadeAt2AM/Baymax_Backup.git .

# Or clone to a temp dir and move
git clone https://github.com/MadeAt2AM/Baymax_Backup.git /tmp/baymax_backup
rsync -av /tmp/baymax_backup/ /root/
```

---

### Phase 3 — Restore Secrets FIRST

```bash
# CRITICAL — restore .env before anything else
cp /root/baymax_backup/.env.placeholder /root/.hermes/.env
# Then edit with real values (or restore from the backed up .env file directly)
nano /root/.hermes/.env
# Paste the actual values from your backup .env file

# Restore auth.json
cp /root/baymax_backup/auth.json.placeholder /root/.hermes/auth.json
# Update with actual credentials

# Restore Google tokens (if used)
mkdir -p /root/.hermes/
cp /root/baymax_backup/google_token.json.placeholder /root/.hermes/google_token.json
cp /root/baymax_backup/google_client_secret.json.placeholder /root/.hermes/google_client_secret.json
```

> **Note:** The actual `.env` and `auth.json` files ARE included in this backup (not gitignored). Restore them from the repo directly if you have the real values pushed. If you prefer not to push real secrets, use the placeholder files and fill them in manually.

---

### Phase 4 — Python Environment

```bash
# Recreate Hermes virtual environment
cd /root/.hermes
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Install any custom packages (check requirements files)
# pip install -r requirements.txt  (if present in backup)
```

---

### Phase 5 — Restore Hermes Binary

```bash
# The hermes binary is at /root/.hermes/bin/
# Verify it's present
ls -la /root/.hermes/bin/hermes

# If missing, reinstall Hermes:
# curl -fsSL https://hermes-agent.nousresearch.com/install.sh | sh

# Make executable
chmod +x /root/.hermes/bin/hermes
```

---

### Phase 6 — Restore Projects

```bash
# Projects are at /root/projects/ and other root-level directories
# Verify:
ls -la /root/projects/
ls -la /root/browser-search/
ls -la /root/Obsidian-Vaults/

# Run npm install in any Node.js projects
cd /root/browser-search && npm install
```

---

### Phase 7 — Restore Skills

```bash
# Skills are at /root/.hermes/skills/
# All skills are git-tracked. Verify:
ls /root/.hermes/skills/
```

---

### Phase 8 — Restore Systemd Services

```bash
# Copy systemd service files
cp -r /root/.hermes/services/*.service /etc/systemd/system/
systemctl daemon-reload

# Enable services
systemctl enable hermes-gateway.service
systemctl enable hermes-dashboard.service
systemctl enable nginx
systemctl enable docker
```

---

### Phase 9 — Restore Docker Services

```bash
# Restore SearXNG
cd /root/browser-search
docker compose up -d
# or (older docker-compose syntax)
docker-compose up -d
```

---

### Phase 10 — Restore Nginx / Web Configs

```bash
# Nginx configs
cp /root/baymax_backup/nginx-conf/ /etc/nginx/ -r
nginx -t
systemctl reload nginx

# SSL certificates (if restored from backup)
# Or re-issue with certbot:
certbot --nginx -d yourdomain.com
```

---

### Phase 11 — Restore SSH Keys

```bash
# SSH keys are NOT in the repo (gitignored)
# If you need to restore them:
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# Copy from backup (if you backed them up separately)
# or generate new ones:
ssh-keygen -t ed25519 -C "baymax@your-vps"
```

---

### Phase 12 — Final Verification

```bash
# Restart services
systemctl restart hermes-gateway
systemctl restart hermes-dashboard
systemctl restart nginx
systemctl restart docker

# Check status
systemctl status hermes-gateway
systemctl status hermes-dashboard
ss -tlnp | grep -E ':(80|443|8080|22)\b'

# Verify Hermes is running
curl -s http://localhost:3000/health 2>/dev/null || \
curl -s http://localhost:8080/health 2>/dev/null || \
echo "Check hermes-gateway logs: journalctl -u hermes-gateway -n 50"
```

---

### Phase 13 — Schedule Daily Backup (Optional on new VPS)

```bash
# Install the backup cron (already set up on this VPS)
# See the baymax-backup skill for full cron setup
```

---

## What Gets Excluded (Safe to Regenerate)

| Excluded | Regeneration Method |
|---|---|
| `.hermes/.venv/` | `python3 -m venv .venv` |
| `.hermes/node/` | `npm install` in Hermes context |
| `.hermes/sessions/` | Auto-created on use |
| `.hermes/cache/` | Auto-created, Hermes rebuilds |
| `.npm/_cacache/` | `npm cache clean && npm install` |
| `.cache/` | Auto-created |
| `gateway.lock` | Auto-created |
| `*.pid` files | Auto-created |

---

## Critical Files to Never Lose

1. `/root/.hermes/.env` — all API keys, tokens, credentials
2. `/root/.hermes/auth.json` — credential pool
3. `/root/.hermes/config.yaml` — Hermes configuration
4. `/root/.hermes/kanban.db` — task state
5. `/root/.hermes/memories/` — persistent memory
6. `/root/.hermes/skills/` — all skill definitions

---

## Contact / Support

- **GitHub:** https://github.com/MadeAt2AM/Baymax_Backup
- **Primary Channel:** Telegram (configured in `.env`)
- **Owner:** Chris Vincent — CYBERSLIDE / MadeAt2Am

---

*This document is auto-generated daily. Last regenerated: 2026-06-27 00:00 SGT*
