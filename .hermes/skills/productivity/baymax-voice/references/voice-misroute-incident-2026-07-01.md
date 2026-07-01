# Voice Misroute Incident — 2026-07-01

## Symptom

Chris messaged from Telegram topic `57217` (chat_id `1283992553`). Agent replied with a voice bubble **and a text reply**. The voice bubble landed in the bot home (no topic). The text reply landed correctly in topic `57217`.

User feedback: *"you are sending it to telegram bot home page, nt to the topic, text is coming to the topic chat, voice is going there"*

## Root cause

Agent called `/root/.kokoro/send_voice.py` via the `terminal()` tool with no positional arguments after the text:

```bash
/opt/kokoro-venv/bin/python /root/.kokoro/send_voice.py \
  "Hi Chris! I'm doing well, thanks for asking..."
```

The script:

1. Generated OGG audio via Kokoro (this worked).
2. Posted directly to `api.telegram.org/bot<TOKEN>/sendVoice` using its built-in `DEFAULT_CHAT_ID = "1283992553"` — which is Chris's DM **without any thread_id**, so the voice bubble went to the bot home.
3. Printed `sent:9s` to stdout. Hermes's terminal wrapper captured this and posted it as a separate text message — also to the bot home, since the terminal output doesn't inherit the session's thread binding.

## Why the native path would have worked

The `text_to_speech` tool returns a `MEDIA:/path/to/file.ogg` tag prefixed with `[[audio_as_voice]]`. The gateway's `_collect_auto_append_media_tags` picks this up and calls `_deliver_media_from_response`, which:

1. Reads `event.source.thread_id` from the active session.
2. Builds the metadata dict via `_thread_metadata_for_source(event.source, reply_anchor)`.
3. Calls `TelegramAdapter.send_voice(file, chat_id, reply_to, metadata)` with `message_thread_id` set.
4. Renders as a native Telegram voice bubble (because `voice_compatible: true` is set on the Kokoro provider).

None of that happened on the standalone-script path. The terminal wrapper treated the script as an opaque command, not as a platform-aware delivery.

## Reproduction

To reproduce the bug:

1. Open topic `57217` in Chris's Telegram DM.
2. Run `/opt/kokoro-venv/bin/python /root/.kokoro/send_voice.py "test"` from a Hermes session bound to that topic.
3. Observe: voice lands in bot home, "sent:Ns" text also lands in bot home, no voice in topic.

To verify the fix:

1. Same topic, same session.
2. Call the `text_to_speech` tool with the same text.
3. Observe: voice bubble in topic `57217`, no stray text in bot home.

## Related config (verified correct on 2026-07-01)

- `~/.hermes/config.yaml`:
  - `tts.providers.kokoro.output_format: ogg`
  - `tts.providers.kokoro.voice_compatible: true`
  - `voice.auto_tts: true`
- `~/.hermes/gateway_voice_mode.json`: `{"telegram:1283992553": "all"}`
- Session DB binding: chat `1283992553`, thread `57217` → session `agent:main:telegram:dm:1283992553:57217`, updated 2026-07-01 05:58:37.

Everything was set up correctly. The bug was purely in agent decision-making (chose the wrong path). Fix lives in `baymax-voice/SKILL.md` (ABSOLUTE RULE section) and in memory.