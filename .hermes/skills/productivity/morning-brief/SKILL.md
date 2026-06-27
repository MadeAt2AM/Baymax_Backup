---
name: morning-brief
description: "Daily Morning Brief — compiled at 8:00 AM SGT from dreaming-sequence output. Fetches weather, quote, calendar, recommendations and sends a polished brief to Telegram channel -1004490060634."
version: 1.0.0
author: Baymax / CYBERSLIDE
tags: [morning-brief, daily-brief, telegram, weather, calendar]
schedule: "0 0 * * *"  # 8:00 AM Singapore Time (UTC+8)
deliver: "telegram:-1004490060634"
platforms: [linux]
---

# Daily Morning Brief

Every day at **8:00 AM Singapore Time (00:00 UTC)**, this skill compiles and sends a polished Morning Brief to **Telegram channel `-1004490060634`**.

---

## What This Does

1. **Read the dreaming-sequence output** from `~/.hermes/cron/output/dreaming_sequence.json`
2. **Fetch Singapore weather** for today (via wttr.in or similar free API)
3. **Select a motivational quote** from a world-class entrepreneur
4. **Fetch today's calendar** events from Google Workspace
5. **Compile the full brief** with all sections
6. **Send to Telegram** channel `-1004490060634`

---

## Execution Steps

### Step 1 — Read Dreaming Sequence Output

```bash
cat ~/.hermes/cron/output/dreaming_sequence.json
```

If the file doesn't exist or is empty, use fallback values:
- `recommendations`: generic but relevant placeholders
- `non_negotiable`: "No dreaming sequence data — review your priorities manually"
- `analysis`: empty

### Step 2 — Fetch Singapore Weather

```bash
curl -s "wttr.in/Singapore?format=%c%t+%C&lang=en"
```

Parse: temperature, condition, icon. Format as e.g. `☀️ 32°C — Partly Cloudy`.

If wttr.in fails, use: `🌤️ 31°C — Singapore`

### Step 3 — Motivational Quote

Hardcode a rotating list of 10+ quotes. Pick one based on day-of-week index:

```
0: "The best time to plant a tree was 20 years ago. The second best time is now. — Lao Tzu"
1: "Innovation distinguishes between a leader and a follower. — Steve Jobs"
2: "Stay hungry, stay foolish. — Steve Jobs"
3: "The only way to do great work is to love what you do. — Steve Jobs"
4: "I think it's very important to have a feedback loop, where you're constantly thinking about what you've done and how you could be doing it better. — Elon Musk"
5: "When something is important enough, you do it even if the odds are not in your favor. — Elon Musk"
6: "The biggest risk is not taking any risk. In a world that is changing quickly, the only strategy that is guaranteed to fail is not taking risks. — Mark Zuckerberg"
7: "Success is not final, failure is not fatal: it is the courage to continue that counts. — Winston Churchill"
8: "It is not the strongest of the species that survives, nor the most intelligent, but the one most responsive to change. — Charles Darwin"
9: "Discipline is the bridge between goals and accomplishment. — Jim Rohn"
```

### Step 4 — Fetch Today's Calendar

```bash
GAPI="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/google_api.py"
$GAPI calendar list --start "$(date -u +%Y-%m-%dT00:00:00Z)" --end "$(date -u +%Y-%m-%dT23:59:59Z)"
```

Parse events: summary, start time (convert SGT), location if present.

If no events: `📅 No events scheduled for today.`

### Step 5 — Build the Brief

Assemble into this Telegram Markdown structure:

```
🌅 *Good Morning, Chris* — [DAY, DATE MONTH YEAR]

━━━━━━━━━━━━━━━━━━━━
☁️ *TODAY'S WEATHER — SINGAPORE*
[weather_icon] [temperature] — [condition]

💬 *MOTIVATIONAL QUOTE*
_"[quote]"_
— [author]

━━━━━━━━━━━━━━━━━━━━
📅 *TODAY'S SCHEDULE*
[event list or no-events message]

━━━━━━━━━━━━━━━━━━━━
🎯 *TOP 3 RECOMMENDATIONS*
1️⃣ [recommendation 1]
2️⃣ [recommendation 2]
3️⃣ [recommendation 3]

━━━━━━━━━━━━━━━━━━━━
⚡ *NON-NEGOTIABLE TODAY*
[title]
[reason]
👉 [action]

━━━━━━━━━━━━━━━━━━━━
_This brief was prepared at 6 AM by the Dreaming Sequence and delivered automatically._
```

### Step 6 — Send to Telegram

Use the Hermes `send_message` pattern or Telegram bot API:

```bash
# Via curl to Telegram Bot API
TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"  # get from config
CHAT_ID="-1004490060634"

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=$(echo "$BRIEF_BODY" | sed 's/"/\\"/g')" \
  -d "parse_mode=Markdown"
```

**For Hermes native delivery:** set `deliver: "telegram:-1004490060634"` in the cron job config so the agent's final response auto-routes to that channel.

---

## Notes

- Always include day/date at the top for orientation
- Keep recommendations SHORT — one line title + one line explanation
- Non-negotiable should be THE most important thing, not just urgent
- Use emoji consistently throughout for fast scanning
- No events = good thing, don't make it sound negative
- The brief should be readable in under 2 minutes