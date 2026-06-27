---
name: email-digest-automation
description: "Build scheduled email digest pipelines: pull inbox, classify/prioritise, deliver to Telegram. For recurring briefing jobs, alert pipelines, and inbox monitoring automations."
version: 1.0.0
author: Baymax (CYBERSLIDE)
platforms: [linux]
---

# Email Digest Automation

Build a recurring email briefing that pulls from Gmail, classifies emails by priority, and sends a digest to a Telegram channel on a schedule.

## Reference

- `references/email-briefing-template.py` — the briefing script used for the CYBERSLIDE daily digest (production-tested, ready to adapt)
- Live production script: `/root/.hermes/scripts/email_briefing.py` — **do not copy from references/ into scripts/**; the live script at `/root/.hermes/scripts/email_briefing.py` IS the canonical version and already has the correct `TELEGRAM_CHAT_ID` for Chris's home channel. Copy the reference only when creating a new independent instance.
- `references/telegram-token-troubleshooting.md` — diagnosing and fixing Telegram 401 Unauthorized (token revoked): why polling still works while sends fail, diagnostic commands, and step-by-step fix. **Read this first whenever a Telegram send fails with 401/404.**

## Architecture

```
Gmail API (Google Workspace)
    ↓  gmail search (newer_than:1d, max 30)
Python script (classify + format)
    ↓  Telegram Bot API (sendMessage)
Telegram channel (chat_id)
```

## Prerequisites

1. Google Workspace OAuth configured (`google-workspace` skill, `$GSETUP --check` → AUTHENTICATED)
2. Telegram bot token in `/root/.hermes/.env` as `TELEGRAM_BOT_TOKEN`
3. Bot must be a member of the target channel and have permission to post

## Step-by-step

### 1. Load the reference script

```bash
cat /root/.hermes/skills/productivity/email-digest-automation/references/email-briefing-template.py
```

### 2. Adapt the script

Key values to update in the script:
- `TELEGRAM_CHAT_ID` — target channel/group ID (e.g. `-1004490060634`)
- The `classify_email()` function — adjust priority keywords, add custom senders to flag
- `date_str` format — uses SGT (`UTC+8`); adjust timezone as needed

The script auto-loads `TELEGRAM_BOT_TOKEN` from `/root/.hermes/.env` at runtime — no hardcoding needed.

### 3. Test before scheduling

```bash
python3 /root/.hermes/scripts/email_briefing.py
```

Watch for:
- ✅ "Briefing sent to Telegram" — script worked
- ❌ "HTTP Error 404" — bot token wrong or bot not in channel
- Empty digest (0 chars / "0 emails") — likely using bare `python3` instead of venv Python

**GAPI must use venv Python** in scripts that run outside the agent session:
```python
GAPI = "/root/.hermes/.venv/bin/python3 /root/.hermes/skills/productivity/google-workspace/scripts/google_api.py"
```
Bare `python3` will silently return empty results (no `googleapiclient` in system Python).

### 4. Schedule with cron

```bash
# 11 AM SGT daily (UTC+8 = 03:00 UTC)
cronjob create \
  --name "daily-email-briefing" \
  --prompt "Run the daily email briefing script and send the digest to Telegram..." \
  --schedule "0 3 * * *" \
  --deliver "none"
```

The script handles Telegram delivery internally. Set `deliver: none` on the cron — the script is the delivery agent, not the cron.

## Email Classification Logic

The `classify_email()` function assigns flags based on keyword matching across subject + snippet + sender:

| Flag | Trigger keywords |
|------|-----------------|
| ⚠️ urgent | urgent, asap, critical, emergency, important |
| 📌 needs reply | reply, action, please respond, let me know, your thoughts |
| 💰 financial | invoice, payment, receipt, bill, due |
| 📅 invite/event | meeting, invite, calendar, scheduled |
| 🔒 security | security, alert, sign-in, 2-step |

Sort order: urgent → needs reply → financial → events → security → other.

## Pitfalls

1. **Bare `python3` returns empty Gmail results** — `googleapiclient` is only in `/root/.hermes/.venv`. Always use venv Python in standalone scripts.
2. **Telegram 401 Unauthorized on send** — bot token is invalidated (revoked, expired, or regenerated via @BotFather). Verify with the Python probe above (never curl with a masked/token-containing URL — bash glob expansion corrupts `***` patterns). If 401: get a fresh token from `@BotFather` (`/newbot` or `/revoke`). After replacing the token in `.env`, restart the gateway with `hermes gateway restart`. **NEVER use `sed` or shell substitution to edit `.env` tokens** — the file contains masked values that bash expands as globs, and the `***` pattern will corrupt lines. Use Python file I/O only.
3. **Telegram 404 on send** — bot not added to channel, wrong `TELEGRAM_BOT_TOKEN`, or wrong `TELEGRAM_CHAT_ID`. Verify bot is in channel and `chat_id` is correct.
4. **No emails found** — `newer_than:1d` searches from ~24h ago. Adjust to `newer_than:2d` if inbox is low-traffic.
5. **Channel ID wrong sign** — supergroups use negative IDs with `-100` prefix, e.g. `-1003825565541` (MadeAt2Am home channel). Private channels use plain negative integers.
6. **Script has stale `TELEGRAM_CHAT_ID` hardcoded** — the live script at `/root/.hermes/scripts/email_briefing.py` is the canonical version. The reference template in `references/` may be outdated. Always use the live script path, not a copied reference. The correct home channel for Chris is `-1003825565541` (Baymax_Home, a supergroup). A wrong ID like `-1004490060634` will silently fail to deliver.

## Verification

After scheduling, manually trigger the cron to confirm end-to-end delivery:
```bash
cronjob run --job_id <job_id>
```
