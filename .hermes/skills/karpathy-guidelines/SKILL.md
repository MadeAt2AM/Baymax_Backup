---
name: karpathy-guidelines
description: "Use when writing, reviewing, or refactoring code. Behavioral guidelines that reduce common LLM coding mistakes — overcomplication, unnecessary scope creep, hidden assumptions, weak success criteria. Based on Andrej Karpathy's observations."
version: 1.0.0
author: Baymax (adapted from multica-ai/andrej-karpathy-skills)
license: MIT
metadata:
  hermes:
    tags: [coding, behavior, discipline, karpathy, code-review]
    related_skills: [software-development, requesting-code-review, plan, simplify-code]
---

# Karpathy Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from Andrej Karpathy's observations on LLM coding pitfalls.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment — don't ceremony-up a one-liner.

## When to Use

- Writing new code (any language, any size)
- Reviewing or refactoring existing code
- Planning a multi-step coding procedure
- Debugging a non-trivial bug

**Don't over-apply to:** trivial one-liners, pure research/exploration, or work where the user has explicitly asked for speed over deliberation.

## The Four Guidelines

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Self-check: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: **Every changed line should trace directly to the user's request.**

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan with verify steps:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Application Order

When starting a coding task, apply them in order:

1. **Think** — Have I stated assumptions and surfaced tradeoffs? If unsure, ask.
2. **Plan with verify steps** — Can the operator see what "done" looks like?
3. **Implement** — Minimum code. No speculative features.
4. **Verify** — Tests pass? Live behavior confirmed? (Remember: green tests ≠ user-visible fix — verify end-to-end.)
5. **Surgical cleanup** — Remove only what YOUR changes orphaned.

## Common Pitfalls

1. **Speculative features** — "What if we need X later?" You won't. Cut it.
2. **Asking forgiveness vs. permission** — When truly ambiguous, ask. Don't guess-and-apologise.
3. **Over-abstraction** — Helper for two callers is fine. Helper for one is not.
4. **Hiding assumptions in code** — If you assumed a config value, say so. If you assumed an API returns X, say so.
5. **Weak success criteria** — "It works" is not a criterion. "Test X passes" is.
6. **Tests-green ≠ fixed** — Unit tests can pass while live integration is still broken. Verify end-to-end before declaring done.
7. **Refactoring while fixing** — Keep the fix surgical. Refactors belong in their own change.
8. **Reporting success before verifying the state change** — A common failure pattern: the tool printed "Installed 13 skills," you relay that to the user, and only afterward notice the install was partial / symlinks weren't created / the next session can't load the skill. The success report and the verification probe are the SAME step — verify first, then report. "Installer said it succeeded" is not verification; verification is loading the thing and confirming it works end-to-end. This applies to installs, config changes, system service changes, cron registrations, file writes, symlink creation — any state change that produces a visible side effect. Skill installs in particular: after `npx skills add …`, load every skill with `skill_view` BEFORE telling the user it worked. See the `agent-skills-install` skill for the canonical workflow.
9. **React-table `<TableCell colSpan={N}>` is on both header and body** — when you add a column to a `<Table>` (TanStack Table, shadcn `<Table>`, Mantine, anything based on the same primitive), update `colSpan` in BOTH the empty-state `<TableRow><TableCell colSpan={N}>` AND the loading-state `<TableRow><TableCell colSpan={N}>` in the body. Forgetting one produces a console warning AND a misaligned empty row that scrolls horizontally under the now-wider header. Count once, then change all three.
10. **LSP diagnostics can go stale after large structural edits** — when you wrap a JSX subtree in a new `<div>`, the language server often emits a transient "Unexpected token" error on a line near the bottom of the file, even when the file is structurally balanced. Don't panic-refactor. Counter-check by parsing the source yourself (regex on `<tag …>` vs `</tag>`, or count `{} () []` braces). If structural balance passes AND the affected region closes correctly, the LSP is just lagging. Touch the file with a no-op edit to force reload, or wait for the next save.

## Verification Checklist

- [ ] Assumptions stated explicitly (or operator's intent is unambiguous)
- [ ] Multiple interpretations surfaced, not silently resolved
- [ ] Simpler alternative considered and rejected with reason (if any)
- [ ] Plan stated with checkable verify steps (for multi-step work)
- [ ] Every changed line traces to the user's request
- [ ] No speculative features, no premature abstractions
- [ ] Success criteria are concrete and verified (not "it works")
- [ ] Live end-to-end verification when applicable — not just unit tests
- [ ] For state-change operations (installs, configs, services, symlinks, file writes): a probe that reads back the new state ran BEFORE the success report was sent