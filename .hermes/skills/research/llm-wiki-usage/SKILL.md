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
- Script: `/root/.hermes/scripts/wiki-sync.sh` (background process `proc_918fc57514bf`)
- Listens for filesystem changes via `inotifywait` and auto-pushes to / pulls from GitHub
- Handles debouncing (5s) to avoid rapid-fire syncs
- Log: `/root/Obsidian-Vaults/.sync.log`

## Systemd Service (persistent across reboots)
```bash
systemctl --user daemon-reload
systemctl --user enable --now hermes-wiki-sync
sudo loginctl enable-linger $USER  # allow background service
```

## Orientation (MANDATORY at session start)
Read these files before ANY wiki operation:
```bash
WIKI=/root/Obsidian-Vaults/Hermes
cat $WIKI/SCHEMA.md
cat $WIKI/index.md
tail -20 $WIKI/log.md
```

## Daily Workflow
- **Add notes:** Save to `raw/articles/`, `entities/`, `concepts/`, etc.
- **Update index.md** when adding pages
- **Append log.md** for every action
- **Cross-link** with `[[wikilinks]]` (min 2 per page)

## Git Operations
```bash
cd /root/Obsidian-Vaults
git status           # check sync status
git log --oneline    # recent changes
# Push/pull is automatic via sync daemon
```

## Wiki Structure
```
Hermes/
├── SCHEMA.md        # Conventions, tag taxonomy
├── index.md         # Content catalog
├── log.md           # Action log (append-only)
├── raw/             # Layer 1: immutable sources
│   ├── articles/
│   ├── papers/
│   ├── transcripts/
│   └── assets/
├── entities/        # Layer 2: people, companies, products
├── concepts/        # Layer 2: topics, techniques
├── comparisons/     # Layer 2: side-by-side analyses
├── queries/         # Layer 2: filed Q&A results
├── _archive/        # Superseded pages
└── _meta/           # Topic maps, helper files
```

## Schema Domain
Covers: tech infrastructure, devops, AI/ML, brand management, social media content, web development, productivity, CYBERSLIDE projects.

## Tags (from SCHEMA.md)
- Tech: `infrastructure`, `devops`, `ai-ml`, `tools`, `automation`
- Business: `brand`, `product`, `growth`, `social-media`
- Personal: `productivity`, `workflow`, `learning`
- Projects: `cyberslide`, `web-apps`, `content`
- Meta: `comparison`, `timeline`, `decision`, `archived`

## Notes
- Raw sources are immutable — corrections go in wiki pages, not raw/
- Debounce prevents rapid syncs (5s window)
- Sync daemon started at PID 242384 — check it's running before assuming auto-sync works