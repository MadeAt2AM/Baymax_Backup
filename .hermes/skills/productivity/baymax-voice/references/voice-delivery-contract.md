# Voice Delivery Contract

Codifies the three delivery paths in `gateway/run.py:_handle_message` (around
line 11048) and the suppression rules that keep them from double-sending.
Pin-tested by `tests/gateway/test_voice_prose_suppression.py` (20 cases).

## TL;DR

One turn → one user-visible message. If voice fires, prose is suppressed.
If prose fires, voice was never generated. Streaming-already-delivered turns
return `None` from the runner (no second dispatch).

## The three delivery paths

| Path | Trigger | What gets sent | Runner returns |
|---|---|---|---|
| **Streaming** | `agent_result["already_sent"] is True` (stream consumer delivered the final answer via `_send_or_edit`) | Whatever `MEDIA:` / `[[audio_as_voice]]` tags exist in `response` (delivered by `_deliver_media_from_response`) plus a small trailing `_footer_line` (runtime metadata) | `None` — adapter does NOT re-send text |
| **Auto-voice-reply** | `_should_send_voice_reply(event, response, agent_messages, already_sent)` returns True → runner fires `_send_voice_reply` (synth TTS → `adapter.send_voice`) | Voice bubble via the platform adapter's native send_voice | After voice fires: `response = ""` so adapter sends nothing. Prose is suppressed. |
| **Agent-tool TTS** | Agent itself called `text_to_speech` tool. Detected via `_agent_called_voice_tool(agent_messages)`. Auto-mode may be off. | Voice bubble (delivered by the streaming path if `already_sent` is True, OR via `_deliver_media_from_response` for the MEDIA tag, OR sometimes leaks as raw text) | `_voice_sent = True` → `response = ""`. Prose around the tool call is suppressed. |

## Suppression rules (the contract)

The inline code at `gateway/run.py:11048` enforces:

```python
_voice_sent = False
if self._should_send_voice_reply(event, response, agent_messages, already_sent=_already_sent):
    await self._send_voice_reply(event, response)
    _voice_sent = True
elif self._agent_called_voice_tool(agent_messages):
    _voice_sent = True
if _voice_sent and response:
    logger.debug("Suppressing prose text after voice delivery: chat=%s len=%d", ...)
    response = ""
```

Three predicates:

- **`_should_send_voice_reply`** — auto-mode gate (`voice_mode == "all"` /
  `"voice_only"`), AND not already deduped (no `text_to_speech` tool call from
  agent this turn), AND not an empty / `Error:`-prefixed response.
- **`_agent_called_voice_tool`** — scans `agent_messages` for any assistant
  turn whose `tool_calls` contains a function named `text_to_speech`.
- **Final guard** — if either fired AND `response` is non-empty, blank it.

## Why this is non-obvious

Three things have to be true at once or a duplicate sneaks through:

1. The runner must actually fire voice (auto-mode OR agent tool call).
2. The runner must blank `response` before returning — otherwise the base
   adapter dispatches the prose as a separate text message.
3. The streaming path must keep its existing `return None` after media
   extraction — otherwise streaming also fires the adapter twice.

When all three hold, one turn → one message. When any one slips, the user
sees the "voice file after the exact msg" bug, which appears random because
it depends on which delivery path the turn took.

## What is NOT suppressed

- The streaming path's small trailing `_footer_line` (runtime metadata like
  model name, timing). This is by design — Chris's complaint was about prose
  leaking alongside the voice, not about metadata footers.
- Errors (`response` starting with `Error:`). The runner skips voice for
  these so the error text always reaches the user.
- Empty responses. Both `_should_send_voice_reply` and the blanking guard
  short-circuit on `not response`.

## How to verify after a change

Three checks, in order:

1. **Unit tests pass** — `tests/gateway/test_voice_prose_suppression.py` has
   20 cases pinning the suppression logic. Plus the broader suite
   `test_auto_voice_reply_format.py`, `test_tts_media_routing.py`,
   `test_send_voice_reply_notify.py`, `test_duplicate_reply_suppression.py`,
   `test_voice_mode_platform_isolation.py`. Run all before deploying.

2. **Gateway restart** — `systemctl restart hermes-gateway.service` from a
   shell OUTSIDE the gateway process. (`hermes gateway restart` is blocked
   from inside the gateway — it kills itself before the command completes.)

3. **Live smoke test** — send a text to the bot in Telegram:
   - Auto-mode `"all"`: ONE voice bubble, no prose after it.
   - No auto-mode + you ask for TTS by voice: ONE voice bubble, no prose.
   - Plain text question: prose text reply, no voice.

If voice AND text both arrive after restart, the patch did not load — check
`systemctl status hermes-gateway.service` and the gateway logs.

## Pitfalls when changing this area

- **Don't blanket-suppress.** The guard `if _voice_sent and response:` is
  intentionally narrow. Suppressing ALL responses when voice fires would
  also suppress the trailing footer on streaming-delivered turns, killing
  the runtime metadata surface users rely on.

- **Don't move the suppression past `_footer_line` emission.** The streaming
  path (line 11064+ in `gateway/run.py`) emits the footer INSIDE the
  `return None` block, AFTER the auto-voice-reply check has run. If you
  restructure the order, you can accidentally emit prose before the
  `response = ""` blanking takes effect.

- **`agent_messages` may include streamed fragments.** The detection helper
  walks the whole turn list. If the agent streamed prose between tool calls,
  the suppression still triggers correctly because `_agent_called_voice_tool`
  only checks tool-call names, not message content.

## Cross-references

- Skill `baymax-voice` → "Pitfall: prose text sent after voice bubble" — the
  symptom view, point-in-time fix record.
- `tests/gateway/test_voice_prose_suppression.py` — the regression tests.
- `tests/gateway/test_duplicate_reply_suppression.py` — adjacent
  suppression logic for streaming-delivery double-sends (different layer,
  same shape of fix).
- `tests/gateway/test_auto_voice_reply_format.py` — `.ogg` vs `.mp3`
  format selection for the auto-voice-reply path.