# Telegram Bot Token Troubleshooting

## The Problem

Gateway shows "connected" (polling works) but all outbound sends fail with **HTTP 401 Unauthorized**. The gateway state shows `connected` because polling is a read operation — it doesn't validate the token. Outbound sends (sendMessage, etc.) do validate and return 401.

**Error from logs:**
```
Telegram error: HTTP Error 404: Not Found
❌ Failed to send to Telegram. Check bot token.
```
(404 can also appear for 401 depending on how the script calls the API — the underlying cause is the same: unauthorized.)

## Diagnostic Command

```bash
# Extract real token from .env — MUST use Python; bash glob expansion corrupts masked tokens
python3 -c "
import re
from pathlib import Path
content = Path('/root/.hermes/.env').read_text()
m = re.search(r'^TELEGRAM_BOT_TOKEN=(.*)$', content, re.MULTILINE)
print(m.group(1).strip()) if m else print('NOT FOUND')
"

# Python probe — avoids all shell expansion issues:
python3 -c "
import urllib.request, json, re
from pathlib import Path
content = Path('/root/.hermes/.env').read_text()
m = re.search(r'^TELEGRAM_BOT_TOKEN=(.*)$', content, re.MULTILINE)
token = m.group(1).strip() if m else None
if not token: exit('Token not found')
with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getMe', timeout=10) as r:
    print(r.read().decode())
"
# {"ok":false,"error_code":401,"description":"Unauthorized"} → token invalid
# {"ok":true,...} → token valid, problem is elsewhere
```

## Root Cause

Token was regenerated/revoked via `@BotFather` (`/revoke` command) or the bot was deleted and recreated. The old token is still in `~/.hermes/.env`.

## Fix

1. Get a fresh token from **@BotFather**:
   - Send `/revoke` to revoke the old token and get a new one, OR
   - Send `/newbot` to create a fresh bot
   - Copy the token (format: `123456789:ABCDefGhIJKlmNoPQRsTUVwxYZ`)

2. Update `.env`:
   ```
   TELEGRAM_BOT_TOKEN=<new_token>
   ```
   Use `hermes config env-path` to find the exact path.

3. Restart the gateway:
   ```bash
   hermes gateway restart
   ```

4. Verify:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/getMe"
   # Should return {"ok":true,...}
   ```

## Why Polling Still Works

Long polling (the gateway's `getUpdates`) uses a streaming HTTP request that returns only when new messages arrive. Telegram's API does not validate the bot token on long-polling endpoints the same way it validates outbound API calls. This is why `gateway_state.json` shows `"state":"connected"` even with an invalid token — the polling connection succeeds, but any attempt to `sendMessage` fails with 401.

**Key diagnostic insight:** A "connected" gateway state does NOT mean outbound sends will work. Always test outbound separately with the Python probe above.

## Related Values (CYBERSLIDE)

| Key | Value |
|-----|-------|
| `TELEGRAM_BOT_TOKEN` | In `~/.hermes/.env` — get fresh from @BotFather |
| `TELEGRAM_HOME_CHANNEL` | `-1003825565541` (MadeAt2Am group) |
| `TELEGRAM_ALLOWED_USERS` | `1283992553` (Chris Kal DM) |
| Bot name | `hermes-telegram` (from @BotFather setup) |

## Other Failure Modes

| Code | Cause | Fix |
|------|-------|-----|
| 401 | Token invalid/revoked | Get new token from @BotFather |
| 404 | Wrong token format, or bot not in channel | Verify bot added to channel, check token |
| 403 | Bot not admin in channel / no post permission | Make bot admin in channel |
| 400 + "chat not found" | Wrong `TELEGRAM_CHAT_ID` | Use the supergroup ID with `-100` prefix |
