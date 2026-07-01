# Telegram Topic Threading — Architecture Notes

## How Hermes handles Telegram topic threading

When Chris messages from a Telegram DM topic (thread), Hermes must send replies into the same topic thread or they silently disappear into General.

### Session binding (how Hermes knows the thread)

`SessionSource` carries:
- `chat_id` — the DM chat ID
- `thread_id` — the topic thread ID (e.g. `56643`)
- `chat_type` — always `"dm"` for Chris's case

Session DB tables:
- `telegram_dm_topic_mode` — per-chat topic mode flag (`enabled=1` means topic mode active)
- `telegram_dm_topic_bindings` — maps `(chat_id, thread_id)` → `session_key`

Query current bindings:
```sql
SELECT * FROM telegram_dm_topic_bindings
WHERE chat_id = '1283992553'
ORDER BY updated_at DESC LIMIT 5;
```

### Threading metadata construction

`_thread_metadata_for_source(source, reply_anchor)` in `gateway/run.py` builds the `metadata` dict:
```python
{
    "message_thread_id": <thread_id>,
    "telegram_dm_topic_reply_fallback": True,  # enables fallback send for DM topics
    "direct_messages_topic_id": <thread_id>,    # fallback thread ID for synthetic sends
}
```

`_reply_anchor_for_event(event)` in `gateway/platforms/base.py`:
- For Telegram DM with `thread_id` and `chat_type == "dm"`: returns `event.message_id` (reply-to anchor)
- For Telegram forum topics: returns `None` (thread_id alone routes the message)
- Falls back to `event.message_id`

### Voice send paths (and their threading correctness)

| Path | File | Threading | Notes |
|---|---|---|---|
| `_send_voice_reply` | `gateway/run.py:11933` | ✅ Correct | Fires when voice_mode is `"all"`, uses `_thread_metadata_for_source` |
| `_deliver_media_from_response` | `gateway/run.py:12009` | ✅ Correct | Handles `[[audio_as_voice]]` MEDIA tags from TTS tool |
| `send_voice.py` (standalone) | `/root/.kokoro/` | ❌ Fallback only | No thread params unless explicitly passed; Chris requests no use |
| `TelegramAdapter.send_voice` | `plugins/platforms/telegram/adapter.py:5158` | ✅ Correct | Receives metadata dict, extracts `message_thread_id` |

### Voice mode

Voice mode is stored in-memory in the gateway (`_voice_mode` dict, keyed by `_voice_key(platform, chat_id)`) and persisted to **`~/.hermes/gateway_voice_mode.json`** — NOT `voice_modes.json`.

Format in `gateway_voice_mode.json`:
```json
{
  "telegram:1283992553": "all"
}
```

Key format: `telegram:<chat_id>` — **no `:dm:` suffix**. `telegram:dm:1283992553` will NOT match.

Valid modes: `"off"`, `"voice_only"`, `"all"`.

The gateway loads this on startup and also saves any runtime changes (e.g. when joining a voice channel sets it to `"all"`).

### Key code locations

- Thread metadata: `gateway/run.py:_thread_metadata_for_source`
- Reply anchor: `gateway/platforms/base.py:_reply_anchor_for_event`
- Voice mode load/save: `gateway/run.py:_load_voice_modes` / `_save_voice_modes`
- Voice reply decision: `gateway/run.py:_should_send_voice_reply`
- Native voice send: `gateway/run.py:_send_voice_reply`
- Media delivery: `gateway/run.py:_deliver_media_from_response`
- Telegram send_voice: `plugins/platforms/telegram/adapter.py:send_voice`
- Telegram thread_id extraction: `plugins/platforms/telegram/adapter.py:_metadata_thread_id`
- Session DB schema: `telegram_dm_topic_mode`, `telegram_dm_topic_bindings` tables in `state.db`

### Voice mode is loaded once at startup

The gateway calls `_load_voice_modes()` at startup only — it does **not** re-read `gateway_voice_mode.json` at runtime. Any changes to the file require `hermes gateway restart` to take effect. The in-memory `_voice_mode` dict is the live authority, not the JSON file.

## Concurrent sessions per topic

Chris can have **multiple simultaneous Hermes sessions** for the same DM — one per topic. The gateway routes each incoming message to the session matching `session_key = agent:main:telegram:dm:1283992553:<thread_id>`. If a message arrives in topic 56768 but the gateway routes it to the session for 56643, voice replies go to the wrong topic.

**Correct session isolation:**
```sql
SELECT id, session_key, thread_id, title,
       datetime(started_at, 'unixepoch') as started
FROM sessions
WHERE chat_id = '1283992553'
ORDER BY started_at DESC LIMIT 5;
```

## TTS tool → MEDIA tag pipeline

`text_to_speech_tool` in `tools/tts_tool.py`:
1. Generates audio (`.ogg` for Telegram when `voice_compatible: true` is set on the provider)
2. Returns JSON with `media_tag = f"[[audio_as_voice]]\nMEDIA:{file_str}"` when voice-compatible
3. Gateway's `_collect_auto_append_media_tags` scans tool results for `MEDIA:` tags
4. If `[[audio_as_voice]]` is present, `_deliver_media_from_response` calls `adapter.send_voice()`
5. `send_voice` uses the correct `message_thread_id` from `event.source.thread_id`

### CRITICAL: `voice_compatible: true` on command providers

For command-type TTS providers (like Kokoro), the `voice_compatible` flag is **opt-in**. Without it, Hermes assumes the output is a generic audio file and attaches it as a file, not a voice bubble.

The kokoro command provider in `config.yaml` needs:
```yaml
tts:
  provider: kokoro
  providers:
    kokoro:
      type: command
      command: /opt/kokoro-venv/bin/python /root/.kokoro/kokoro_tts.py --input {text_path} --output {output_path} --voice bm_fable --speed 0.95
      output_format: ogg
      voice_compatible: true   # ← THIS FLAG IS REQUIRED for voice bubble routing
```

Set with:
```bash
hermes config set tts.providers.kokoro.voice_compatible true
```

## Known issues and fixes

### Transcription echo

When a user sends a voice message, Hermes auto-transcribes it (STT) and immediately echoes the transcript back to the user as `🎙️ "transcript text"`. This is hardcoded in `gateway/run.py:9518–9532`. The transcription is still passed to the agent internally — only the echo back to the user is suppressed by patching that block.

**Current status:** No config flag to disable this. Requires a code change in `gateway/run.py` to comment out the `if _successful_transcripts:` echo block.

### Kokoro stderr output leaking to chat

`kokoro_tts.py` had a `print(f"Generated: {args.output}", file=sys.stderr)` debug line. This stderr output can leak into the agent session and appear in the chat. **Fixed** by removing the print statement from `kokoro_tts.py`. If terminal noise appears again, check `kokoro_tts.py` for any remaining print statements.
