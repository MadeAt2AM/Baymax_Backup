# Competitors Intelligence Dashboard - Project Index

## Project Overview

- **Name:** Competitors Intelligence Dashboard
- **Project Root:** `/root/.hermes/projects/competitors/`
- **Target URL:** `https://competitors.terrybot.top`
- **Dev VPS:** `147.79.18.32` (Hermes host)
- **Docker Network:** `web` (MTU 1400)
- **Primary Language:** Python 3.12, Node 20+, React/TypeScript, FastAPI
- **Primary Framework:** Hermes Agent (self-hosted), OpenCLI Instagram method, Faster-Whisper, FFmpeg, FastAPI, React, Vite
- **Status:** Planning complete, preflight verified, scaffold pending.

## Project Directory Structure

```
/root/.hermes/projects/competitors/
├── .gitignore
├── .env.example
├── .hermes.md
├── PROJECT_INDEX.md
├── README.md
├── 00-README.md
├── ANALYZE.md
├── DASHBOARD-SPEC.md
├── competitor-accounts.md
├── scrape.py
├── pyproject.toml
├── config/
│   └── project.yaml
├── docs/
│   ├── upstream-gist/
│   │   ├── 00-README.md
│   │   ├── ANALYZE.md
│   │   ├── DASHBOARD-SPEC.md
│   │   ├── competitor-accounts.md
│   │   ├── scrape.py
│   │   ├── SOURCE.md
│   │   ├── SHA256SUMS
│   │   ├── architecture.md
│   │   ├── data-retention.md
│   │   ├── deployment.md
│   │   ├── runbook.md
│   │   └── IMPLEMENTATION_PLAN.md
│   └── implementation_plan.md
├── pipeline/
│   ├── __init__.py
│   ├── accounts.py
│   ├── opencli_instagram.py
│   ├── media.py
│   ├── whisper_transcriber.py
│   ├── ledger.py
│   ├── models.py
│   ├── notes.py
│   ├── collector.py
│   └── cli.py
├── scripts/
│   ├── validate_analysis.py
│   ├── build_publish_bundle.py
│   ├── publish_bundle.sh
│   ├── cleanup_working_videos.py
│   ├── validate_local.sh
│   └── validate_live.sh
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── auth.py
│   │   │   ├── importer.py
│   │   │   └── routes/
│   │   │       ├── health.py
│   │   │       ├── auth.py
│   │   │       ├── dashboard.py
│   │   │       ├── reels.py
│   │   │       └── runs.py
│   │   ├── alembic/
│   │   └── tests/
│   └── web/
│       ├── package.json
│       ├── vite.config.ts
│       ├── nginx.conf
│       ├── src/
│       │   ├── app/
│       │   │   ├── components/
│       │   │   ├── pages/
│       │   │   ├── api/
│       │   │   ├── styles/
│       │   │   └── test/
│       │   └── e2e/
│       └── package-lock.json
├── deploy/
│   ├── docker-compose.yml
│   ├── docker-compose.test.yml
│   ├── Dockerfile.api
│   ├── Dockerfile.migrate
│   ├── Dockerfile.web
│   ├── Dockerfile.scraper
│   ├── Dockerfile.whisper
│   ├── competitors_dev.sh
│   ├── competitors.caddy
│   └── webhook-hook.json
├── tests/
│   ├── fixtures/
│   ├── test_accounts.py
│   ├── test_collector.py
│   ├── test_ledger.py
│   ├── test_models.py
│   ├── test_notes.py
│   └── test_publish_bundle.py
├── data/
│   ├── staging/
│   ├── notes/
│   ├── exports/
│   └── ledger.json
└── .hermes/
    └── skills/
        └── competitor-intelligence/
            ├── SKILL.md
            └── references/
                ├── analysis-contract.md
                └── operator-runbook.md