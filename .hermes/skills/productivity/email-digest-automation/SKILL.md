---
name: email-digest-automation
description: "Build scheduled email digest pipelines that pull from Gmail and deliver to Telegram. For recurring briefing jobs, alert pipelines, and inbox monitoring automations. Two architectures supported: LLM-driven (script emits --json, agent + inbox-triage skill does classification and reply-drafting) and legacy keyword-driven (script does it all in --pretty mode)."
version: 1.1.0
author: Baymax (CYBERSLIDE)
platforms: [linux]
---

# Email Digest Automation

Build a recurring email briefing that pulls from Gmail and delivers a digest to a Telegram channel. Two architectures are supported — pick by complexity:

- **LLM-driven (recommended, production):** Python script fetches raw emails in `--json` mode; a scheduled agent loads the `inbox-triage` skill, classifies into ACTION / WAIT / ARCHIVE, drafts 3-sentence replies for ACTION items, and posts the table. Reasoning happens in the agent, not the script.
- **Keyword-driven (legacy, low-traffic only):** Python script does classification + HTML formatting + Telegram send in `--pretty` mode. No LLM in the loop.

The two share the same fetch + auth + Telegram plumbing; only the classification + output layer differs. **For new builds, default to LLM-driven** — the legacy keyword classifier hides personal threads (rule 3 of the `inbox-triage` skill) and the new model fixes that.

## Reference

- Live production script: `/root/.hermes/scripts/email_briefing.py` — canonical version. Two output modes:
  - `--pretty` (default): grouped HTML digest, sent to Telegram by the script itself. Use for ad-hoc human runs or simple low-traffic cron jobs.
  - `--json`: emits `{fetched_at, count, emails: [...]}` to stdout. **The LLM-driven cron uses this mode** — the agent then loads `inbox-triage` and formats the table.
  The script also has a `legacy_flags` field in the JSON output so the LLM can see what the old keyword classifier thought, without being bound by it.
- `inbox-triage` skill at `/root/.hermes/skills/productivity/inbox-triage/SKILL.md` — the LLM-side classifier. **Load it from the cron prompt** with `skill_view(name='inbox-triage')` and follow it. Defines the ACTION / WAIT / ARCHIVE buckets, the 3-sentence draft format, and the "default to ACTION for human senders" guardrail.
- `references/telegram-token-troubleshooting.md` — diagnosing and fixing Telegram 401 Unauthorized (token revoked): why polling still works while sends fail, diagnostic commands, and step-by-step fix. **Read this first whenever a Telegram send fails with 401/404.**
- `references/dual-mode-script-pattern.md` — why and how to split a digest script into `--json` (LLM-consumable) and `--pretty` (human-consumable) output modes. The pattern that lets a keyword-driven pipeline evolve into an LLM-driven one without breaking ad-hoc human runs.

> **Note:** Earlier versions of this skill referenced `references/email-briefing-template.py`. That file does not exist and has been removed from the skill — the live script at `/root/.hermes/scripts/email_briefing.py` is the only source of truth. If you need a starting point, copy that live script and adapt the constants.

## Architecture

### LLM-driven (production, current)

```
Gmail API (Google Workspace)
    ↓  gmail search (newer_than:1d, max 30)
Python script: email_briefing.py --json
    ↓  JSON to stdout
Scheduled agent (cron)
    ↓  loads inbox-triage skill, classifies, drafts replies
Markdown table → Telegram channel (auto-delivered by platform)
```

### Keyword-driven (legacy, retained for ad-hoc human use)

```
Gmail API (Google Workspace)
    ↓  gmail search (newer_than:1d, max 30)
Python script: email_briefing.py --pretty
    ↓  grouped HTML digest
Telegram Bot API (sendMessage)
    ↓
Telegram channel (chat_id)
```

## Prerequisites

1. Google Workspace OAuth configured (`google-workspace` skill, `$GSETUP --check` → AUTHENTICATED)
2. Telegram bot token in `/root/.hermes/.env` as `TELEGRAM_BOT_TOKEN`
3. Bot must be a member of the target channel and have permission to post

## Step-by-step — LLM-driven (production path)

### 1. Adapt the data-fetcher script

The script lives at `/root/.hermes/scripts/email_briefing.py`. For a new instance, copy that file and update:
- `TELEGRAM_CHAT_ID` in the script only matters for `--pretty` mode (the LLM-driven cron doesn't use it). For a new LLM-driven cron, leave the default or set to your own.
- `GAPI` — path to the Google API helper. Only change if your venv lives elsewhere.
- The `classify_email()` function is the **legacy keyword classifier** — used by `--pretty` mode only. The LLM-driven path emits the same flags as hints via `legacy_flags`, but the agent does its own classification per the `inbox-triage` skill.

The script auto-loads `TELEGRAM_BOT_TOKEN` from `/root/.hermes/.env` at runtime — no hardcoding needed.

### 2. Test the JSON output

```bash
/root/.hermes/.venv/bin/python3 /root/.hermes/scripts/email_briefing.py --json | head -40
```

Watch for:
- ✅ Valid JSON with `count: N` and `emails: [...]` — script worked
- ❌ `count: 0` — either no emails in the last 24h, OR you're using bare `python3` instead of venv Python (googleapiclient is only in the venv; bare `python3` silently returns empty results)
- ❌ Non-zero exit / parse error — check the stderr trace

### 3. Schedule the cron with the inbox-triage skill

```bash
cronjob create \
  --name "daily-email-briefing" \
  --skills "inbox-triage" \
  --prompt "..." \
  --schedule "0 3 * * *" \
  --deliver "telegram:-1003825565541"
```

The cron prompt must:
1. Run `/root/.hermes/.venv/bin/python3 /root/.hermes/scripts/email_briefing.py --json` and read the JSON.
2. Load `inbox-triage` via `skill_view(name='inbox-triage')` and follow it.
3. Classify every email into ACTION / WAIT / ARCHIVE per the skill's bucket rules.
4. Draft 3-sentence replies for ACTION rows only (em-dash for others).
5. Output exactly one Markdown table with header `| From | Subject | Bucket | Draft reply |`.
6. If `count: 0`, post a single "no emails in last 24h" line and stop. **Never fabricate emails.**
7. Set `deliver` to the target Telegram chat. The platform layer handles final delivery from the agent's response.

See `/root/.hermes/cron/output/5d79aefd3746/` for a live production example of the rendered prompt and the resulting run.

### 4. Verify end-to-end

```bash
cronjob run --job_id <job_id>
```

Then check Telegram. The cron run produces a session log at `/root/.hermes/cron/output/<job_id>/<timestamp>.md` — read it to see the actual skill content loaded and the agent's final response, even if Telegram delivery failed. This is your best diagnostic when the brief doesn't show up.

**If `count: 0`**, the agent should output `[SILENT]` and the platform suppresses the post. That's the correct behaviour — do not treat a silent run as a failure.

## Step-by-step — Keyword-driven (legacy)

For simple digests where LLM reasoning is overkill, the legacy path still works:

### 1. Run the script in pretty mode

```bash
python3 /root/.hermes/scripts/email_briefing.py
```

The script handles classification, formatting, and Telegram send in one shot. Use this for ad-hoc human runs.

### 2. Schedule (if needed)

The legacy cron used `deliver: none` because the script sent the Telegram message itself. With the LLM-driven path, prefer the architecture in "LLM-driven" above — the legacy cron path is preserved in the older prompt structure and remains supported for low-traffic keyword-only digests.

## Classification — current and legacy

### inbox-triage skill (LLM-driven, current)

ACTION / WAIT / ARCHIVE buckets with a 3-sentence draft reply for every ACTION item. **Default to ACTION for human senders** — the legacy keyword model hid personal threads, this one surfaces them. See `inbox-triage` skill for the full bucket rules, security carve-out, and "needs your call" pattern for ambiguous items.

### Legacy 5-flag keyword classifier (`--pretty` mode only)

The `classify_email()` function assigns flags based on keyword matching across subject + snippet + sender:

| Flag | Trigger keywords |
|------|-----------------|
| ⚠️ urgent | urgent, asap, critical, emergency, important |
| 📌 needs reply | reply, action, please respond, let me know, your thoughts |
| 💰 financial | invoice, payment, receipt, bill, due |
| 📅 invite/event | meeting, invite, calendar, scheduled |
| 🔒 security | security, alert, sign-in, 2-step |

Sort order: urgent → needs reply → financial → events → security → other.

**This classifier is kept only for `--pretty` mode and as hints in `--json` output. Do not extend it for new use cases — build a new LLM-driven pipeline instead.**

## Pitfalls

1. **Bare `python3` returns empty Gmail results** — `googleapiclient` is only in `/root/.hermes/.venv`. Always use venv Python in standalone scripts.
2. **Telegram 401 Unauthorized on send** — bot token is invalidated (revoked, expired, or regenerated via @BotFather). Verify with the Python probe in `references/telegram-token-troubleshooting.md` (never curl with a masked/token-containing URL — bash glob expansion corrupts `***` patterns). If 401: get a fresh token from `@BotFather` (`/newbot` or `/revoke`). After replacing the token in `.env`, restart the gateway with `hermes gateway restart`. **NEVER use `sed` or shell substitution to edit `.env` tokens** — the file contains masked values that bash expands as globs, and the `***` pattern will corrupt lines. Use Python file I/O only.
3. **Telegram 404 on send** — bot not added to channel, wrong `TELEGRAM_BOT_TOKEN`, or wrong `TELEGRAM_CHAT_ID`. Verify bot is in channel and `chat_id` is correct.
4. **No emails found** — `newer_than:1d` searches from ~24h ago. For LLM-driven runs, `count: 0` is the correct silent-run case — the agent will output `[SILENT]` and the post is suppressed. Don't fabricate emails to "fill" the brief. For keyword-driven runs that are always empty, adjust to `newer_than:2d` if inbox is low-traffic.
5. **Channel ID wrong sign** — supergroups use negative IDs with `-100` prefix, e.g. `-1003825565541` (MadeAt2Am home channel). Private channels use plain negative integers.
6. **Script has stale `TELEGRAM_CHAT_ID` hardcoded** — the live script at `/root/.hermes/scripts/email_briefing.py` is the canonical version. The correct home channel for Chris is `-1003825565541` (Baymax_Home, a supergroup). A wrong ID like `-1004490060634` will silently fail to deliver.
7. **LLM-driven cron declares "fixed" on unit tests alone** — the LLM-driven path is reasoning, not deterministic code, so unit tests don't exist. The real verification is end-to-end: trigger the cron, then read the session log at `/root/.hermes/cron/output/<job_id>/<timestamp>.md` AND check the Telegram channel. The log shows the actual skill content loaded and the agent's final response — invaluable when Telegram delivery is the failure mode.
8. **Cron prompt doesn't load the `inbox-triage` skill explicitly** — without `skill_view(name='inbox-triage')` in the prompt, the agent will fall back to the legacy 5-flag logic in the script's `legacy_flags` field and produce a degraded table. Always pass `--skills "inbox-triage"` on `cronjob create` and tell the prompt to load it.
9. **Cron prompt recurses into scheduling more jobs** — cron runs should not create other cron jobs. If a briefing triggers a follow-up action, deliver it as a one-shot command or note for the next session, not a new schedule.
10. **Treating `count: 0` as a failure** — it's not. The agent outputs `[SILENT]`, the platform suppresses delivery, and the cron job is recorded as `ok`. Don't change the script to "always post something."

## Verification

After scheduling, manually trigger the cron to confirm end-to-end delivery:

```bash
cronjob run --job_id <job_id>
```

Then check **both**:
1. The Telegram channel — confirm the table landed in the right chat_id.
2. The cron session log at `/root/.hermes/cron/output/<job_id>/<timestamp>.md` — confirms what skill was loaded, what the agent produced, and what was sent. This is your primary diagnostic surface when the brief doesn't show up in Telegram.

For the LLM-driven path, "tests pass" doesn't apply — reasoning isn't testable in unit-test form. Live end-to-end verification is the only signal.
