# Cross-Host Service Health Probe (06:00 SGT, read-only)

## Purpose

Catch **overnight drift on remote production hosts** before the morning brief goes out. Distinct from the local watchdog pattern in `references/service-watchdog-pattern.md`: this probe runs once a day, from a different host (the Hermes Agent host, not the production host itself), and reports read-only HTTP status for each known production URL.

It is the only signal that catches "Payntra is 502" before Chris hits it at 09:00 SGT — session history shows what was *worked on*, not what *broke while nobody was looking*.

## When to run

This is a 06:00 SGT cron job (the **dreaming-sequence** skill owns it as Step 3.5). Do not duplicate it in the 15-min resource monitor or the per-service watchdog — those catch different signals.

## SSH prerequisite

Production hosts must be reachable from the Hermes host via passwordless SSH (key auth, configured in `~/.ssh/`). If SSH fails, the probe reports "host unreachable" and the brief flags it as VPS-level, not app-level.

Example alias for the dev VPS (Hetzner Helsinki):
```bash
ssh -i /root/.ssh/baymax_dev_vps -o BatchMode=yes -o ConnectTimeout=8 deploy@147.79.18.32
```

## Probe Recipe

```bash
# Run from the Hermes host. One curl per known prod URL.
ssh -i ~/.ssh/baymax_dev_vps -o BatchMode=yes -o ConnectTimeout=8 deploy@147.79.18.32 \
  "for u in payntra.terrybot.top openreply.terrybot.top syntra.terrybot.top; do \
     echo \"=== \$u ===\"; \
     curl -fsS -o /tmp/h -w '%{http_code}\n' https://\$u/api/health 2>&1 || echo DOWN; \
   done"
```

## What the codes mean

| Code | Meaning | Brief action |
|------|---------|--------------|
| HTTP 200 | Service responding | Log as "X is healthy as of HH:MM SGT" |
| HTTP 502 | Caddy upstream error — proxy up, backend down | Flag in `outstanding_items`; likely stale upstream port or dead backend container |
| HTTP 503 | Service unavailable | Same as 502; check service health from VPS side |
| HTTP 504 | Gateway timeout | Backend unreachable from proxy; check firewall/network/MTU |
| Connection refused | Port closed locally | VPS issue or app container crashed; SSH in and `docker ps` |
| DNS / curl unreachable | Host-level outage | Flag the host (VPS issue, not app) |

## Why this is read-only, not auto-repair

The dreaming-sequence is a *preparation* run for the morning brief — it does not take action. Auto-restarting a neighbour app from a 06:00 SGT cron is a footgun: it would silence real outages behind silent reboots and lose forensic context. Surface the 502 in the brief, let Chris (or the morning Baymax session) decide the fix.

The auto-repair pattern is the local watchdog (per-host, every 5 min). This probe is a *reporting* pattern (cross-host, daily).

## Output integration with dreaming-sequence

The probe output goes into two fields of `~/.hermes/cron/output/dreaming_sequence.json`:

- **HTTP 200 results** → `analysis.active_projects` — append "(X is healthy as of HH:MM SGT)" to the relevant project entry
- **Non-200 / unreachable results** → `outstanding_items` — flag the URL + last-known-good state + likely cause

Always run this step before generating the JSON. Without it, the brief is built on session history alone and misses silent overnight failures.

## Current prod URLs (as of 2026-07-31)

| URL | What it is | Health path |
|-----|-----------|-------------|
| `https://payntra.terrybot.top` | Personal expense ledger | `/api/health` |
| `https://openreply.terrybot.top` | IG comment→DM automation | `/api/health` |
| `https://syntra.terrybot.top` | Multi-tenant workforce SaaS | `/api/health` |

Add new entries here when a new app ships to production so the probe covers it.

## Pitfalls

- **Don't run the probe from inside the dream loop's heredoc** — bash escaping for the inner `for u in` is fragile. Use `execute_code` (Python wrapper) or write the script to a tempfile and `bash <file>` if you need a clean run.
- **Probe timeout too short** — `ConnectTimeout=8` is tight but acceptable for a known-good production host. If you see sporadic `Connection refused` that flips back to 200 on re-run, bump to 15s and add a single retry inside the loop.
- **Missing `BatchMode=yes`** — without it, the probe hangs waiting for a password prompt when the key is missing. Always include it.
- **Treating 200 with broken body as healthy** — `curl -fsS` only checks HTTP code. For apps that return `{"status":"ok"}` with broken sub-checks (e.g. `db:down`), inspect the body too: `curl -fsS https://X/api/health | jq .checks`. The OpenReply health endpoint returns `db.status` / `redis.status` / `worker.healthy` separately — all three must be ok to call it healthy.
- **Stale URL list** — if a new app ships to production and the URL isn't in the loop, its drift goes unreported. Review the list when adding new prod apps.

## Related

- `dreaming-sequence` (Step 3.5) — owner of the daily run
- `references/service-watchdog-pattern.md` — local-host auto-restart watchdog (different scope)
- `morning-brief` — consumer of the JSON this probe contributes to