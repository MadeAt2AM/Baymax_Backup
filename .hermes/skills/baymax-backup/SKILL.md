---
name: baymax-backup
description: Backs up /root (full Hermes state) to GitHub repo MadeAt2AM/Baymax_Backup, analyses environment, updates RESTORATION_GUIDE.md. Run manually or via daily cron at 00:00 SGT.
category: devops
---

# Baymax Backup Skill

Backs up the entire `/root` directory to the private GitHub repo `MadeAt2AM/Baymax_Backup`, runs an environment analysis, and updates the `RESTORATION_GUIDE.md` document.

## What it does

1. **Authenticates** `gh` CLI using `GITHUB_TOKEN` from `/root/.hermes/.env`
2. **Git add** on all files in `/root/baymax_backup` (which mirrors `/root`)
3. **Analyses the environment** — packages, ports, Docker, Hermes config, npm/node versions, cron jobs
4. **Updates** `RESTORATION_GUIDE.md` with fresh analysis
5. **Commits and pushes** to `MadeAt2AM/Baymax_Backup` on branch `main`

## Files

| File | Purpose |
|------|---------|
| `/root/baymax_backup/backup.sh` | The backup script (also callable directly) |
| `/root/baymax_backup/.gitignore` | Excludes caches, node_modules, .venv, etc. |
| `/root/baymax_backup/RESTORATION_GUIDE.md` | Live restoration manual |
| `/root/baymax_backup/backup_data/` | Copied backup of `.env`, `config.yaml`, `auth.json`, skills, memories, projects |

## Run manually

```bash
bash /root/baymax_backup/backup.sh
```

## Cron schedule

Daily at **00:00 SGT (UTC-8) / 16:00 UTC previous day**

Check existing cron:
```bash
cronjob action=list
```

## What is backed up (included in GitHub)

- `/root/.hermes/.env` — all API tokens and secrets
- `/root/.hermes/config.yaml` — full Hermes configuration
- `/root/.hermes/auth.json` — credential pool
- `/root/.hermes/kanban.db` — task/kanban state
- `/root/.hermes/skills/` — all skill definitions
- `/root/.hermes/memories/` — persistent memory store
- `/root/.hermes/projects/` — all projects
- `/root/.hermes/plugins/` — plugin configs
- `/root/.hermes/scripts/` — custom scripts
- `/root/browser-search/` — SearXNG config
- `/root/Obsidian-Vaults/` — LLM Wiki
- `/root/projects/` — all root-level projects
- Systemd services, nginx configs, Docker compose files

## What is NOT backed up (too large / machine-specific)

- `.hermes/cache/`, `.hermes/audio_cache/`, `.hermes/image_cache/`
- `.hermes/.venv/` (rebuilt via pip/uv on restore)
- `.hermes/node/` (857 MB — npm packages rebuilt on restore)
- `.npm/` (1.2 GB — npm cache)
- `.cache/` (browser profiles, typescript, pip, mesa shaders)
- `.camofox/`, `.camoufox/`, `.cloakbrowser/`
- `.docker/buildx/`, `.hyperframes/`
- `gateway.lock`, `gateway.pid`, `state.db-wal`, `processes.json`
- `.ssh/` private keys

## Verification

After running, confirm push succeeded:
```bash
gh run list --repo MadeAt2AM/Baymax_Backup 2>/dev/null || true
git -C /root/baymax_backup log -1 --oneline
```

## Restore on new VPS

1. Clone repo: `git clone https://github.com/MadeAt2AM/Baymax_Backup.git /root`
2. Follow `RESTORATION_GUIDE.md` step-by-step
3. Restore secrets: `cp backup_data/.env.restore /root/.hermes/.env`
4. Run setup: `bash /root/baymax_backup/first_restore.sh`

## Troubleshooting

**gh not authenticated:** Run `gh auth login --with-token` with a GitHub PAT that has `repo` scope for `MadeAt2AM` org.

**Push fails:** Check `gh auth status` and ensure the token has `Contents: Read & Write` on `MadeAt2AM/Baymax_Backup`.

**Empty push (no changes):** Normal — no new changes since last backup. Exit code 0, nothing to do.
