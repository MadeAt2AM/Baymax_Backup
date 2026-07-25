# Worked Example — competitors project

A real-world filled-out example from the `competitors` project
(`/root/.hermes/projects/competitors/IMPLEMENTATION_CHECKLIST.md`). Use it
to see how phases are scoped, verified, and ticked in practice.

This is a snapshot of the live checklist at the moment 5 phases were
complete. It is **not** a template — it is a working document showing the
patterns the agent should produce.

---

# Competitors Intelligence Dashboard Implementation Checklist

## Progress State
- **Current phase:** Phase 5 (API + database) — not yet started
- **Current task:** API-001 (Scaffold FastAPI app)
- **Last completed task:** PL-001 through PL-019, PB-001 through PB-005, SK-001 through SK-003
- **Next task:** API-001
- **Last updated:** 2026-07-24 12:48 SGT
- **Implementation status:** Self-hosted pipeline green; 57 tests pass; validator + publish bundle + Hermes playbook entry all wired.
- **Deployment status:** Not started
- **First-user status:** Not created
- **Live operator confirmation:** Pending

## Phase 0 – Checklist and Operating Controls ✅
- [x] **C-001** Created durable implementation checklist at `/root/.hermes/projects/competitors/IMPLEMENTATION_CHECKLIST.md`.
- [x] **C-002** Read full source plan (`/root/.hermes/plans/2026-07-24_100009-competitors-dashboard-web-app.md`). Implementation does not begin from memory.
- [x] **C-003** Confirmed project name, root, target hostname (`competitors.terrybot.top`), dev VPS (`147.79.18.32`), SGT timezone.
- [x] **C-004** Confirmed this checklist is the recovery source of truth.

## Phase 1 – Read-only preflight ✅
- [x] **P-001** Confirmed project root contains only the checklist (CLEAN).
- [x] **P-002** Local tool versions: Python 3.11.15, Node 22.22.3, OpenCLI 1.8.5, FFmpeg/ffprobe 6.1.1, faster-whisper 1.2.1, ctranslate2 4.8.0, Docker 29.5.2.
- [x] **P-003** Hermes status: v0.19.0, default profile, MiniMax-M3/minimax, gateway running, 10 active routines.
- [x] **P-004** GitHub authenticated; token scope read-only confirmed.
- [x] **P-005** dev-vps SSH identity confirmed (host `cyberslide`, user `root`).
- [x] **P-006** Dev-VPS resources: 4 vCPU AMD Ryzen 5 5600, 7.8 GiB RAM, ~50 GiB free disk, no GPU.
- [x] **P-007** Docker infrastructure: external `web` bridge MTU 1400. `payntra-app`, `payntra-db`, `searxng` running. **No `caddy` container** — dev VPS uses host nginx.
- [x] **P-008** Webhook: no `/etc/webhook/hooks.json`, no webhook systemd unit, no `/srv/scripts/.gh-token`. Deployment will require designing the deploy trigger, not assuming the existing pattern.
- [x] **P-009** Cloudflare: `competitors.terrybot.top` returns NXDOMAIN. No `/srv/scripts/.cf-env`. DNS/proxy must be explicitly provisioned in deployment.
- [x] **P-010** OpenCLI 1.8.5 installed; `whoami` blocked because Browser Bridge extension is not connected. No cookies printed.
- [x] **P-011** **BLOCKED** until operator confirms: secondary Instagram account, session bootstrap method. Implementation continues with offline fixtures; authenticated collection is gated.
- [x] **P-012** Faster-Whisper readiness: packages present, FFmpeg present, no GPU.
- [x] **P-013** Cron status: gateway running, host timezone `Asia/Singapore`.
- [x] **P-014** Preflight summary recorded.

## Phase 2 – Project Scaffold ✅
- [x] **S-001** Project root + approved subdirectories created.
- [x] **S-002** `.gitignore` written.
- [x] **S-003** `.env.example` written.
- [x] **S-004** `README.md` written.
- [x] **S-005** `.hermes.md` written.
- [x] **S-006** `PROJECT_INDEX.md` written.
- [x] **S-007** Git init deferred until scaffold is settled.
- [x] **S-008** Five pinned upstream gist files downloaded to `docs/upstream-gist/`.
- [x] **S-009** Upstream byte counts verified: 5267, 3822, 2729, 960, 10898.
- [x] **S-010** `docs/upstream-gist/SHA256SUMS` generated.
- [x] **S-011** `docs/upstream-gist/SOURCE.md` written with pinned URLs, gist ID, attribution, fetch timestamps.
- [x] **S-012** Checksum file regenerated after redownload and re-verified identical.

## Phase 3 – Hermes Adaptation of Upstream Documents ✅
- [x] **S-013** Rewrote `00-README.md` from paid-API to Hermes/OpenCLI/Faster-Whisper/dev-VPS.
- [x] **S-014** Rewrote `ANALYZE.md` from Claude to Hermes.
- [x] **S-015** Rewrote `DASHBOARD-SPEC.md` to target React/FastAPI spec.
- [x] **S-016** Rewrote `competitor-accounts.md` to retain Markdown source-of-truth.
- [x] **S-017** Refactored `scrape.py` into a thin CLI wrapper.
- [x] **S-018** Scanned active files for stale Claude references: **0 matches outside `docs/upstream-gist/`**.
- [x] **S-019** Verified upstream SHA-256 sums unchanged after active copies were edited.

## Phase 4 – Pipeline Foundation (TDD) ✅
- [x] **PL-001** `pyproject.toml` written.
- [x] **PL-002** Local venv created; project installed in editable mode.
- [x] **PL-003** RED then **PL-004** GREEN: `tests/test_accounts.py` (7 tests) + `pipeline/accounts.py`.
- [x] **PL-005** RED then **PL-006** GREEN: `tests/test_ledger.py` (6 tests) + `pipeline/ledger.py`.
- [x] **PL-007** RED then **PL-008** GREEN: `tests/test_models.py` (10 tests) + `pipeline/models.py`.
- [x] **PL-009** RED then **PL-010** GREEN: `tests/test_opencli_instagram.py` (10 tests) + `pipeline/opencli_instagram.py`.
- [x] **PL-011** RED then **PL-012** GREEN: `tests/test_media.py` (10 tests) + `pipeline/media.py`.
- [x] **PL-013** RED then **PL-014** GREEN: `tests/test_whisper_transcriber.py` (4 tests) + `pipeline/whisper_transcriber.py`.
- [x] **PL-015** RED then **PL-016** GREEN: `tests/test_collector.py` (5 tests) + `pipeline/collector.py`.
- [x] **PL-017** RED then **PL-018** GREEN: `tests/test_notes.py` (5 tests) + `pipeline/notes.py`.
- [x] **PL-019** Full Python suite: **57 passed in 0.13s**.

## Phase 5 – Validator, Publish Bundle, and Hermes Playbook Entry ✅
- [x] **PB-001** `scripts/validate_analysis.py` written.
- [x] **PB-002** Good bundle fixture pinned at `tests/fixtures/bundles/good.json`.
- [x] **PB-003** Bad bundle fixture pinned at `tests/fixtures/bundles/bad_score.json`; validator fails closed with exit 1.
- [x] **PB-004** `scripts/build_publish_bundle.py` written and round-trip verified.
- [x] **PB-005** `scripts/publish_bundle.sh` written; dry-run produces the expected SCP + docker exec commands.
- [x] **SK-001** `.hermes/skills/competitor-intelligence/SKILL.md` written.
- [x] **SK-002** `references/analysis-contract.md` written mirroring the JSON schema.
- [x] **SK-003** `references/operator-runbook.md` written with recovery flow.

## Phase 6 – API, Database, and Importer (TDD) 🔜
- [ ] **API-001** Scaffold `apps/api/app/` with FastAPI, SQLAlchemy 2, Alembic, psycopg 3.
- [ ] **API-002** RED: `apps/api/tests/test_health.py` — DB-down responses do not leak secrets.
- [ ] **API-003** GREEN: `/api/healthz` returns 200 healthy or 503 with a non-secret reason.
- [ ] **API-004** RED: `apps/api/tests/test_auth.py` — login, wrong password, rate limit, cookie attrs, logout.
- [ ] **API-005** GREEN: implement bcrypt + secure session cookie for the single-operator login.
- [ ] **API-006** RED: `apps/api/tests/test_importer.py` — first import, duplicate, transaction rollback.
- [ ] **API-007** GREEN: implement the import CLI + the API route.
- [ ] **API-008** RED: `apps/api/tests/test_dashboard.py` — KPIs, reach, taxonomy, pagination, date windows.
- [ ] **API-009** GREEN: implement `/api/dashboard/summary`, `/api/reels`, `/api/reels/{id}`, `/api/runs`.
- [ ] **API-010** RED: `apps/api/tests/test_publish_bundle.py` — bundle round-trip into the database.
- [ ] **API-011** GREEN: implement the publish-bundle importer using the Pydantic models.
- [ ] **API-012** Run the full API suite against PostgreSQL (not SQLite).

## Blockers and decisions
- **BLOCKED:** P-011 secondary Instagram account + session bootstrap.
- **Decision required:** repository names for canonical source + VPS mirror; deployment trigger design (no webhook daemon present).
- **Decision required:** SGT schedule for any future routine; pinned Hermes model.

## Completion record
| Phase | Status | Evidence |
|---|---|---|
| Phase 0 – Checklist bootstrap | COMPLETE | IMPLEMENTATION_CHECKLIST.md exists |
| Phase 1 – Read-only preflight | COMPLETE | 14 items, deviations noted |
| Phase 2 – Project scaffold | COMPLETE | 5 upstream files, SHA-256 verified |
| Phase 3 – Hermes adaptation | COMPLETE | 0 stale Claude references in active files |
| Phase 4 – Pipeline foundation | COMPLETE | 57 tests pass |
| Phase 5 – Validator + playbook | COMPLETE | Validator + publish bundle + Hermes SKILL.md in place |
| Phase 6 – API + database | NOT STARTED | |
| Phase 7 – Frontend | NOT STARTED | |
| Phase 8 – Deployment | NOT STARTED | |
| Phase 9 – Live data + first user | NOT STARTED | Blocked on P-011 |
| Phase 10 – Validation | NOT STARTED | |
| Phase 11 – Routine | NOT STARTED | |
| Phase 12 – Final acceptance | NOT STARTED | |
