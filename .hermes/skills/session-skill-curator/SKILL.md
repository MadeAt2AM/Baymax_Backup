---
name: session-skill-curator
description: Run a post-session skill-library audit. Decide per signal whether the lesson belongs in a current skill, a support file under an umbrella, or a new class-level umbrella. Use at the end of any session with non-trivial work, corrections, or new techniques — especially VPS/deploy work, install/scaffold sessions, or any task where the user pushed back on style or workflow. Trigger on phrases like "update skills", "audit the skill library", "what did we learn", or after any sub-agent completion where richer context is available.
category: meta
version: 1.0.0
---

# Session Skill Curator

## When to Use

After any session that:
- Used 5+ tool calls to solve a problem
- Ended with a workaround, technique, or debugging recipe
- Heard a correction from the user about style, format, tone, verbosity, or sequencing
- Touched infrastructure where future sessions would benefit from the file paths, secrets layout, or lay-of-the-land specifics

Skip only when the session was a one-off lookup (date lookup, currency conversion, simple Q&A).

## Audit Procedure

1. **Diff the conversation against the loaded skill(s)** — any skill opened via `skill_view`. If a pitfall surfaced that wasn't covered, that's priority-1: patch that skill's SKILL.md.
2. **Diff the conversation against the umbrella skills in the class** — use `skills_list`. Pick the umbrella whose `description:` matches. Add a subsection / pitfall / step.
3. **Diff the conversation against support files** — `templates/`, `scripts/`, `references/`. If a one-shot script kept being re-invoked, that's a script candidate. If a config blob was reconstructed from memory, that's a template candidate.
4. **Only create a new class-level umbrella if no existing one fits.** Named narrowly (one-session-one-fix) is always wrong — that becomes a memory fact, not a skill.

## What to Embed vs What to Memory

## What to Embed vs What to Memory

| Goes in skill body | Goes in memory |
|---|---|
| "Always do X before Y" | "User lives in SGT" |
| "Pitfall Z silently breaks step N" | "Token has webhook-write perm" |
| "When user says 'push', execute procedure F" | "VPS is at 147.79.18.32" |
| "Format responses as Markdown tables for K/V data" | "Project at /root/projects/<name>" |

Skill body = how to do this class of work for this user. Memory = who the user is and current state. If the user complained about *how* you did something, the skill carries the lesson. If the user said something true about their environment, memory captures it.

## Pitfall Catalogue — common mistakes to avoid

### A. Capture environment failures as skill rules

WRONG: skill says "webhook binary is not installed on dev VPS — use the API instead"
RIGHT: skill says "install webhook via `apt-get install -y webhook` (Ubuntu 24.04 has it in universe); if not present, capture step in setup checklist, not as a permanent constraint"

Environment snapshots go stale. Install commands stay useful.

### B. Negative claims about tools

WRONG: "the shell guard blocks force-push, so don't try to push — that won't work"
RIGHT: "force-push and delete-repo trigger the shell safety filter; need explicit user confirmation via `clarify` before invoking either"

Capture the FIX path, not the inability.

### C. Session-narrative skills

WRONG: create `fix-probe-pipeline-2026-07-03` as a skill
RIGHT: that lesson lives in the deploy skill's pitfall section

If a future agent needs the lesson, they shouldn't have to know it's dated 2026-07-03.

### D. One-off corrections without generalizability

WRONG: skill says "Chris prefers metric units over imperial"
RIGHT: skill says "default to user's locale units; infer from MEMORY.md `.hermes/SOUL.md` operator profile"

Capture the abstract rule, not the specific instance.

## Where to Find Existing Umbrellas

- `skills_list` — full catalogue, filtered by category if needed
- For devops / deploy / VPS tasks: `devops/vps-container-deploy/` is the current umbrella
- For project organization / folder conventions: hit `agent-skills-install`, `project-initialization`
- For HermeS-specific config: `hermes-agent-skill-authoring`

Always check the relevant umbrella before adding a new skill.

## Output Format

After the audit, produce a one-paragraph report listing:
- Skill(s) patched (with the pitfall/section added)
- Support file(s) added (with path + reason)
- Any "Nothing to save" (with the reason — short sessions with no new learnings)