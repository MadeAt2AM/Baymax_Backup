---
name: llm-wiki-usage
description: "Use the CYBERSLIDE LLM Wiki at /root/Obsidian-Vaults/Hermes — read, write, query, and maintain it. Sync daemon runs via /root/.hermes/scripts/wiki-sync.sh"
version: 1.0.0
author: Baymax
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [wiki, knowledge-base, cyberslide]
    category: research
    domain: /root/Obsidian-Vaults/Hermes
---

# Using the CYBERSLIDE LLM Wiki

## Location
`/root/Obsidian-Vaults/Hermes/` — the wiki directory that syncs bidirectionally with GitHub.

## Sync Daemon
- Script: `/root/.hermes/scripts/wiki-sync.sh`
- Listens for filesystem changes via `inotifywait` and auto-commits + pushes to / pulls from GitHub
- Handles debouncing (5s) to avoid rapid-fire syncs
- Log: `/root/Obsidian-Vaults/.sync.log`

### Production Supervision (systemd)
The daemon is managed by systemd as a **system service** (NOT `--user`):
- Service file: `/etc/systemd/system/hermes-wiki-sync.service` (source: `references/hermes-wiki-sync.service` in this skill)
- Service name: `hermes-wiki-sync.service`
- Auto-starts on boot (enabled)
- Auto-restarts on crash (Restart=always, 10s delay)

```bash
# Check if daemon is alive
sudo systemctl is-active hermes-wiki-sync.service

# Check all instances of inotifywait watching the vault (there should be exactly 1)
ps aux | grep 'inotifywait.*Hermes' | grep -v grep

# Restart if dead
sudo systemctl restart hermes-wiki-sync.service

# View sync log
tail -20 /root/Obsidian-Vaults/.sync.log
```

### Cron Health-Check (second layer)
A cron job runs every 15 minutes as a safety net:
- Job ID: `59cc5538d6a5`
- Script: `/root/.hermes/scripts/check-wiki-sync.sh`
- Checks if the systemd service is alive; restarts it if not
- Completely silent unless something breaks

### Repo Details
- Remote: `https://github.com/MadeAt2AM/Obsidian-Vaults`
- Vault subdirectory: `Hermes/` within that repo
- Git identity for wiki commits: configured via `gh auth setup-git` (uses `chrisvincodes` account)
- **The vault can drift behind remote** — always check `git status` and `git log --oneline origin/main` before assuming local is current

## Tags (from SCHEMA.md)
The original script ran `git add -A` but never committed — the push logic checked `git rev-parse @` (HEAD) vs `origin/main` but HEAD never advanced because nothing was committed. The production script now includes an explicit `git commit` step before the push/fetch/merge logic. If the script is ever replaced, ensure it commits after `git add -A`.

## Orientation (MANDATORY at session start)
Read these files before ANY wiki operation:
```bash
WIKI=/root/Obsidian-Vaults/Hermes
cat $WIKI/SCHEMA.md
cat $WIKI/index.md
tail -20 $WIKI/log.md
```

## Daily Activities Log
- Location: `daily_activities_log/YYYY-MM-DD.md`
- Format: date-coded entries with sections — **What was done**, **Decisions made**, **Blockers / open items**, **Notes for tomorrow**
- Append new entries via `/root/.hermes/scripts/append-to-vault.sh daily "done" "decisions" "blockers" "notes"`
- End-of-day auto-generation: cron job `894a7027fd80` runs at 14:00 UTC daily (22:00 SGT), executes `/root/.hermes/scripts/daily-log-generator.sh`, delivers a summary to Telegram

## Research Log
- Location: `research_log/YYYY-MM-DD-TOPIC.md`
- Created after every research task — web searches, code investigations, skill authoring
- Sections: **Question**, **Sources consulted**, **Key findings**, **Verdict / next action**
- Append via `/root/.hermes/scripts/append-to-vault.sh research "topic" "question" "sources" "findings" "verdict"`
- Always provenance-mark claims with `^[source]`

## Vault Log Scripts
- `/root/.hermes/scripts/append-to-vault.sh` — append daily or research log entries
  - Daily: `append-to-vault.sh daily "done" "decisions" "blockers" "notes"`
  - Research: `append-to-vault.sh research "topic" "question" "sources" "findings" "verdict"`
  - Uses Python for safe multi-section in-place file editing (handles YAML frontmatter correctly)
- `/root/.hermes/scripts/daily-log-generator.sh` — end-of-day auto-logger (called by cron)

## Wiki Structure
```
Hermes/
├── SCHEMA.md              # Conventions, tag taxonomy, daily/research log policy
├── index.md              # Content catalog
├── log.md                # Action log (append-only)
├── daily_activities_log/ # Date-coded daily summaries
├── research_log/         # Research task records
├── raw/                  # Layer 1: immutable sources
│   ├── articles/
│   ├── papers/
│   ├── transcripts/
│   └── assets/
├── entities/             # Layer 2: people, companies, products
├── concepts/             # Layer 2: topics, techniques
├── comparisons/          # Layer 2: side-by-side analyses
├── queries/              # Layer 2: filed Q&A results
├── _archive/             # Superseded pages
└── _meta/                # Topic maps, helper files
```

### Repo Details
- Remote: `https://github.com/MadeAt2AM/Obsidian-Vaults`
- Vault lives at: `Hermes/` subdirectory within that repo
- **The vault CAN drift behind remote** — always check `git status` and `git log --oneline origin/main` before assuming local is current

### Production Supervision (systemd)
The daemon is managed by systemd as a **system service** (NOT `--user`):
- Service file: `/etc/systemd/system/hermes-wiki-sync.service`
- Service name: `hermes-wiki-sync.service`
- Auto-starts on boot (enabled)
- Auto-restarts on crash (Restart=always, 10s delay)

**Pitfall — ProtectHome=true blocks the working directory:**
`ProtectHome=true` in the service file causes systemd to deny access to `/root/`, making `WorkingDirectory=/root/Obsidian-Vaults` fail with `CHDIR` exit code 200. Use `ProtectHome=read-only` + `ReadWritePaths=/root/Obsidian-Vaults` instead.

**Pitfall — stale inotifywait orphans:**
If the daemon crashes uncleanly, a stray `inotifywait` process can keep running. `pgrep -f 'inotifywait.*Hermes'` will show 2 instances. Kill the older one (lower PID = older = orphan).

```bash
# Check if daemon is alive
sudo systemctl is-active hermes-wiki-sync.service

# Check all instances — should be exactly 1
ps aux | grep 'inotifywait.*Hermes' | grep -v grep

# Restart if dead
sudo systemctl restart hermes-wiki-sync.service

# View sync log
tail -20 /root/Obsidian-Vaults/.sync.log
```

### Cron Health-Check (second layer)
A cron job runs every 15 minutes as a safety net:
- Job ID: `59cc5538d6a5`
- Script: `/root/.hermes/scripts/check-wiki-sync.sh`
- Checks if the systemd service is alive; restarts it if not — completely silent unless something breaks

### End-of-Day Cron (third layer)
- Job ID: `894a7027fd80` — runs at 14:00 UTC daily (22:00 SGT)
- Script: `/root/.hermes/scripts/daily-log-generator.sh`
- Generates daily log entry, pushes to GitHub, delivers Telegram summary

### Morning Sync Check (fourth layer)
- Job ID: `44cd86c70264` — runs at 23:55 SGT daily (before Dreaming Sequence)
- Verifies sync daemon health before the night cycle begins — silent unless daemon is down

### Pitfall: wiki-sync.sh must COMMIT before push
The original script ran `git add -A` but never committed — the push logic checked `git rev-parse @` (HEAD) vs `origin/main` but HEAD never advanced because nothing was committed. The production script now includes an explicit `git commit` step before the push/fetch/merge logic. If the script is ever replaced, ensure it commits after `git add -A`.

## Git Operations
```bash
cd /root/Obsidian-Vaults
git status           # check sync status
git log --oneline    # recent changes
# Push/pull is automatic via sync daemon — manual intervention only needed if divergence occurs
```

## Schema Domain
Covers: tech infrastructure, devops, AI/ML, brand management, social media content, web development, productivity, CYBERSLIDE projects.

## Tags (from SCHEMA.md)
- Tech: `infrastructure`, `devops`, `ai-ml`, `tools`, `automation`
- Business: `brand`, `product`, `growth`, `social-media`
- Personal: `productivity`, `workflow`, `learning`
- Projects: `cyberslide`, `web-apps`, `content`
- Meta: `comparison`, `timeline`, `decision`, `archived`

### Diagnosing Sync State
```bash
cd /root/Obsidian-Vaults/Hermes

# Are we ahead, behind, or diverged?
git status

# Local vs remote — how far behind?
git log --oneline HEAD..origin/main
git log --oneline origin/main..HEAD

# Last sync activity
tail -20 /root/Obsidian-Vaults/.sync.log
```