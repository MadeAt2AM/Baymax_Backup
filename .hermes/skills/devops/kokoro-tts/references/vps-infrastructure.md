# VPS Infrastructure Specs — July 2026

**Host:** Singapore · AS200257 UserDepth LLC · AMD Ryzen 5 5600 6-Core (QEMU/KVM)
**OS:** Ubuntu 24.04 LTS · Kernel 6.8.0-117-generic

## Resources

| Resource | Value | Notes |
|----------|-------|-------|
| CPU | 4 vCPU AMD Ryzen 5 5600 @ 2GHz | QEMU/KVM passthrough |
| RAM Total | 7.8 GB | ~5.5 GB in use, ~2.0 GB available |
| Disk | 96 GB `/` · 71 GB free | 27% used |
| GPU | None | No NVIDIA, no GPU passthrough |
| Audio HW | /dev/snd/ (timer + sequencer) | No playback device |
| Audio SW | PipeWire + PulseAudio libraries | No local playback |
| Docker | v29.5.2 | Container runtime available |
| Python | 3.12.3 system + Hermes 3.11 venv | |

## TTS Model Benchmark (CPU-capable)

| Model | RAM | Speed | Voice Quality | License |
|-------|-----|-------|---------------|---------|
| Kokoro-82M (fp16) | ~2 GB | 0.1-0.2x RTF | #6-7 TTS Arena | Apache 2.0 ✅ |
| MeloTTS | 2 GB | 0.1-0.3x RTF | #15 TTS Arena | MIT ✅ |
| Piper | 1-2 GB | 0.05-0.1x RTF | Basic | BSD-2 ✅ |
| ChatTTS | 4 GB | 0.3-0.5x RTF | Good CN/EN | Apache 2.0 ✅ |
| Orpheus-150M | 2 GB | ~0.3x RTF | Emotional tags | Apache 2.0 ✅ |
| Chatterbox-Turbo | 3-5 GB | <0.3x RTF | Emotion slider | MIT ✅ |
| XTTS-v2 | 6 GB | 0.5-1x RTF | Best cloning | Non-commercial |

**Selected for this VPS: Kokoro-82M** — best quality-per-size ratio, Apache 2.0 license, runs comfortably in available RAM.

## edge-tts Streaming (Current Default)

- First-byte latency: **0.59s** (measured)
- Generation speed: **8x real-time**
- Chunk count: ~60-80 chunks per sentence
- Chunk size: 720 bytes MP3 frames
- Supports prosody: pitch (+/-Hz), rate (+/-%), volume (+/-%)
- 322 voices available (30+ English variants)

## Kokoro Memory Footprint

```
Model: 169 MB (fp16 ONNX)
Voices: 28 MB (voices-v1.0.bin)
Runtime (ONNX Runtime): ~300-500 MB
espeak-ng + phonemizer: ~50 MB
Total Kokoro footprint: ~600 MB RAM
```

## Hermes TTS Config

Provider order in `config.yaml`:
1. edge (current default, Microsoft Azure) — streaming capable
2. elevenlabs — API key required
3. openai — API key required
4. gemini — API key required
5. xai — API key required
6. mistral — API key required
7. neutts — configured but not installed (neuphonic/neutts-air-q4-gguf)
8. piper — configured but not installed

Current: `tts.provider: edge` with `edge.voice: en-US-AriaNeural`
