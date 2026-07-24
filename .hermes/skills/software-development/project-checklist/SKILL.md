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

1. **Create the checklist** at the start of the project using the template above, filling in project-specific details.
2. **Mark tasks as completed** only after objective verification (e.g., running a command and seeing expected output, or confirming a file exists with correct content).
3. **Update the checklist** immediately after verification:
   - Change the relevant `[ ]` to `[x]`.
   - Update `Last completed task` to include the newly completed task ID.
   - Update `Current task` to the next pending task.
   - Update `Last updated` timestamp in SGT.
   - Update `Implementation status` with a brief note.
4. **After a session restart**, read the checklist to determine where to leave off.
5. **Never** rely on chat history or memory for task status; always read the checklist.

## Pitfalls

- **Forgetting to update the checklist** after a task leads to drift between actual progress and recorded progress.
- **Checking a task before verification** creates false confidence; always verify first.
- **Storing secrets or sensitive data** in the checklist; keep it free of passwords, tokens, cookies, or session material.
- **Using ambiguous task descriptions**; each task should be a focused 2-5 minute action with clear verification steps.
- **Not using SGT for timestamps**; always convert to Asia/Singapore (SGT, UTC+8) first.

## Verification

After updating the checklist, read it back to ensure the changes are saved correctly and the file is valid markdown.

## References

- See `references/checklist-template.md` for a starter template.
- See `references/example-checklist.md` for an example of a filled-out checklist.