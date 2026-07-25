---
name: project-checklist
description: Create and maintain a durable implementation checklist for a project, stored in the project workspace, to track progress across sessions.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [checklist, project-management, implementation, workflow]
    related_skills: [project-initialization, todo]
---

# Project Checklist Skill

This skill provides a reusable approach to creating and maintaining a durable implementation checklist for a project. The checklist is stored as a markdown file in the project workspace and is updated after each completed task to serve as the source of truth across session restarts.

## When to Use

- When starting a new project and you want to track implementation tasks with persistence.
- When you need a session has ended and you need to resume work without relying on chat history.
- When you want a clear, verifiable record of completed and pending tasks.

## Key Principles

- The checklist is the single source of truth for task status.
- Update the checklist immediately after verifying a task is complete.
- Never rely on chat history or memory for task status; always read the checklist.
- Keep the checklist in the project root (e.g., `/root/.hermes/projects/<project>/IMPLEMENTATION_CHECKLIST.md`).
- Use checkboxes (`[ ]` for pending, `[x]` for completed) for visual clarity.
- Include phase and task identifiers to allow precise tracking.

## Template

Create a file `IMPLEMENTATION_CHECKLIST.md` with the following structure:

```markdown
# <Project Name> Implementation Checklist

## Progress State
- **Current phase:** <current phase name>
- **Current task:** <current task ID>
- **Last completed task:** <list of task IDs>
- **Next task:** <next task ID>
- **Last updated:** <timestamp in SGT>
- **Implementation status:** <brief status>
- **Deployment status:** Not started
- **First-user status:** Not created
- **Live operator confirmation:** Pending

## Phase 0 – Checklist and Operating Controls
- [ ] **C-001** Create this durable checklist at the project workspace and verify it can be read back.
  - Verify: file exists at `<project_path>/IMPLEMENTATION_CHECKLIST.md`.
- [ ] **C-002** Read the full source plan before implementation begins.
  - Verify: source plan path recorded above and no implementation begins from memory alone.
- [ ] **C-003** Confirm the project name, project root, target hostname, target VPS, and SGT timezone.
  - Verify: values match the source plan and user request.
- [ ] **C-004** Confirm this checklist is the recovery source of truth after a session restart.
  - Verify: the next session can locate and read it without relying on chat history.

## Phase 1: Read-only preflight
- [ ] **P-001** Confirm `/root/.hermes/projects/<project>/` contains only this checklist and no unrelated work.
  - Command: `test "$(find /root/.hermes/projects/<project>/ -mindepth 1 -maxdepth 1 ! -name IMPLEMENTATION_CHECKLIST.md -print -quit)" = "" && echo CLEAN || echo EXISTS`
  - Expected: `CLEAN`; stop and inspect any other entry before touching it.
- [ ] **P-002** Check local tool versions and availability.
  - Check: Python 3.12-compatible, Node 20+, npm, git, Docker, SSH, curl, ffmpeg, ffprobe, pytest.
  - Verify: record versions in `docs/environment.md` after scaffold creation.
- ... (add more preflight checks as needed)

## Phase 2: Project scaffold and source preservation
- [ ] **S-001** Confirm `/root/.hermes/projects/<project>/` is the project root and create the approved project subdirectories without disturbing the checklist.
- [ ] **S-002** Create `.gitignore` to ignore secrets, caches, and temporary files.
- [ ] **S-003` Create `.env.example` with placeholder environment variables.
- [ ] **S-004** Create `README.md`.
- [ ] **S-005** Create `.hermes.md`.
- [ ] **S-006** Create `PROJECT_INDEX.md`.
- [ ] **S-007** Initialize git in the project root after confirming the path is correct.
- [ ] **S-008** Download all five pinned upstream gist files into `docs/upstream-gist/`.
- [ ] **S-009** Verify upstream byte counts.
- [ ] **S-010** Generate `docs/upstream-gist/SHA256SUMS`.
- [ ] **S-011** Create `docs/upstream-gist/SOURCE.md` with pinned URLs, gist ID, attribution, and fetch timestamps.
- [ ] **S-012** Create `docs/upstream-gist/SHA256SUMS` with checksums of each upstream file.
- [ ] **S-013** Rewrite **00-README.md** from paid‑API references to Hermes/OpenCLI/Faster‑Whisper/dev‑VPS operation.
- [ ] **S-014** Rewrite **ANALYZE.md** from Claude/paid‑API references to Hermes.
- [ ] **S-015** Rewrite **DASHBOARD‑SPEC.md** to target the React/FastAPI dashboard spec.
- [ ] **S-016** Rewrite **competitor‑accounts.md** to retain Markdown source‑of‑truth format.
- [ ] **S-017** Refactor **scrape.py** into a thin CLI wrapper that only schedules jobs and writes staged JSON and media.
- [ ] **S-018** Search active files for stale Claude references.
- [ ] **S-019** Verify upstream files remain checksum‑identical after active copies are edited.

## Subsequent Phases
Add additional phases as needed (pipeline, app, deployment, validation, etc.) following the same pattern:
- [ ] **<Phase>-<XXX>** Description of task.
  - Verify: objective evidence of completion.

## Completion
When all tasks are complete, update the checklist to reflect final status and record evidence.
```

## Procedure

1. **Create the checklist** at the start of the project using the template above, filling in project-specific details. The checklist should be the first file in the project root so it lands before any other work — `IMPLEMENTATION_CHECKLIST.md` at `/root/.hermes/projects/<project>/IMPLEMENTATION_CHECKLIST.md`.
2. **Mark tasks as completed** only after objective verification (e.g., running a command and seeing expected output, or confirming a file exists with correct content).
3. **Update the checklist** immediately after verification:
   - Change the relevant `[ ]` to `[x]`.
   - Update `Last completed task` to include the newly completed task ID.
   - Update `Current task` to the next pending task.
   - Update `Last updated` timestamp in SGT.
   - Update `Implementation status` with a brief note.
4. **After a session restart**, read the checklist to determine where to leave off. Do not read chat history first — the checklist is the recovery contract.
5. **Never** rely on chat history or memory for task status; always read the checklist.

## Recovery protocol (session dies, picks up later)

The new session starts with zero memory of what happened. It should:

1. Locate the project root: `find /root/.hermes/projects -name IMPLEMENTATION_CHECKLIST.md -maxdepth 2`.
2. Read the checklist in full.
3. Read the `Progress State` block to find `Current task` and `Next task`.
4. Read the `Last completed task` line and the `[x]` ticks to confirm what is actually done.
5. Run the verification command for the next pending task before starting work.
6. Continue. Do not re-run anything in the `[x]` block.

If the checklist is missing, the project is not in a recoverable state. Halt and surface the gap to the user before doing anything else.

## Recovery from context compression (same session)

When the conversation is compacted mid-session, the user's next message is often a variant of "where are we at, continue from there". The same checklist-based recovery applies, but with one extra step: the compressed summary is a hint, not a source of truth.

1. **Read the checklist first.** Do not reason from the compressed summary; treat it as a hint about what was happening, not what was done.
2. **Confirm via grep, not memory.** Run `grep -cE "^- \[x\] \*\*" <project>/IMPLEMENTATION_CHECKLIST.md` to count completed tasks, then `grep -nE "^- \[(x| )\] \*\*" <project>/IMPLEMENTATION_CHECKLIST.md | head -20` to see the top of the list. The progress state block at the top should match the ticked count.
3. **Reply with current state first.** A short status-report reply (phase, last completed task, current task, next task) wins. Then continue the next task in the plan.
4. **Re-verify the in-progress task.** If the compressed summary claims work was done but the checklist shows it unchecked, re-run the verification command and only then tick. An unchecked phase that has actually been done is a soft failure; a checked phase that has not been done is a hard failure.
5. **Trust the dense file over the summary.** The checklist is written continuously; the summary is computed at compaction time. The file is fresher and more precise.

## Tick-as-you-go cadence

The checklist is written once and rewritten continuously. The minimum viable pattern is:

- After every verified task, update the checklist **before** starting the next one.
- Treat each phase as a checkpoint: when the last task in a phase is verified, flip the phase heading from `## Phase N – <name>` to `## Phase N – <name> ✅` and update the Progress State block.
- When appending new phases to a long checklist, anchor the new phase at the bottom but update the Progress State block at the top immediately — the next session reads the top first.

## References

- See `references/checklist-template.md` for a starter template.
- See `references/example-checklist.md` for a real-world filled-out example (the `competitors` project, ~70 tasks across 5 phases).
- See `references/updating-the-checklist.md` for the `terminal` + python heredoc fallback used when the `patch` tool rejects valid edits.
- See `references/api-tdd-syspath-pattern.md` for the conftest + module-reload pattern when the FastAPI app lives in `apps/api/app/`.

## Pitfalls

- **Forgetting to update the checklist** after a task leads to drift between actual progress and recorded progress.
- **Checking a task before verification** creates false confidence; always verify first.
- **Storing secrets or sensitive data** in the checklist; keep it free of passwords, tokens, cookies, or session material.
- **Using ambiguous task descriptions**; each task should be a focused 2-5 minute action with clear verification steps.
- **Not using SGT for timestamps**; always convert to Asia/Singapore (SGT, UTC+8) first.
- **Letting the checklist drift out of sync with the `todo` tool.** The `todo` list is for the current session's working memory; the checklist is for session death. Pick the checklist as the source of truth and update it after every verified task, regardless of whether `todo` mirrors it.
- **Updating the checklist with the `patch` tool** when the target line is short or the file has been mutated by sibling agents. The `patch` tool can intermittently reject `mode="replace"` calls with a `path required` error even when `path` is supplied. Fall back to `terminal` + `python` heredoc (`python3 - <<'PY' ... PY`) doing a literal `str.replace()` on the file. This is reliable and survives helper substitution.
- **Treating the Progress State block as set-and-forget.** When you append new phases mid-document, you must update the `Current phase`, `Last completed task`, `Next task`, `Last updated`, and `Implementation status` lines at the top before the next task. Without that, a recovered session reads stale state and resumes in the wrong place.
- **Pre-creating the checklist before scaffold.** The first file in the project root should be `IMPLEMENTATION_CHECKLIST.md` (so it lands before any other work and the recovered session finds it immediately). Directory layout, `.gitignore`, and `README.md` come after C-001.
- **Tick-then-test vs test-then-tick.** Test, observe the expected output, then tick. The checklist is the recovery contract — an unchecked phase that has actually been done is a soft failure; a checked phase that has not been done is a hard failure.
- **MD-arity task IDs.** Use `PhaseLetter-NNN` consistently (e.g. `C-001`, `P-001`, `S-001`, `PL-001`, `API-001`). They are sortable, greppable, and survive sed/awk substitution. Mixing shapes (`PHASE1-2`, `1.3`) breaks the search.
- **Missing body row vs. blocker note.** A task ID mentioned only in the Progress State block's "Blocked task" line but NOT represented as a `[ ] **P-NNN**` row in the body becomes invisible to grep-based recovery. The next session sees "P-011 is blocked" but no checkbox to flip. Either include every task ID as an explicit body row, or don't mention the ID in the Progress State block — never reference a task that isn't in the body.
- **Stale references in active files after adaptation.** When the source plan instructs you to adapt a document from one system (e.g. "edit Claude docs to use Hermes"), pin a checklist item that scans the active files (the rewritten copies) for the stale system name. Symptom: a "Hermes" doc still says "tell Claude to run X". Acceptance: `grep -r "Claude" <project>/00-README.md <project>/ANALYZE.md <project>/DASHBOARD-SPEC.md` returns zero matches. The pinned verification proves the rewrite actually happened, not just that the file was renamed.
- **Two file trees, one byte count check.** When the source plan says "preserve N upstream files verbatim AND write N adapted copies", each tree needs its own byte-count + SHA-256 verification. A single `wc -c` over both trees will report the active copies' size if they sit in the same `find ...` pass. Walk the upstream tree first (record byte count), then walk the active tree separately, and assert the upstream bytes match the expected pinned sizes from the source plan.
- **Preflight on the wrong machine.** When the plan involves a remote VPS, every "is tool X installed?" preflight check must run **on the target machine**, not the Hermes host. Common pitfall: the Hermes host has OpenCLI 1.8.5, the developer assumes the dev VPS does too, and the install step later discovers the VPS is a clean Ubuntu 24.04 image with none of Node, npm, google-chrome, ffmpeg, ffprobe, or OpenCLI. Pre-flight pattern that catches this: `ssh <vps-alias> 'for c in opencli node npm google-chrome ffmpeg ffprobe python3.12; do command -v $c; done'` — run once at preflight and pin the output as evidence in the checklist. The checklist row should explicitly say "on the dev VPS" not just "OpenCLI installed".
- **Refuse the impossible ask, offer the only safe alternative.** When the user asks for a UX shape the underlying platform forbids (e.g. "build an in-dashboard login for Instagram" — Instagram doesn't support third-party OAuth or post-login redirects), do NOT silently build a phishing-style proxy. The right move: explain concretely why the requested shape is impossible (cite the platform's behavior), then offer the only safe alternative with a clear risk warning (e.g. cookie paste from a real Chrome where the operator logged in directly). Encode the chosen path as checklist tasks before any code is written, and pin a task that warns the user about the account-ban risk. The discipline: distinguish "user said X" from "user wants Y, and X was their guess at how to get Y". Surface the Y, then offer the X' that's actually buildable.
- **API subfolder + sys.path + module reload.** When the project layout puts the API under `apps/api/app/` rather than at the repo root, tests in `apps/api/tests/` need three things: (1) `apps/api/` on `sys.path` via a `conftest.py` that does `sys.path.insert(0, str(_API_DIR))`, (2) `tests/__init__.py` *removed* at the repo root or pytest treats the sibling `tests/` as a package and breaks collection when both `tests/` and `apps/api/tests/` are collected, (3) `importlib.reload()` between tests if any of the app modules read env vars at import time. See `references/api-tdd-syspath-pattern.md` for the worked example.

## Verification

After updating the checklist, read it back to ensure the changes are saved correctly and the file is valid markdown.