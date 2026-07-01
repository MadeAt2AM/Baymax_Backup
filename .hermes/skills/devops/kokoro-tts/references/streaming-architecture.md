# Streaming TTS Architecture — Research Findings

**Date:** 2026-07-01

## Key Discovery: edge-tts Already Streams

edge-tts (currently the Hermes default) already does true chunked streaming:

```python
from edge_tts import Communicate

comm = Communicate(text, voice='en-US-AriaNeural')
async for chunk in comm.stream():
    if chunk['type'] == 'audio':
        # chunk['data'] = raw MP3 bytes (~720 bytes per frame)
        audio_queue.put(chunk['data'])
    elif chunk['type'] == 'SentenceBoundary':
        # Marker with timing: offset, duration, text
        print(f"Completed: {chunk['text']}")
```

**Measured on VPS:**
- First audio chunk: ~0.59s after request
- Generation speed: 8x real-time (7s audio in 0.87s)
- Chunk size: 720 bytes MP3 frames + final frame (~57 KB total for 7s)
- `SentenceBoundary` markers enable sentence-level sync

## Streaming Architecture Modes

### Mode A — Chunked Buffer (Current Telegram compatible)
Collect chunks → buffer 50%+ audio → send as voice message
- Telegram plays when received, not before
- Perceived latency = buffer_time + 0.59s

### Mode B — HTTP Streaming Proxy (True streaming)
Stream chunks to temp file → serve via HTTP → send URL to Telegram
- Audio starts before synthesis complete
- Requires public HTTP endpoint

### Mode C — Hybrid (Best balance)
LLM generates text streaming → each sentence triggers TTS → queue sentences
- Perceived latency = sentence_time + 0.59s
- Natural pacing via SentenceBoundary markers

## Kokoro Streaming

```python
async for chunk, sr in kokoro.create_stream(text, voice='bf_alice', speed=0.95):
    # chunk = np.ndarray at 24kHz
    # Yield rate: one chunk per phoneme batch
    yield chunk
```

## Key Libraries for Streaming TTS

| Library | Type | Streaming | Notes |
|---------|------|-----------|-------|
| edge-tts | Cloud | ✅ stream() async generator | Free, WebSocket, first-byte 0.59s |
| RealtimeTTS | Multi-engine | ✅ TextToAudioStream | Abstracts multiple backends |
| Kokoro-ONNX | Local | ✅ create_stream() async | CPU-native, 82M params |
| Piper | Local ONNX | ✅ SpeechStreamer | Lowest latency, robotic |
| Deepgram | Cloud API | ✅ WebSocket | Lowest latency neural |

## first-byte Latency Comparison

- Piper: ~0.05-0.1s (fastest, RNN-based)
- Deepgram WebSocket: ~0.2-0.4s
- Kokoro ONNX: ~0.3-0.5s
- edge-tts: ~0.59s (measured on VPS)
- Standard HTTP TTS: ~1-3s

## Implementation Pattern for Telegram Streaming

```python
# Pseudo: stream TTS chunks to a buffer, send to Telegram progressively
async def stream_to_telegram(chat_id, text):
    comm = edge_tts.Communicate(text, 'en-US-AriaNeural')
    chunks = []
    async for chunk in comm.stream():
        if chunk['type'] == 'audio':
            chunks.append(chunk['data'])
            if len(chunks) >= 20:  # Buffer 20 chunks before sending
                audio_bytes = b''.join(chunks)
                await bot.send_voice(chat_id, audio=audio_bytes)
                chunks = []
```

Note: Telegram voice messages require complete audio files — can't append to existing message. Best approach: buffer then send as complete voice file once enough is synthesized.
