---
name: kokoro-tts
description: "Install, configure, and use Kokoro-ONNX for local TTS voice generation on the VPS. Covers the full pipeline: venv setup, model/voice download from correct sources, environment vars, np.load patch, voice evaluation, Hermes TTS integration, and streaming audio generation. Use whenever installing or configuring local TTS on the host."
version: 1.0.0
category: devops
---

# Kokoro-ONNX TTS — Local Voice Generation

## Overview

Kokoro-82M is a lightweight (82M params) TTS model that runs natively on CPU via ONNX Runtime. It produces natural-sounding voice with good prosodic control and no GPU required. Deployed at `/opt/kokoro-venv/` on this VPS.

**Active voice for Baymax: `bm_fable`** (British Male) — expressive, warm, good for informal British tone. User chose this voice after evaluating samples. `bf_alice` is an alternative British Female voice if a female voice is preferred.

---

## Quick Start

```bash
# Activate the venv
source /opt/kokoro-venv/bin/activate

# Generate speech (bm_fable voice, 0.95 speed for natural pacing)
python -c "
import os
os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = '/opt/kokoro-venv/lib/python3.11/site-packages/espeakng_loader/libespeak-ng.so'
os.environ['PHONEMIZER_ESPEAK_DATA'] = '/opt/kokoro-venv/lib/python3.11/site-packages/espeakng_loader/espeak-ng-data'

from kokoro_onnx import Kokoro
import scipy.io.wavfile as wavfile

kokoro = Kokoro(
    '/root/.kokoro/models/thewh1teagle/kokoro-v1.0.fp16.onnx',
    '/root/.kokoro/voices/thewh1teagle/voices-v1.0.bin'
)
audio, sr = kokoro.create('Your text here.', voice='bm_fable', speed=0.95)
wavfile.write('/tmp/output.wav', sr, audio)
"
```

Portable install on any VPS: see `scripts/install.sh`

---

## Architecture

```
/opt/kokoro-venv/          — Python venv (3.11)
  lib/python3.11/site-packages/kokoro_onnx/  — Kokoro package
  lib/python3.11/site-packages/espeakng_loader/  — espeak-ng phonemizer
    libespeak-ng.so         — espeak-ng shared library
    espeak-ng-data/         — espeak-ng data files

/root/.kokoro/
  models/thewh1teagle/
    kokoro-v1.0.fp16.onnx  — ONNX model (169 MB)
  voices/thewh1teagle/
    voices-v1.0.bin         — All voices (28 MB)
```

---

## Setup Procedure (Already Completed)

The installation is done. If re-installing:

### 1. System dependency
```bash
apt-get install -y espeak-ng
```

### 2. Create venv and install packages
```bash
python3 -m venv /opt/kokoro-venv --system-site-packages
/opt/kokoro-venv/bin/pip install --upgrade pip
/opt/kokoro-venv/bin/pip install \
  kokoro-onnx \
  huggingface-hub \
  scipy \
  espeakng-loader \
  phonemizer-fork \
  misaki \
  num2words \
  numpy
```

### 3. Download model and voices (CORRECT sources)
```bash
# Model from GitHub releases (NOT HuggingFace — different format)
curl -L "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx" \
  -o /root/.kokoro/models/thewh1teagle/kokoro-v1.0.fp16.onnx

# Voices from same release (onnx-community repo has incompatible .bin format)
curl -L "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" \
  -o /root/.kokoro/voices/thewh1teagle/voices-v1.0.bin
```

### 4. Patch kokoro-onnx for raw float32 voice files
The installed `kokoro-onnx` uses `np.load()` for voices but the `.bin` files are raw float32. Patch:

```python
# File: /opt/kokoro-venv/lib/python3.11/site-packages/kokoro_onnx/__init__.py
# Replace all: self.voices: np.ndarray = np.load(voices_path)
# With try/except that falls back to np.fromfile

try:
    self.voices: np.ndarray = np.load(voices_path)
except ValueError:
    data = np.fromfile(voices_path, dtype=np.float32)
    self.voices = data.reshape(-1, 1, 256)
```

---

## Voice Options

All voices available in `voices-v1.0.bin`:

| Voice | Description | Best For |
|-------|-------------|----------|
| `bm_fable` | **British Male** — expressive, warm | **Baymax active voice** |
| `bm_george` | British Male — warm, measured | Alternative British male |
| `bm_lewis` | British Male — articulate | Formal British |
| `bf_alice` | British Female — warm, clear | Alternative British female |
| `bf_emma` | British Female — crisp, professional | Formal contexts |
| `hf_alpha` | Hybrid Female — natural all-rounder | General purpose |
| `af_heart` | American Female — very warm | Friendly tone |
| `af_bella` | American Female — rich | Quality narration |
| `am_michael` | American Male — deep, calm | Authoritative tone |

**Speed setting: 0.95** produces the most natural pacing. Range: 0.5–2.0.

---

## Streaming Audio Generation

Kokoro supports async streaming via `create_stream()`. For real-time pipeline:

```python
async def stream_audio():
    async for chunk, sr in kokoro.create_stream(text, voice='bf_alice', speed=0.95):
        yield chunk, sr  # chunk is np.ndarray of audio samples at 24kHz
```

---

## Hermes TTS Integration

Hermes supports custom TTS providers via `type: command` in config.yaml — **no plugin code needed**. Hermes writes text to a temp file, runs the command, and reads the audio output.

### Step 1: Deploy the TTS script

The script lives at `/root/.kokoro/kokoro_tts.py`. **It outputs `.ogg` (Opus) by default** — required for Telegram native voice bubbles. Do NOT change to `.wav` or `.mp3` if you want actual Telegram voice bubbles, not audio file attachments.

```python
#!/usr/bin/env python3
"""
Kokoro TTS Generator — Hermes Command Provider
Outputs .ogg (Opus) for Telegram native voice bubbles.
Run: python3 kokoro_tts.py --input /tmp/text.txt --output /tmp/audio.ogg
"""
import os, sys, argparse, subprocess

os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = '/opt/kokoro-venv/lib/python3.11/site-packages/espeakng_loader/libespeak-ng.so'
os.environ['PHONEMIZER_ESPEAK_DATA'] = '/opt/kokoro-venv/lib/python3.11/site-packages/espeakng_loader/espeak-ng-data'

from kokoro_onnx import Kokoro
import scipy.io.wavfile as wavfile

MODEL = '/root/.kokoro/models/thewh1teagle/kokoro-v1.0.fp16.onnx'
VOICES = '/root/.kokoro/voices/thewh1teagle/voices-v1.0.bin'
_kokoro = None

def get():
    global _kokoro
    if _kokoro is None:
        _kokoro = Kokoro(MODEL, VOICES)
    return _kokoro

def generate(text, out_path, voice='bm_fable', speed=0.95):
    kokoro = get()
    audio, sr = kokoro.create(text, voice=voice, speed=speed)
    wav_path = out_path.replace('.ogg', '_temp.wav')
    wavfile.write(wav_path, sr, audio)
    subprocess.run([
        'ffmpeg', '-y', '-i', wav_path,
        '-codec:a', 'libopus', '-b:a', '128k', '-ar', '48000',
        out_path
    ], capture_output=True)
    os.remove(wav_path)
    return out_path

if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--input', help='Text input file')
    a.add_argument('--output', required=True)
    a.add_argument('--voice', default='bm_fable')
    a.add_argument('--speed', type=float, default=0.95)
    a.add_argument('--format', default='ogg')
    args = a.parse_args()
    text = open(args.input).read().strip() if args.input else sys.stdin.read().strip()
    generate(text, args.output, voice=args.voice, speed=args.speed)
```

Make it executable: `chmod +x /root/.kokoro/kokoro_tts.py`

### Step 2: Add to config.yaml

Edit `~/.hermes/config.yaml`, replacing the `tts:` section with Kokoro as the default provider while keeping other providers:

```yaml
tts:
  provider: kokoro
  kokoro:
    voice: bm_fable
    speed: 0.95
  providers:
    kokoro:
      type: command
      command: "/opt/kokoro-venv/bin/python /root/.kokoro/kokoro_tts.py --input {text_path} --output {output_path} --voice bm_fable --speed 0.95"
      output_format: ogg
      timeout: 120
  edge:
    voice: en-US-AriaNeural
  elevenlabs:
    voice_id: pNInz6obpgDQGcFmaJgB
    model_id: eleven_multilingual_v2
  # ... other providers unchanged ...
```

### Step 3: Restart Hermes

In Telegram: send `/restart`. Kokoro bm_fable will now be used for all voice replies.

### Switching back to edge-tts

```yaml
tts:
  provider: edge   # revert
```

### Portable installer

Run on any VPS with Hermes to install Kokoro end-to-end:
```bash
curl -fsSL <install-url>/install.sh | bash
```
Or copy and run `/root/.kokoro/install/install.sh` directly.

---

## Prosody Rules — ALWAYS apply

Kokoro uses punctuation as prosodic cues. **Always include proper punctuation when sending text to Kokoro** — commas for pauses, periods for sentence ends, exclamation marks for emphasis, question marks for questions. Short punchy sentences with good punctuation = natural rhythm and pauses. Long unpunctuated text = flat and robotic output.

Example good input:
```
Right then! I am Baymax, your personal IT assistant. I may not be a genius, but I read the manuals cover to cover. Dad would have loved this one.
```

Example bad input (will sound flat):
```
right then i am baymax your personal it assistant i may not be a genius but i read the manuals cover to cover dad would have loved this one
```

## Pitfalls

### Telegram voice bubbles require `.ogg` (Opus), not `.wav` or `.mp3`
Telegram natively renders `.ogg`/`.oga` Opus files as voice bubbles. Any other format (`.wav`, `.mp3`) is sent as a downloadable audio file attachment, not a voice message. The TTS script must output `.ogg` and the Hermes config must have `output_format: ogg`. Hermes only auto-converts to Opus for built-in providers (`edge`, `neutts`, `minimax`, `xai`, `kittentts`, `piper`) — custom command providers must output `.ogg` directly.

### Hermes config — wrong provider format
Do NOT use `provider: kokoro` alone expecting it to work as a built-in. Hermes has no native Kokoro provider. You must use the `type: command` provider declaration under `tts.providers.kokoro`. The earlier skill revision incorrectly implied a plugin was needed — the command provider approach works natively.

### Hermes voice mode is read once at startup
The gateway loads `voice_modes.json` only at startup. Changes to that file while the gateway is running require a restart to take effect. See `baymax-voice` skill for details on voice mode configuration.

## References

- `references/voice-audit.md` — Full voice evaluation results, sample audio paths, test texts used
- `references/streaming-architecture.md` — Streaming TTS pipeline research and edge-tts findings
- `references/vps-infrastructure.md` — VPS specs and model benchmark data
- `scripts/install.sh` — Portable one-shot installer for any VPS with Hermes (outputs `.ogg` for Telegram voice bubbles)
