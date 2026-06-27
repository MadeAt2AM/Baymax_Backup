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

### Step 2 — Honcho Context

```bash
honcho_context(peer="user")
honcho_profile(peer="user")
```

Pull: goals, current projects, priorities, communication preferences.

### Step 3 — Today's Calendar

```bash
GAPI="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/google_api.py"
$GAPI calendar list --start "$(date -u +%Y-%m-%dT00:00:00Z)" --end "$(date -u +%Y-%m-%dT23:59:59Z)"
```

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
  "non_-negotiable": {
    "title": "...",
    "reason": "...",
    "action": "..."
  },
  "mood_check": "Brief note on energy/tone based on recent context"
}
```

### Step 7 — Save to File

```bash
mkdir -p ~/.hermes/cron/output
# Write the JSON output to ~/.hermes/cron/output/dreaming_sequence.json
```

---

## Notes

- Always be honest and direct in recommendations — no generic advice
- Recommendations must tie to specific ongoing projects or goals
- The non-negotiable should be something that if skipped, meaningfully delays progress
- Save output BEFORE the job ends — morning-brief depends on this file
- Cron delivers "local" — check `~/.hermes/cron/output/` for the saved JSON