---
name: dreaming-sequence
description: "Dreaming Sequence — deep context analysis at 6 AM SGT to prepare the Morning Brief. Analyzes conversation history, goals, projects, calendar, files, and priorities to generate 3 recommendations + 1 non-negotiable action."
version: 1.0.0
author: Baymax / CYBERSLIDE
tags: [morning-brief, context-analysis, planning]
schedule: "0 22 * * *"  # 6:00 AM Singapore Time (UTC+8)
deliver: "local"       # Save output to file for morning-brief to read
platforms: [linux]
---

# Dreaming Sequence

Every morning at **6:00 AM Singapore Time (22:00 UTC)**, this skill runs a deep analysis of Chris's complete context — conversations, goals, projects, calendar, files, and priorities — to generate personalised recommendations for the day ahead.

---

## What This Does

1. **Analyze conversation history** — recent sessions, outstanding commitments, unresolved threads
2. **Query Honcho peer context** — goals, projects, priorities, communication style
3. **Fetch today's calendar** — all scheduled meetings and events via Google Workspace
4. **Scan project files** — `/root/.hermes/projects/` for active work and deliverables
5. **Check Obsidian vault** — LLM Wiki and any notes relevant to current work
6. **Generate 3 high-impact recommendations** — specific, actionable, prioritised
7. **Identify 1 non-negotiable action** — the single task with maximum long-term impact
8. **Save output to `~/.hermes/cron/output/dreaming_sequence.json`** — for morning-brief to consume

---

## Execution Steps

### Step 1 — Session History (last 7 days)

```bash
# Search recent sessions for active projects and commitments
session_search(query="", limit=10, sort="newest")
```

Look for: unfinished tasks, project kick-offs, recent decisions, follow-up items.

### Step 2 — Honcho / Memory Context

Honcho tools (`honcho_context` / `honcho_profile`) may not be exposed in the current agent toolset. **Use the flat-file fallback first** — it's reliable and is the canonical source for this skill's purposes:

```bash
cat /root/.hermes/memories/USER.md   # who the user is, project conventions, comms prefs
cat /root/.hermes/memories/MEMORY.md # durable environment + workflow facts, hard rules
cat /root/.hermes/honcho.json        # confirms peerName (Chris), aiPeer (Baymax)
```

Pull: goals, current projects, priorities, communication preferences, voice routing rules, hard memory rules.

Only invoke `honcho_context(peer="user")` if Honcho tools show up in the available toolset — otherwise the file read covers it.

### Step 3 — Today's Calendar

```bash
GAPI="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/google_api.py"
$GAPI calendar list --start "$(date -u +%Y-%m-%dT00:00:00Z)" --end "$(date -u +%Y-%m-%dT23:59:59Z)"
```

**Expected outcomes and what to do:**
- Empty array `[]` → no events today. Record `"upcoming_deadlines": ["No confirmed deadlines found — calendar returned empty."]`. This is normal, NOT an error.
- Auth failure / token expired → skip the calendar section entirely; do NOT halt the job. Note it under `outstanding_items`.
- Network timeout / non-zero exit → same: skip gracefully, log to `outstanding_items`.

### Step 4 — Project Files Scan

```bash
# List all projects
search_files(pattern="*", target="files", path="/root/.hermes/projects")

# Read project README or brief files if they exist
# Focus on projects with recent activity
```

### Step 5 — Obsidian Vault (LLM Wiki)

```bash
# Check for relevant notes
skill_view(name="llm-wiki-usage")
# Then read recent notes related to current projects
```

### Step 6 — Generate Analysis Output

Based on all gathered data, produce a JSON object:

```json
{
  "date": "YYYY-MM-DD",
  "analysis": {
    "active_projects": ["..."],
    "upcoming_deadlines": ["..."],
    "outstanding_items": ["..."],
    "recent_context": "2-3 sentence summary of what's been happening"
  },
  "recommendations": [
    {
      "priority": 1,
      "title": "...",
      "reason": "...",
      "action": "..."
    },
    {
      "priority": 2,
      "title": "...",
      "reason": "...",
      "action": "..."
    },
    {
      "priority": 3,
      "title": "...",
      "reason": "...",
      "action": "..."
    }
  ],
  "non_negotiable": {
    "title": "...",
    "reason": "...",
    "action": "..."
  },
  "mood_check": "Brief note on energy/tone based on recent context"
}
```

**Field name note:** use `non_negotiable` (single underscore). The template above used `non_-negotiable` which is a typo — the morning-brief consumer reads `non_negotiable`.

### Step 7 — Save to File

```bash
mkdir -p ~/.hermes/cron/output
```

**PITFALL — JSON write method:** Do NOT write the JSON via `terminal` heredoc. The body contains apostrophes/quotes (e.g. "Chris's", contract names) and multi-line `recent_context` paragraphs that break heredoc escaping. This bit a real run on 2026-07-02 — heredoc produced a file that failed JSON validation with `Invalid control character at line X column Y`.

**Correct method:** use `write_file(path, content)` with the entire JSON as a single string body. After write, validate:

```bash
python3 -c "import json; json.load(open('/root/.hermes/cron/output/dreaming_sequence.json'))" && echo OK
```

If validation fails, fall back to `execute_code` with `json.dump(...)` (not available in cron context — same block applies), or in a future context use the `hermes-agent` tool's JSON-aware writer.

---

## Notes

- Always be honest and direct in recommendations — no generic advice
- Recommendations must tie to specific ongoing projects or goals
- The non-negotiable should be something that if skipped, meaningfully delays progress
- Save output BEFORE the job ends — morning-brief depends on this file
- Cron delivers "local" — check `~/.hermes/cron/output/` for the saved JSON
- Date in the JSON must be `$(date +%Y-%m-%d)` (today, SGT-aware at runtime) — not the run timestamp from `cronjob list`