Example Agents.md


 Working Rules

- Work on **one feature at a time**. Never parallelize within a sprint feature.
- Do not mark a feature complete just because code was added.
- Keep changes within the selected feature scope unless a blocker forces a narrow supporting fix.
- Do not silently change verification rules during implementation.
- Prefer durable repo artifacts over chat summaries.
- If baseline verification is already failing, fix that first. Do not stack new feature work on top of a broken starting state.

---

## Required Artifacts

| File | Purpose |
|---|---|
| `feature_list.json` | Source of truth for all features — name, status, verification method, evidence |
| `PROGRESS.md` | Session log + current verified state |
| `SESSION-HANDOFF.md` | Per-session context transfer for next session continuity |
| `CLEAN-STATE-CHECKLIST.md` | Pre-flight check before ending session |
| `EVALUATOR-RUBRIC.md` | Acceptance criteria applied before marking feature done |
| `init.sh` | Standard startup + verification path |

---

## Definition of Done

A feature is done only when ALL of the following are true:
1. The target behavior is implemented
2. The required verification actually ran
3. Evidence is recorded in `feature_list.json` or `PROGRESS.md`
4. The repository remains restartable from the standard startup path (`./init.sh`)

---

## End of Session Checklist

Before ending a session:
1. Update `PROGRESS.md`
2. Update `feature_list.json`
3. Record any unresolved risk or blocker
4. Run `CLEAN-STATE-CHECKLIST.md` — all 6 gates must pass
5. Commit with a descriptive message
6. Leave repo clean enough for next session to run `./init.sh` immediately

---

## Startup Protocol

Every new session:
1. `cd .hermes/projects/example_project && ./init.sh`
2. Read `PROGRESS.md` — understand current verified state + next step
3. Read `feature_list.json` — pick highest-priority unfinished feature (status = `pending` or `in_progress`)
4. Run verification for the selected feature — confirm baseline passes FIRST
5. Implement one feature to completion before moving to the next
6. Apply `EVALUATOR-RUBRIC.md` before marking any feature done

---
