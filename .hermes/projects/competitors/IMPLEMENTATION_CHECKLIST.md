# Competitors Intelligence Dashboard Implementation Checklist

## Progress State
- **Current phase:** Scaffold complete; upstream preservation complete; moving to adaptation
- **Current task:** S-013 (rewrite 00-README.md)
- **Last completed task:** S-012 (source preservation complete)
- **Blocked task:** None (S-011 was the Instagram auth gate; it remains a pre-deployment blocker only)
- **Next task:** S-013
- **Last updated:** 2026-07-24 12:34 SGT
- **Implementation status:** Preflight completed with no secrets leaked. Scaffold and upstream preservation are complete. Active Hermes adaptations begin now.

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

## Phase 2 – Hermes Adaptation of Upstream Documents
- [ ] **S-013** Rewrite **00-README.md** from paid-API references to Hermes/OpenCLI/Faster-Whisper/dev-VPS operation.
- [ ] **S-014** Rewrite **ANALYZE.md** from Claude/paid-API references to Hermes.
- [ ] **S-015** Rewrite **DASHBOARD-SPEC.md** to target the React/FastAPI dashboard spec.
- [ ] **S-016** Rewrite **competitor-accounts.md** to retain Markdown source-of-truth format.
- [ ] **S-017** Refactor **scrape.py** into a thin CLI wrapper that only schedules jobs and writes staged JSON and media.
- [ ] **S-018** Search active files for stale Claude references.
- [ ] **S-019** Verify upstream files remain checksum-identical after active copies are edited.

## Next Steps
1. Execute **S-013** through **S-019** to produce the Hermes-adapted working copies of the five upstream documents.
2. Confirm the `IMPLEMENTATION_CHECKLIST.md` status before moving to the pipeline implementation phase.