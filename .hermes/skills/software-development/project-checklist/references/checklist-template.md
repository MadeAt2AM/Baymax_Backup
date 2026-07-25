# Checklist Template

A blank, copy-paste-ready skeleton. Replace bracketed placeholders before
use. Keep the `Progress State` block at the top and phases from top to
bottom in execution order.

---

# [<Project Name>] Implementation Checklist

## Progress State
- **Current phase:** [phase name]
- **Current task:** [Phase-NNN]
- **Last completed task:** [Phase-NNN]
- **Next task:** [Phase-NNN]
- **Last updated:** [YYYY-MM-DD HH:MM SGT]
- **Implementation status:** [one-sentence status]
- **Deployment status:** [Not started | In progress | Live]
- **First-user status:** [Not created | Created]
- **Live operator confirmation:** [Pending | Received]

## Phase 0 – Checklist and Operating Controls
- [ ] **C-001** Create this durable checklist at the project workspace and verify it can be read back.
  - Verify: file exists at `<project_path>/IMPLEMENTATION_CHECKLIST.md`.
- [ ] **C-002** Read the full source plan before implementation begins.
- [ ] **C-003** Confirm the project name, project root, target hostname, target VPS, and SGT timezone.
- [ ] **C-004** Confirm this checklist is the recovery source of truth after a session restart.

## Phase 1 – Read-only preflight
- [ ] **P-001** Confirm the project root contains only this checklist and no unrelated work.
- [ ] **P-002** Check local tool versions and availability.
- [ ] **P-003** Check active profile and running services without modifying configuration.
- [ ] **P-004** Check authentication state read-only.
- [ ] **P-005–P-NN** Add project-specific preflight items.

## Phase 2 – Project scaffold and source preservation
- [ ] **S-001** Confirm project root and create approved subdirectories.
- [ ] **S-002** Create `.gitignore` to ignore secrets, caches, and temporary files.
- [ ] **S-003** Create `.env.example` with placeholder environment variables.
- [ ] **S-004** Create `README.md`.
- [ ] **S-005** Create `.hermes.md`.
- [ ] **S-006** Create `PROJECT_INDEX.md`.
- [ ] **S-007** Initialize git in the project root after confirming the path.
- [ ] **S-008–S-NN** Add project-specific scaffold items.

## Phase 3 – [Core implementation phase name]
- [ ] **XX-001** [Focused 2-5 minute action.] Verify: [objective evidence.]

## Phase N – [Final phase: validation, deployment, or handoff]
- [ ] **FN-001** [Final verification.]

## Blockers and decisions
- **BLOCKED:** [list]
- **Decision required:** [list]

## Completion record
| Phase | Status | Evidence |
|---|---|---|
| Phase 0 | NOT STARTED | |
| Phase 1 | NOT STARTED | |
| Phase 2 | NOT STARTED | |
| Phase N | NOT STARTED | |
