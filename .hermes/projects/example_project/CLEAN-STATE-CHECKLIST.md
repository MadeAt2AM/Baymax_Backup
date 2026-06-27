# CLEAN-STATE-CHECKLIST.md

Run this checklist before ending every session. All 6 gates must pass.

---

## Pre-Flight Checks

- [ ] **The standard startup path still works.**
  Run: `cd .hermes/projects/example_project && ./init.sh`
  Expected: Exit 0, all checks pass.

- [ ] **The standard verification path still runs.**
  Run: `python3 -c "import json; json.load(open('feature_list.json')); print('valid')"`
  Expected: "valid" printed, no errors.

- [ ] **Current progress is recorded in the progress log.**
  Run: `grep -c "Session [0-9]" PROGRESS.md`
  Expected: ≥1 (at least one session logged).

- [ ] **Feature state reflects what is actually passing versus unverified.**
  Run: Check feature_list.json — any feature with status=`in_progress` must have evidence field populated.
  Any status=`done` must have passed the EVALUATOR-RUBRIC.

- [ ] **No half-finished step is left undocumented.**
  Run: Check PROGRESS.md for any feature marked "in_progress" that has no corresponding entry in the session log.
  If found: either complete it or document it as "blocked" with reason.

- [ ] **The next session can continue without manual repair.**
  Run: `cd .hermes/projects/example_project && git status 2>/dev/null` (if git initialized)
  Or: verify all created/modified files are in place via `ls -la`.

---

## Gate Criteria

All 6 must be ✅ before committing and ending session.

If any gate fails:
- **Gates 1-2:** Fix the broken path immediately before ending.
- **Gates 3-5:** Update the relevant document(s) until the check passes.
- **Gate 6:** Verify file presence manually.

---

## End-of-Session Summary

After passing all 6 gates, record:

```
Session: [N]
Date: [YYYY-MM-DD]
Features completed this session: [F#] — [name]
Features in progress: [F#] — [name]
Sprint status: [Sprint X — X/6 features complete]
Blocked features: [F#] — [reason]
Next session: Start with [F#]
```

Commit message format:
```
example_project: Sprint X session [N] — [brief description of changes]

Completed: F1, F2
In progress: F3 (blocked by X API registration)
```

---

Last updated: 2026-05-21