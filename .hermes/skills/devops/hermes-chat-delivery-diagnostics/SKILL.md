---
name: hermes-chat-delivery-diagnostics
description: Diagnose stray, duplicate, or unexpected messages appearing in Hermes gateway chats (Telegram, Discord, Slack, etc.). Trace the source of any chat message back to its delivery path — text reply vs tool progress vs media vs terminal echo vs footer — using the four-path mental model and gateway source landmarks. Use when a user reports "why am I getting an extra message", "I see a duplicate", "where did this message come from", "something is leaking into the chat", or when the agent's own reply contains unintended content.
version: 1.0.0
---

# Hermes Chat Delivery Diagnostics

When a user reports a stray message in their chat, the cause is almost always one of four delivery paths firing when it shouldn't, or firing correctly but with unintended content. This skill gives you a mental model and a concrete trace procedure to find which one.

## The four delivery paths

Every message that lands in a chat comes from exactly one of these:

| # | Path | Source landmark | Typical symptom |
|---|------|-----------------|-----------------|
| 1 | **Agent text reply** | `gateway/run.py` `_process_message_background` / `_send_final_response` | The model's prose response after a tool call. Looks like normal English. |
| 2 | **Tool progress chatter** | `gateway/run.py` `progress_callback` (around line 15630) → `progress_queue` → `_send_progress_text` (line 15954) | Verb from `agent/display.py` `_TOOL_VERBS` dict + emoji + preview, e.g. `🎙️ Generating speech`, `🔍 Searching the web`, `💻 terminal`. |
| 3 | **Media delivery** | `gateway/run.py` `_deliver_media_from_response` (line 11995) + `adapter.send_voice` / `send_video` / `send_document` / `send_multiple_images` | Files from `MEDIA:<path>` tags or auto-detected bare paths. Voice bubbles, photos, docs. |
| 4 | **Terminal / script stdout** | Any tool that prints to stdout — terminal wrapper posts it as a chat message via Telegram adapter. | Lookalike raw output, e.g. `sent:9s`, `File uploaded: ...`, exit codes, JSON blobs. |

Path 1 is the only one the user "asked for" in the strict sense. Paths 2-4 are background plumbing — they fire when the system has something to say that isn't the user's prompt and isn't the model's reply.

## Symptom → likely path

| User complaint | Most likely path |
|---|---|
| "I see an emoji + verb + preview line" | Path 2 — tool progress chatter |
| "I see `🎙️ "..."` echoing my voice message back" | Path 2-variant — STT transcript echo, see `baymax-voice` skill |
| "I see terminal output in the chat" | Path 4 — terminal wrapper echo. Switch to a native tool, never use terminal() to call APIs directly |
| "I see a voice bubble PLUS a text reply" | Path 1 + Path 3 — expected when `text_to_speech` is called and the model also produces prose |
| "I see the same message twice" | Path 1 fired twice (streaming sent + final sent). Look for `already_sent=True` gating in `_process_message_background` |
| "Footer text appearing under my reply" | Runtime metadata footer, `gateway/runtime_footer.py` |
| "I see a message but I'm not sure what triggered it" | All four paths — read the chat timestamps and check gateway logs |

## Trace procedure

### 1. Identify the timestamp

Note the time the user saw the message. Cross-reference `~/.hermes/logs/gateway.log` for events in that window:
```bash
grep -E "send_voice|send_video|_deliver_media|_send_progress_text|tool_progress" ~/.hermes/logs/gateway.log | tail -30
```

### 2. Classify the content

Run the user's verbatim text through this heuristic:
- **Starts with emoji + verb phrase** ("🔍 Searching", "💻 terminal", "🎙️ Generating") → Path 2
- **Starts with `🎙️` and contains quoted text** → STT echo (Path 2-variant, see `baymax-voice`)
- **Starts with `MEDIA:`, contains a path, or is a file/voice/photo** → Path 3
- **Looks like English prose** → Path 1
- **Looks like raw shell output** (starts with `$`, contains `Traceback`, looks like JSON, contains exit codes) → Path 4
- **Mixed** (e.g. emoji + preview + prose) → Path 2 (verb) + Path 1 (prose), fired together

### 3. Trace to source

For each path:

**Path 2 — Tool progress:**
- Verb lookup: `grep "_TOOL_VERBS\[" /usr/local/lib/hermes-agent/agent/display.py` — find which tools have entries
- Caller: `gateway/run.py` around line 15807 — `get_tool_verb(tool_name)` is called when building the progress message
- Gate: `tool_progress_enabled = progress_mode != "off"` (line 15527). Per-platform overrides in `_PLATFORM_DEFAULTS` (gateway/display_config.py line 106+). Telegram defaults to `"off"` but a global `tool_progress: all` overrides it.
- **Fix when fired inappropriately:** Either (a) set `display.tool_progress: off` (or per-platform override for the affected platform), (b) remove the tool from `_TOOL_VERBS` if the tool's own output is the user-visible signal (e.g. `text_to_speech` removed 2026-07-01 because the voice bubble IS the signal), or (c) wrap the entry in a per-platform check.

**Path 3 — Media delivery:**
- Tag source: `MEDIA:` tags from tool results, `[[audio_as_voice]]` directive, or auto-detected bare paths in `final_response`
- See `baymax-voice` skill for the audio-specific debug (voice_compatible, output_format, thread routing)

**Path 4 — Terminal echo:**
- Hermes's terminal wrapper captures stdout/stderr and posts as chat messages when invoked in gateway mode
- **Fix:** Never call `requests`-style scripts via `terminal()`. Use a native tool (MCP, plugin, or built-in) that routes through `adapter.send_*` with proper threading.

### 4. Verify the fix

After patching:
1. Restart the gateway: `systemctl restart hermes-gateway.service`
2. Trigger the same interaction that produced the stray message
3. Confirm only the intended message(s) land — no extra chatter, no echo, no terminal output

## Common architectural invariants

These rarely change but bite when forgotten:

- **Config is read once at startup.** Toggling `display.tool_progress` in `~/.hermes/config.yaml` has NO effect until gateway restart.
- **Voice mode is read once at startup** from `~/.hermes/gateway_voice_mode.json`. Same restart requirement.
- **Telegram adapter posts tool progress silently** when `_notifications_mode == "important"` (the default) — `disable_notification: true` is set, but the message is still DELIVERED, just without a push notification. Silent ≠ suppressed.
- **Per-platform config defaults exist in `gateway/display_config.py` `_PLATFORM_DEFAULTS`** and most platforms opt out of tool_progress by default. A user's global override at `display.tool_progress: <mode>` wins over these defaults.
- **`_TOOL_VERBS` is a one-line-per-tool dict in `agent/display.py`.** Adding/removing entries there is a global change affecting every platform's progress output. For per-platform changes, branch in `progress_callback` instead.

## Key files

| File | Purpose |
|------|---------|
| `/usr/local/lib/hermes-agent/agent/display.py` | `_TOOL_VERBS` dict, `build_tool_label`, `get_tool_emoji` |
| `/usr/local/lib/hermes-agent/gateway/run.py` | `progress_callback` (~15630), `_send_progress_text` (~15954), `_deliver_media_from_response` (~11995) |
| `/usr/local/lib/hermes-agent/gateway/display_config.py` | `_PLATFORM_DEFAULTS`, `resolve_display_setting` |
| `/usr/local/lib/hermes-agent/plugins/platforms/telegram/adapter.py` | `_send_progress_text` consumer, `_notifications_mode` |
| `~/.hermes/config.yaml` | `display.tool_progress`, `display.platforms.telegram.*` overrides |
| `~/.hermes/logs/gateway.log` | Trace delivery events for a session |

## Related skills

- `baymax-voice` — voice-specific debug (thread routing, voice_compatible flag, transcript echo)
- `kokoro-tts` — TTS provider setup, OGG/Opus format requirements
- `hermes-agent` — bundled skill: gateway config, slash commands, general architecture