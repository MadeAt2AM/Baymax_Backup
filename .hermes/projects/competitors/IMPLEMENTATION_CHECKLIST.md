# Competitors Intelligence Dashboard Implementation Checklist

## Progress State
- **Current phase:** Phase 7 (deployment) — DP-001 through DP-015 complete; DP-016..023 awaiting dev-VPS operations
- **Current task:** DP-016 (build API image on dev VPS)
- **Last completed task:** All Phase 7 deployment assets written (Dockerfiles, docker-compose, Caddyfile, .env.example, deploy.sh, alembic migration, .dockerignore, GitHub Actions workflow)
- **Blocked task:** None
- **Next task:** DP-016 — build images on the dev VPS
- **Last updated:** 2026-07-25 09:42 SGT
- **Implementation status:** All Phase 7 deployment assets are written. The Docker daemon on the Hermes host has been fixed with `mtu: 1400` in `/etc/docker/daemon.json` to match the Hetzner host MTU. The `competitors-net` Docker network has `driver_opts com.docker.network.driver.mtu: 1400`. The alembic initial migration runs cleanly. **Total tests: 112 (101 Python + 11 frontend), all pass.** Pending dev-VPS ops: DP-016..023 (build + up + migrate + Caddy + Cloudflare + smoke test).

## Completed Preflight Tasks
- [x] **P-002** Checked local tool versions and availability (Python 3.11.15, Node 22.22.3, OpenCLI 1.8.5, etc.).
- [x] **P-003** Verified Hermes status and active profile (Hermes v0.19.0, default profile, MiniMax-M3/minimax).
- [x] **P-004** Confirmed read‑only GitHub authentication and token scope.
- [x] **P-005** Verified `dev-vps` SSH identity and host key.
- [x] **P-006** Inspected dev‑VPS host resources (4 vCPU AMD Ryzen 5 5600, 7.8 GiB RAM, 50 GiB free disk, no GPU).
- [x] **P-007** Inspected Docker and network infrastructure (bridge `web` MTU 1400, running `payntra-app`, no `caddy` container).
- [x] **P-008** Inspected webhook and script environment (no webhook units or tokens present).
- [x] **P-009** Inspected Cloudflare DNS (domain returns NXDOMAIN, no `.cf-env` file).
- [x] **P-010** Inspected Hermes-VPS OpenCLI Instagram method (OpenCLI 1.8.5 installed, `whoami` blocked due to unconnected browser extension, no session data printed).
- [x] **P-012** Inspected local Faster-Whisper readiness (packages available, FFmpeg/ffprobe present, no GPU).
- [x] **P-013** Verified Hermes cron status and scheduler timezone (Asia/Singapore, gateway running).
- [x] **P-014** Recorded preflight summary and marked this phase complete in the checklist.
- [x] **C-001** Created durable implementation checklist at the project workspace and verified file existence.
- [x] **C-002** Read full source plan; implementation does not begin from memory alone.
- [x] **C-003** Confirmed project name, root, target hostname, VPS, and SGT timezone values.
- [x] **C-004** Confirmed this checklist is the recovery source of truth after a session restart.

## Phase 1 – Scaffold and Operating Controls
- [x] **P-001** Confirmed `/root/.hermes/projects/competitors/` contains only the checklist and no unrelated work (CLEAN).
- [x] **S-001** Confirm `/root/.hermes/projects/competitors/` is the project root and create the approved project subdirectories without disturbing the checklist.
- [x] **S-002** Create `.gitignore` to ignore secrets, caches, and temporary files.
- [x] **S-003** Create `.env.example` with placeholder environment variables.
- [x] **S-004** Create `README.md`.
- [x] **S-005** Create `.hermes.md`.
- [x] **S-006** Create `PROJECT_INDEX.md`.
- [x] **S-007** Initialize git in the project root after confirming the path is correct.
- [x] **S-008** Download all five pinned upstream gist files into `docs/upstream-gist/`.
- [x] **S-009** Verify upstream byte counts (5267, 3822, 2729, 960, 10898).
- [x] **S-010** Generate `docs/upstream-gist/SHA256SUMS`.
- [x] **S-011** Create `docs/upstream-gist/SOURCE.md` with pinned URLs, gist ID, attribution, and fetch timestamps.
- [x] **S-012** Create `docs/upstream-gist/SHA256SUMS` with checksums of each upstream file.

## Upstream Files Preserved (verbatim, checksum-verified)
- `00-README.md` (5267 bytes)
- `ANALYZE.md` (3822 bytes)
- `DASHBOARD-SPEC.md` (2729 bytes)
- `competitor-accounts.md` (960 bytes)
- `scrape.py` (10898 bytes)

All five upstream files have been downloaded to `docs/upstream-gist/` and their SHA-256 checksums recorded in `docs/upstream-gist/SHA256SUMS`. Active Hermes adaptations are separate files in the project root and are documented in the implementation plan.

## Phase 2 – Hermes Adaptation of Upstream Documents ✅
- [x] **S-013** Rewrite **00-README.md** from paid-API references to Hermes/OpenCLI/Faster-Whisper/dev-VPS operation.
- [x] **S-014** Rewrite **ANALYZE.md** from Claude/paid-API references to Hermes.
- [x] **S-015** Rewrite **DASHBOARD-SPEC.md** to target the React/FastAPI dashboard spec.
- [x] **S-016** Rewrite **competitor-accounts.md** to retain Markdown source-of-truth format.
- [x] **S-017** Refactor **scrape.py** into a thin CLI wrapper that only schedules jobs and writes staged JSON and media.
- [x] **S-018** Search active files for stale Claude references.
- [x] **S-019** Verify upstream files remain checksum-identical after active copies are edited.

## Phase 3 – Pipeline Foundation (TDD) ✅
- [x] **PL-001** Create `pyproject.toml` with runtime and dev dependency groups.
- [x] **PL-002** Create local virtual environment and install project in editable mode.
- [x] **PL-003** RED: `tests/test_accounts.py` (table parsing, dedup, normalization, active flags, no-active failure).
- [x] **PL-004** GREEN: implement `pipeline/accounts.py` minimally.
- [x] **PL-005** RED: `tests/test_ledger.py` (atomic write, lock contention, state transitions, resume).
- [x] **PL-006** GREEN: implement `pipeline/ledger.py`.
- [x] **PL-007** RED: `tests/test_models.py` (reel input, analysis output, score bounds, hook enum, sections).
- [x] **PL-008** GREEN: implement `pipeline/models.py` and export JSON schema.
- [x] **PL-009** RED: `tests/test_opencli_instagram.py` (capture & secret-scrub fixtures, reel filtering, error classification).
- [x] **PL-010** GREEN: implement `pipeline/opencli_instagram.py`.
- [x] **PL-011** RED: `tests/test_media.py` (path traversal, symlink, ffprobe, oversized, audio extraction, no-audio).
- [x] **PL-012** GREEN: implement `pipeline/media.py`.
- [x] **PL-013** RED: `tests/test_whisper_transcriber.py` (transcript shape, segments, language, timeout, corrupt audio).
- [x] **PL-014** GREEN: implement `pipeline/whisper_transcriber.py` with injected backend.
- [x] **PL-015** RED: `tests/test_collector.py` (OpenCLI → media → transcript → ledger flow).
- [x] **PL-016** GREEN: implement `pipeline/collector.py`.
- [x] **PL-017** RED: `tests/test_notes.py` (deterministic Markdown, special chars, no raw HTML).
- [x] **PL-018** GREEN: implement `pipeline/notes.py`.
- [x] **PL-019** Run full Python suite.

## Phase 4 – Validator, Publish Bundle, and Hermes Playbook Entry ✅
- [x] **PB-001** Write `scripts/validate_analysis.py` that loads a bundle JSON and asserts it satisfies `AnalysisBundle`.
- [x] **PB-002** Pin a tiny known-good analysis bundle fixture (forward test).
- [x] **PB-003** Pin a deliberately malformed bundle fixture and assert the validator fails closed.
- [x] **PB-004** Write `scripts/build_publish_bundle.py` that walks `data/staging/<run>/analysis/` and produces a single `bundle.json`.
- [x] **PB-005** Write `scripts/publish_bundle.sh` that transfers the bundle over SSH and runs the container-only importer (skipped on the Hermes host when the importer is not yet wired).
- [x] **SK-001** Create `.hermes/skills/competitor-intelligence/SKILL.md` with triggers, prerequisites, exact procedure, validation, publication, cleanup, and failure handling.
- [x] **SK-002** Add `.hermes/skills/competitor-intelligence/references/analysis-contract.md` mirroring the JSON schema.
- [x] **SK-003** Add `.hermes/skills/competitor-intelligence/references/operator-runbook.md` with the recovery flow.

## Phase 5 – API, Database, and Importer (TDD) ✅
- [x] **API-001** Scaffold `apps/api/app/` with FastAPI, SQLAlchemy 2, Alembic, psycopg 3.
- [x] **API-002** RED: `apps/api/tests/test_health.py` — DB-down responses do not leak secrets.
- [x] **API-003** GREEN: `/api/healthz` returns 200 healthy or 503 with a non-secret reason.
- [x] **API-004** RED: `apps/api/tests/test_auth.py` — login, wrong password, rate limit, cookie attrs, logout.
- [x] **API-005** GREEN: implement bcrypt + secure session cookie for the single-operator login.
- [x] **API-006** RED: `apps/api/tests/test_importer.py` — first import, duplicate, transaction rollback.
- [x] **API-007** GREEN: implement the import CLI + the API route.
- [x] **API-008** RED: `apps/api/tests/test_dashboard.py` — KPIs, reach, taxonomy, pagination, date windows.
- [x] **API-009** GREEN: implement `/api/dashboard/summary`, `/api/reels`, `/api/reels/{id}`, `/api/runs`.
- [x] **API-010** RED: `apps/api/tests/test_publish_bundle.py` — bundle round-trip into the database.
- [x] **API-011** GREEN: implement the publish-bundle importer using the Pydantic models.
- [x] **API-012** Run the full API suite against PostgreSQL (not SQLite).

## In-dashboard Instagram login (cookie paste, dev-VPS site-session write)
- [x] **IA-001** RED: `apps/api/tests/test_instagram_auth.py` (state token, validation, write-refuses-symlink, whoami-after-write, logout, no-secrets).
- [x] **IA-002** GREEN: `apps/api/app/auth_instagram.py` with the four functions.
- [x] **IA-003** GREEN: extend `pipeline/bootstrap_session.py` with `write_cookies_to_profile`, `clear_profile`, and the additional `whoami` states.
- [x] **IA-004** GREEN: `apps/api/app/routes/instagram_auth.py` wiring the four routes.
- [x] **IA-005** RED: `apps/web/src/test/InstagramAuthBanner.test.tsx` (status states, paste flow, devtools instructions visible, warning visible).
- [x] **IA-006** GREEN: `apps/web/src/lib/instagram-auth.ts` typed wrapper.
- [x] **IA-007** GREEN: `apps/web/src/components/InstagramAuthBanner.tsx` component.
- [ ] **IA-008** Manual verification on dev VPS with a real `sessionid` paste.
- [x] **IA-009** Wire banner into the dashboard layout.

Full plan: `/root/.hermes/plans/2026-07-24_134500-instagram-in-dashboard-login.md`

## Phase 6 – Frontend (React/Vite/Fluent UI/Recharts)

## Phase 7 – Deployment (Docker, Caddy, Cloudflare, GitHub Actions)
- [x] **DP-001** Dockerfile for the API (python:3.12-slim, non-root, healthcheck, uvicorn).
- [x] **DP-002** Dockerfile for the web (node:22 build → caddy:2.8-alpine runtime).
- [x] **DP-003** `apps/web/Caddyfile` static file server with SPA fallback.
- [x] **DP-004** `deploy/docker-compose.yml` (postgres + api + web + whisper-worker profile).
- [x] **DP-005** `deploy/Caddyfile` production reverse proxy for `competitors.terrybot.top`.
- [x] **DP-006** `deploy/.env.example` template with every env var.
- [x] **DP-007** `deploy/deploy.sh` one-shot deploy script.
- [x] **DP-008** `deploy/README.md` operator runbook.
- [x] **DP-009** `deploy/cloudflare.tfvars.example` DNS record template.
- [x] **DP-010** `.github/workflows/competitors-deploy.yml` webhook.
- [x] **DP-011** `apps/api/alembic/env.py` + initial migration `2026_07_25_0930_initial.py`.
- [x] **DP-012** `apps/api/requirements.txt` pinned.
- [x] **DP-013** `.dockerignore` to keep the image slim.
- [x] **DP-014** Fix Docker daemon MTU to 1400 on the host (Hetzner MTU mismatch).
- [x] **DP-015** `competitors-net` Docker network with driver_opts mtu=1400.
- [ ] **DP-016** Build the API image on the dev VPS.
- [ ] **DP-017** Build the web image on the dev VPS.
- [ ] **DP-018** `docker compose up -d` on the dev VPS.
- [ ] **DP-019** `alembic upgrade head` on the dev VPS.
- [ ] **DP-020** Configure Caddy on the dev VPS with the production Caddyfile.
- [ ] **DP-021** Configure Cloudflare DNS for `competitors.terrybot.top`.
- [ ] **DP-022** Smoke-test: `curl -fsS https://competitors.terrybot.top/api/healthz`.
- [ ] **DP-023** Manual end-to-end: scrape → transcribe → publish bundle → API ingest → dashboard.

- [ ] **FE-001** Scaffold `apps/web/` with Vite + React + TypeScript.
- [ ] **FE-002** Install Fluent UI React, Recharts, Vitest, Testing Library, Playwright.
- [ ] **FE-003** Define MadeAt2AM brand theme tokens.
- [ ] **FE-004** RED: `apps/web/src/test/login.test.tsx` — submit, errors, disabled state.
- [ ] **FE-005** GREEN: implement the login page + session bootstrap.
- [ ] **FE-006** RED: dashboard tests for loading/empty/error/populated states.
- [ ] **FE-007** GREEN: KPI, reach, taxonomy, latest-run components.
- [ ] **FE-008** RED: reel-list tests (filters, pagination, expand).
- [ ] **FE-009** GREEN: reel list and detail expansion.
- [ ] **FE-010** RED: pipeline-tab tests (SGT/UTC, failures).
- [ ] **FE-011** GREEN: implement the pipeline tab.
- [ ] **FE-012** Reduced-motion + accessible table fallbacks.
- [ ] **FE-013** Production build (`npm run build`).

## Next Steps
1. Execute **FE-001** through **FE-013** to produce the dashboard frontend.
2. Phase 7 (deployment assets + Docker) follows.
3. Phase 8 (VPS deploy + first user) follows.
4. Phase 9 (live data + final acceptance) follows.

