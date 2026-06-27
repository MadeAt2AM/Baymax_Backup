# EVALUATOR-RUBRIC.md

Apply this rubric after implementation and before final acceptance of any feature.

---

## Rubric

| Category | Question | Score | Notes |
|---|---|---|---|
| **Correctness** | Does the implemented behavior match the requested feature? | 0 / 1 / 2 | 0=broken, 1=partial, 2=fully correct |
| **Verification** | Did the required checks actually run, with evidence? | 0 / 1 / 2 | 0=none, 1=partial, 2=complete with output |
| **Scope discipline** | Did the session stay inside the chosen feature scope? | 0 / 1 / 2 | 0=scope creep, 1=slight drift, 2=clean scope |
| **Reliability** | Does the result survive restart or rerun without repair? | 0 / 1 / 2 | 0=fails on rerun, 1=fragile, 2=robust |
| **Maintainability** | Is the code and documentation clear enough for the next session? | 0 / 1 / 2 | 0=confusing, 1=readable, 2=self-documenting |
| **Handoff readiness** | Can a fresh session continue work from repo artifacts only? | 0 / 1 / 2 | 0=needs chat context, 1=mostly, 2=fully self-contained |

---

## Scoring Guide

- **10-12:** Accept — feature is complete and production-ready
- **7-9:** Revise — minor fixes needed, re-evaluate after changes
- **4-6:** Block — significant issues, do not mark done until fixed
- **0-3:** Reject — fundamental problems, rework from scratch

**Minimum per-category to accept:** No single category below 1.

---

## Verdict

| Decision | When |
|---|---|
| **Accept** | Score ≥7, no category below 1 |
| **Revise** | Score 4-6, or any category = 0 |
| **Block** | Score 0-3, or multiple categories = 0 |

---

## Required Follow-Up

If **Revise** or **Block**:

- **Missing evidence:** List exactly what verification is missing
- **Required fixes:** Numbered list of concrete changes needed
- **Next review trigger:** What event/action re-triggers evaluation (e.g., "run `./init.sh` after fix")

---

## Example Entry

| Feature | F3 — cross-platform-trend-intelligence skill | Evaluator | OWL |
|---|---|---|---|
| Correctness | 2 | Both platforms scanned, structured report produced | |
| Verification | 2 | Skill ran without error, 5 trends returned with scores | |
| Scope discipline | 2 | No scope creep, only trend intelligence scope | |
| Reliability | 1 | YouTube API sometimes times out — needs retry logic | |
| Maintainability | 2 | Well-documented skill file with clear steps | |
| Handoff readiness | 2 | All context in skill file + feature_list.json | |
| **Total** | **11/12** | **Accept** | |

**Required fixes:** Add retry logic (1 attempt) for YouTube API timeout. Next review trigger: next cron run.

---