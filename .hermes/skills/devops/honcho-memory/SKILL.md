---
name: honcho-memory
description: "Honcho memory backend for Hermes: API structure, tool usage, server status probes, and integration config."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [memory, honcho, persistent-memory, profile, recall]
    related_skills: [hermes-agent]
---

# Honcho Memory

Honcho is the active memory provider for this host (Chris / Baymax, workspace `baymax-core`).

## Integration Config

Config file: `~/.hermes/honcho.json`

```json
{
  "hosts": {
    "hermes": {
      "peerName": "Chris",
      "aiPeer": "Baymax",
      "workspace": "baymax-core",
      "observationMode": "directional",
      "writeFrequency": "async",
      "recallMode": "hybrid",
      "dialecticCadence": 2,
      "dialecticReasoningLevel": "max",
      "sessionStrategy": "per-directory",
      "enabled": true,
      "saveMessages": true
    }
  },
  "baseUrl": "https://honcho.madeat2am.in"
}
```

## Provider Config

In `~/.hermes/config.yaml`:

```yaml
provider: honcho
honcho: {}
memory:
  provider: honcho
  memory_enabled: true
  user_profile_enabled: true
```

## Available Honcho Tools

These are called directly by name (not via terminal):

- **`honcho_profile`** — returns user profile facts. First turn returns empty state (no facts accumulated yet). Accumulation is cadence-driven.
- **`honcho_search`** — FTS5 search over raw conversation excerpts. Optional `peer` filter (e.g., `user`). Returns match excerpts with session context.
- **`honcho_reasoning`** — synthesized answers from raw conversation data. Takes `query` + `reasoning_level` (minimal/low/medium/high/max).
- **`honcho_conclude`** — save a durable fact about the user or environment.
- **`honcho_context`** — raw peer context injection (used by dialectic layer).

## Known API Routes (honcho.madeat2am.in, API v3)

**Auth:** All `/v3/` routes require `Authorization: Bearer $HONCHO_API_KEY`. The key is set in `~/.hermes/.env` as `HONCHO_API_KEY=HONCHO...L9Q8`. Source it with `source ~/.hermes/.env` before calling curl.

**Workspace-scoped base:** `/v3/workspaces/{workspace_id}/...`

| Route | Method | Auth | Response |
|-------|--------|------|----------|
| `/health` | GET | None | `{"status":"ok"}` |
| `/v3/workspaces` | POST | Key | Create/get workspace by `id` field |
| `/v3/workspaces/list` | POST | Key | List all workspaces |
| `/v3/workspaces/{workspace_id}` | GET | Key | Get workspace details |
| `/v3/workspaces/{workspace_id}/peers/list` | POST | Key | List all peers (e.g., Chris, Baymax) |
| `/v3/workspaces/{workspace_id}/peers/{peer_id}/card` | GET | Key | Peer card (usually `null` on fresh workspace) |
| `/v3/workspaces/{workspace_id}/peers/{peer_id}/context` | GET | Key | Peer context/representation (usually empty on fresh workspace) |
| `/v3/workspaces/{workspace_id}/sessions/list` | POST | Key | List sessions |
| `/` | GET | None | 404 (not a web UI) |

**Auth note:** All routes require `Authorization: Bearer $HONCHO_API_KEY`. Source it with `source ~/.hermes/.env` before calling curl.

## Tool Behavior Notes

- `honcho_profile` returns `{"No profile facts available yet."}` on a fresh workspace — this is normal, not an error. Peer cards accumulate over time via dialectic reasoning.
- `honcho_search` returns `{"No relevant context found."}` when FTS5 returns no hits — this is normal, not an error.
- `honcho_context` returns peer context with `representation: ""` and `peer_card: null` on fresh workspaces — this is normal until enough conversation turns have occurred.
- honcho tools do NOT require API key authentication in the request — auth is handled by the Hermes honcho plugin integration internally.
- Terminal-based honcho CLI (`which honcho`) is NOT installed on this host — the honcho integration is plugin-based only (Python package not required).
- The HONCHO_API_KEY in `~/.hermes/.env` is the actual key, not a placeholder — it must be sourced before using curl directly against the API.

## Session Strategy

- `sessionStrategy: per-directory` — each directory gets its own session context.
- `recallMode: hybrid` — combines FTS5 search with generated reasoning.
- `dialecticCadence: 2` + `dialecticReasoningLevel: max` — dialectic reasoning runs every 2 turns at max depth.

## Telegram Integration Notes

**Telegram bot token required for notification crons.** When creating a cron that sends messages to Telegram (via `deliver='telegram'` or direct bot API calls), the bot token must be explicitly provided by the user — it is NOT auto-discovered from config. Workflow:
1. Ask for the bot token before scheduling the cron
2. If not immediately available, halt and request it — do not search extensively through config files
3. Tokens look like `123456789:ABCDefGhIJKlmNoPQRsTUVwxYZ`

**Known Telegram channel IDs for this deployment:**
- Chris's home channel: `-1003825565541`
- Additional channels discovered during session: store in memory as they arise

## User Preferences (Chris / MadeAt2Am)

- **Direct style only** — short sentences, no fluff, no lengthy status reports. When asked to do something, just do it or confirm the approach. Do not respond with verbose multi-section status reports unless explicitly requested.
- **No over-explaining** — if a task is simple, the answer should be simple. Only elaborate when the situation genuinely warrants it.
- **Memory compression** — when memory is running high (>85%), compress aggressively. Cron IDs, script paths, systemd service names, and verbose technical descriptions are rediscoverable via `cronjob list`, skill files, or config on disk. Lean summaries are preferred over exhaustive detail in the memory block.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `honcho_profile` returns empty on turn 1 | Fresh workspace, no facts yet accumulated | Normal — facts accumulate over session turns |
| All honcho tools return auth errors | Honcho plugin not loaded | Check `hermes honcho status` |
| Server unreachable | Network or server outage | `curl -s https://honcho.madeat2am.in/health` |
| 404 on every route except /health | Route not implemented or wrong API version | Use `/v3/` routes, check `/health` to confirm server is up |
| `honcho_context` returns `representation: ""` and `peer_card: null` | Workspace has no accumulated dialectic data yet | Normal on fresh workspace — accumulates via conversation turns |
| `honcho_profile` says "No peer data yet" | Peer card not yet built | Normal — dialectic layer builds peer cards over time |
| `hermes honcho status` shows API key but API calls fail with 404 | Wrong API version path used | Use `/v3/` prefix, not `/v1/` — the v3 routes are workspace-scoped |
| `memory` tool `replace` action fails with "no entry matched" | Auth layer returns a different string than the system prompt shows | Read the actual file at `/root/.hermes/memories/MEMORY.md` via `read_file`, then patch it directly with the `patch` tool using the real content. The system prompt string and the live memory file can diverge. |