---
name: baymax-voice
description: Send Telegram voice replies via Kokoro TTS — gateway-native path with topic threading
triggers:
  - "voice reply"
  - "test voice"
  - "say something"
  - "hear you"
  - "voice message not received"
  - "voice not in topic"
  - "voice going to bot home"
  - "voice in wrong place"
  - "voice in wrong chat"
---

# Baymax Voice — Telegram Voice Reply via Kokoro

## 📎 References & scripts

- `references/telegram-topic-threading.md` — architecture: how thread_id flows from session → adapter → sendVoice.
- `references/voice-misroute-incident-2026-07-01.md` — case study of the bot-home misroute bug (the one this skill exists to prevent).
- `scripts/voice-routing-probe.py` — run before sending voice replies to verify all routing config is correct. Exit code 0 = safe, 1 = misconfigured, 2 = probe itself failed.

## 🚨 ABSOLUTE RULE: NEVER use send_voice.py directly for Chris

**Chris: 2026-07-01 incident.** Voice was sent to the bot home (no topic) instead of the topic thread (57217). Root cause: I called `/root/.kokoro/send_voice.py` directly. It bypasses the gateway's native voice pipeline and has no awareness of `message_thread_id`. Hermes's terminal wrapper then posted the script's "sent:9s" output as a separate text message to the bot home.

**Hard rule for ALL voice replies to Chris:**
- ✅ **USE the `text_to_speech` tool** — goes through the native gateway path, which calls `_deliver_media_from_response` with `[[audio_as_voice]]` tag, which routes via the Telegram adapter with the correct `message_thread_id` from the session source.
- ❌ **NEVER call `/root/.kokoro/send_voice.py` via `terminal()`** — bypasses threading, posts terminal echo to the wrong place, and was explicitly forbidden by Chris.
- ⚠️ `send_voice.py` is NOT a real fallback — if the gateway is down, Telegram replies don't work at all (no inbound messages, no topic context, no conversation continuation). The script is dead weight unless paired with a full gateway revival. If gateway is down, fix the gateway first.

If you are about to type `/opt/kokoro-venv/bin/python /root/.kokoro/send_voice.py` — STOP. Use `text_to_speech` instead. No exceptions.

## ⚠️ Pitfall: gateway_voice_mode.json — NOT voice_modes.json

The gateway reads **`gateway_voice_mode.json`** in `~/.hermes/`, **NOT `voice_modes.json`**. This is the #1 cause of voice not working.

The gateway loads this file **only once** at startup. Changes while the gateway is running have zero effect until restart.

**Always restart after any modification:**
```bash
hermes gateway restart   # run from a shell OUTSIDE the gateway process
```

Symptoms of stale voice mode: auto-TTS never fires, no voice bubble appears, nothing in logs.

## Critical constraint: Topic threading

## Primary procedure: Native gateway path (preferred)

The gateway's own `_send_voice_reply` and `_deliver_media_from_response` both route to the correct topic automatically, provided voice mode is enabled. **Use this path — it avoids terminal echo, handles threading automatically, and renders as a native voice bubble.**

### Voice mode persistence

Voice mode is stored in-memory in the gateway (`_voice_mode` dict, keyed by `_voice_key(platform, chat_id)`) and persisted to **`~/.hermes/gateway_voice_mode.json`** — NOT `voice_modes.json`.

The gateway loads this file **once at startup only**. Any runtime changes via `/voice` slash command are saved back to the file, but manual edits require restart.

Correct format in `gateway_voice_mode.json`:
```json
{
  "telegram:1283992553": "all"
}
```

Key format: `telegram:<chat_id>` — **no `:dm:` suffix**. `telegram:dm:1283992553` will NOT match.

Valid modes: `"off"` | `"voice_only"` | `"all"` (reply to every message with TTS).

### Step 1 — Enable voice mode globally

```bash
hermes config set voice.auto_tts true
```

### Step 2 — Create/verify gateway_voice_mode.json

```bash
echo '{"telegram:1283992553": "all"}' > ~/.hermes/gateway_voice_mode.json
```

### Step 3 — Restart the gateway

**From a shell OUTSIDE the running gateway process** (restarting from inside the gateway process kills it before the command completes):
```bash
hermes gateway restart
```

### Step 4 — Trigger voice reply

Once voice mode is `"all"` and `auto_tts` is `true`, the gateway replies with TTS audio automatically on every turn. Threading is handled by `_thread_metadata_for_source(event.source, reply_anchor)` — no extra parameters needed.

To manually trigger a one-shot voice reply, use the `text_to_speech` tool (see below).

## Kokoro TTS config requirements (CRITICAL for native bubble rendering)

For the native pipeline to render Kokoro output as a **native Telegram voice bubble** (not a downloadable audio file attachment), two config flags are required on the Kokoro command provider in `config.yaml`:

```bash
hermes config set tts.providers.kokoro.voice_compatible true
hermes config set tts.providers.kokoro.output_format ogg
```

- **`voice_compatible: true`** — This tells the gateway to add the `[[audio_as_voice]]` tag when forwarding TTS output. Without this flag, the `.ogg` is generated correctly but delivered as a file attachment, not a voice bubble. This is the **most common cause of downloadable-file behavior**.
- **`output_format: ogg`** — Telegram requires Opus/OGG for native voice bubbles. The standalone script handles this with ffmpeg; the native pipeline needs this flag set.

After any config change: `hermes gateway restart`

## Standalone send_voice.py (DO NOT USE for Chris)

**This script is BANNED for normal replies to Chris.** It bypasses the native voice pipeline and has no awareness of `message_thread_id`. See the ABSOLUTE RULE at the top of this file.

### Why it exists (background only)

`send_voice.py` was written before the native `text_to_speech` tool existed. It generates Kokoro audio and POSTs directly to `api.telegram.org/bot<TOKEN>/sendVoice` with whatever `chat_id` and `thread_id` you pass. It is **not** registered with the gateway — it does not consult `gateway_voice_mode.json`, does not go through `TelegramAdapter.send_voice`, and does not pick up session metadata.

### Why it's dangerous even when given the right arguments

Even if you manually pass `chat_id` + `reply_to` + `thread_id`, two more failures happen:

1. **Terminal echo leak.** Hermes's Telegram integration posts ALL terminal tool output (stdout, stderr, exit codes) as separate Telegram messages. The script prints `sent:9s` on success, which appears in chat as a text message — usually in the **bot home** (no topic) because the terminal wrapper doesn't inherit session thread context. Result: voice lands in topic ✅, but a stray "sent:9s" text lands in bot home ❌. Chris sees this as a misroute bug.
2. **Wrong defaults win.** The script's `DEFAULT_CHAT_ID = "1283992553"` (Chris's DM) means missing arg = always goes to his DM, regardless of which topic was active. The first thing a rushed agent omits is the thread args.

### When (never) acceptable

**Never acceptable.** `send_voice.py` is not a real fallback — when the gateway is down, Telegram is offline (no inbound messages, no session context, no topic awareness). Calling this script in a gateway-down scenario posts an orphan voice bubble with no conversational continuity: you can't reply and have the agent see it, and any text/terminal output also goes nowhere useful. The only real fallback for voice delivery failure is to fix the gateway (`systemctl restart hermes-gateway.service`) and resume the native `text_to_speech` path.

If you find yourself reaching for this script, the correct alternative is the `text_to_speech` tool. No exceptions for "it's just a quick test" or "the gateway is having a wobble."

## ⚠️ Pitfall: "Generating speech…" echo before the voice bubble

A `text_to_speech` tool call normally produces **only** the voice bubble — but if `display.tool_progress: all` (or any non-"off" value) is set in config, the gateway also emits a separate chat message before the audio lands, formatted like "🎙️ Generating speech…". The user sees:

```
[voice bubble 00:07]      ← actual TTS output
🎙️ Generating speech…     ← tool progress chatter
```

**Root cause:** `agent.display._TOOL_VERBS["text_to_speech"] = "Generating speech"` + the `progress_callback` in `gateway/run.py` (around line 15807) which builds a chat message for every `tool.started` event.

**Why this happens on Telegram but not on CLI:** Telegram's platform default is `tool_progress: "off"`, but the user's `display.tool_progress: all` global setting overrides it. The CLI shows this string as a quiet spinner; Telegram renders it as a real message.

**Fix (committed 2026-07-01):** `text_to_speech` removed from `_TOOL_VERBS` in `agent/display.py`. The voice bubble itself is now the only user-visible signal that TTS is happening. If you need to re-add a progress line, prefer an adapter-level hook (Telegram-specific) over the global verb dict.

**Verify after gateway restart:** run a `text_to_speech` call and confirm only the voice bubble appears — no "Generating speech" prefix, no separate echo.

## Audio format for Telegram voice bubbles

Valid voice bubble format (verified with ffprobe):
- Container: Ogg
- Codec: Opus
- Sample rate: 48000 Hz
- Channels: mono
- Duration: must be > 0s (Telegram rejects 0-duration files)
- MIME type: audio/ogg

ffprobe command to verify:
```bash
ffprobe -v quiet -print_format json -show_format -show_streams /path/to/file.ogg
```

Expected output: `format_name: ogg`, `codec_name: opus`, `sample_rate: 48000`, `channels: 1`

**Do NOT use `send_voice.py` for this verification** — it is the misroute bug itself. Use the probe script in `scripts/voice-routing-probe.py` instead.

### Script locations
- `/root/.kokoro/kokoro_tts.py` — Hermes command provider script (native pipeline, the only path that matters)
- `/root/.kokoro/send_voice.py` — DEPRECATED standalone sender. Exists for historical reasons; **do not invoke** for Chris. See ABSOLUTE RULE at top.
- `/opt/kokoro-venv/` — Python venv with kokoro-onnx + espeak-ng
- BOT_TOKEN read from `/root/.hermes/.env` (`TELEGRAM_BOT_TOKEN`)

## Voice options
- bm_fable (British male, Chris's selected voice)
- Speed: 0.95 (slightly slower for warmth)
- Format: OGG Opus, 48kHz (native Telegram voice bubble format)
## Verification

```bash
# Check voice mode file (correct file!)
cat ~/.hermes/gateway_voice_mode.json
# Expected: {"telegram:1283992553": "all"}

# Check config flags are set (note: `hermes config get` does NOT exist —
# use `hermes config show` and grep, or open config.yaml directly)
grep -E "auto_tts|voice_compatible|output_format" ~/.hermes/config.yaml
# Expected: includes `voice_compatible: true`, `output_format: ogg`, `auto_tts: true`

# Verify topic binding is live for the current session
sqlite3 /root/.hermes/state.db \
  "SELECT thread_id, session_key FROM telegram_dm_topic_bindings \
   WHERE chat_id = '1283992553' ORDER BY updated_at DESC LIMIT 1"
# (If sqlite3 is unavailable, use python3 -c with sqlite3 module.)
```

If voice still doesn't appear in the topic after `text_to_speech`, check the gateway logs for `_deliver_media_from_response` errors — the audio file may have been generated but the delivery step failed silently.

## Troubleshooting: Voice appearing in wrong destination

Voice bubble lands in the bot home (no topic) while text from the agent lands in the topic thread — or vice versa. This is a **delivery path mismatch**, not a config issue.

Root causes in order of likelihood:
1. **Used `send_voice.py` directly via `terminal()`** — the script bypasses the gateway's platform adapter and posts to Telegram with whatever `chat_id` is in its defaults or args. Even with correct args, the script's stdout (`sent:9s`) is captured by the terminal wrapper and posted to the bot home. **Fix: switch to the `text_to_speech` tool.** This is the most common cause (2026-07-01 incident).
2. **Manually called Telegram Bot API from a script** — same problem as above; you lose the platform adapter's metadata handling.
3. **Cron job or background subagent sent the voice** — the cron/subagent session does not share the user's session binding. Voice will go wherever its `chat_id` arg points. **Fix: use `deliver="origin"` or the platform-aware path.**

## Troubleshooting: Voice not appearing in topic

Root causes in order of likelihood:
1. **`voice_compatible: true` missing from Kokoro config** — the `.ogg` is generated correctly but the gateway delivers it as a file attachment, not a native voice bubble. Add it to `~/.hermes/config.yaml` under `tts.providers.kokoro.voice_compatible: true`, then `hermes gateway restart`.
2. **`output_format: ogg` missing** — Telegram requires Opus/OGG for native bubbles. Set `tts.providers.kokoro.output_format: ogg` in `config.yaml`.
3. **Wrong voice mode file** — checking `voice_modes.json` instead of `gateway_voice_mode.json` (see pitfall above).
4. **`voice.auto_tts` is false globally** — `grep "auto_tts:" ~/.hermes/config.yaml` should show `auto_tts: true`. Edit the file or use `hermes config edit`.
5. **Gateway not restarted after config change** — any file or config change requires `hermes gateway restart`.
6. **Wrong key format in voice mode** — must be `telegram:1283992553`, NOT `telegram:dm:1283992553`.
7. **Wrong thread_id** — verify the current topic's thread ID from the session DB via `scripts/voice-routing-probe.py` or the verification commands above.

> Note: `hermes config get <key>` does NOT exist. Use `hermes config show`, `grep` on `~/.hermes/config.yaml`, or the probe script.

## Troubleshooting: Downloadable file instead of native voice bubble

Telegram renders the same valid OGG/Opus audio as either a native voice bubble (waveform, play button) or a downloadable file attachment. The determinant is **`voice_compatible: true`** on the Kokoro provider config:

- **With `voice_compatible: true`** → gateway adds `[[audio_as_voice]]` tag → native bubble
- **Without `voice_compatible: true`** → gateway sends as file attachment → downloadable

Fix:
```bash
hermes config set tts.providers.kokoro.voice_compatible true
hermes config set tts.providers.kokoro.output_format ogg
hermes gateway restart
```
(If `hermes config set` is unavailable on your install, edit `~/.hermes/config.yaml` directly — the relevant block is `tts.providers.kokoro`.)

Verify with `ffprobe` that the OGG is valid Opus at 48kHz mono — if the file is valid but renders as a file, the config flag is the cause.

## ⚠️ Pitfall: Transcription echo

When Chris sends a voice message, Hermes auto-transcribes it (STT) and immediately sends `🎙️ "transcript text"` back to the chat **before** the agent even processes the message. This is hardcoded in `gateway/run.py:13983–13997` — there is no config flag to disable it.

**The transcription is still passed to the agent internally.** Only the echo back to the user can be suppressed, and only via a code change.

**Fix:** Comment out the `if successful_transcripts:` block in `_dequeue_pending_audio` around line 13983 in `/usr/local/lib/hermes-agent/gateway/run.py`:

```python
# DISABLED: Chris Kal — transcript echo clutters the chat.
# if successful_transcripts:
#     echo_adapter = self.adapters.get(source.platform)
#     echo_meta = {"thread_id": source.thread_id} if source.thread_id else None
#     if echo_adapter:
#         for tx in successful_transcripts:
#             try:
#                 await echo_adapter.send(
#                     source.chat_id,
#                     f'🎙️ "{tx}"',
#                     metadata=echo_meta,
#                 )
#             except Exception as echo_exc:
#                 logger.debug(
#                     "Transcript echo failed (non-fatal): %s", echo_exc,
#                 )
```

**Restart required after patching:**
```bash
bash -c 'systemctl restart hermes-gateway.service'
```
`hermes gateway restart` is BLOCKED from inside the gateway process — it kills itself before the command completes. Use systemd directly or run from a shell outside the gateway session.
