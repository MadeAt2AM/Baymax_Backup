# Kokoro Voice Audit — 2026-07-01

## Test Text
"Right then! I am Baymax, your personal IT assistant. I may not be a genius, but I read the manuals cover to cover. Dad would have loved this one."

## Voices Evaluated

### British Male (Baymax character match)
| Voice | Duration | File | Notes |
|-------|----------|------|-------|
| `bm_george` | 10.1s | /tmp/kokoro_bm_george.mp3 | Classic British, warm, measured — strong candidate |
| `bm_lewis` | 10.1s | /tmp/kokoro_bm_lewis.mp3 | British, articulate, slightly formal |
| `bm_daniel` | 8.1s | /tmp/kokoro_bm_daniel.mp3 | British, lighter tone |
| `bm_fable` | 8.7s | /tmp/kokoro_bm_fable.mp3 | **SELECTED — British, expressive, good for informal warmth** |
| `am_michael` | 10.6s | /tmp/kokoro_am_michael.mp3 | Deep, American, confident |
| `am_onyx` | 8.7s | /tmp/kokoro_am_onyx.mp3 | Rich American, lower register |
| `am_puck` | 9.5s | /tmp/kokoro_am_puck.mp3 | Lighter, quicker cadence |
| `am_adam` | 8.7s | /tmp/kokoro_am_adam.mp3 | Clear, neutral, approachable |

### Other English voices (British Female)
| Voice | Duration | File | Notes |
|-------|----------|------|-------|
| `bf_alice` | 8.8s | /tmp/kokoro_bf_alice.mp3 | British Female, warm, alternative pick |
| `bf_emma` | 8.5s | /tmp/kokoro_bf_emma.mp3 | British Female, crisp, professional |
| `hf_alpha` | 9.5s | /tmp/kokoro_hf_alpha.mp3 | Hybrid Female, natural all-rounder |
| `af_heart` | 9.2s | /tmp/kokoro_af_heart.mp3 | American Female, very warm |
| `af_bella` | 9.7s | /tmp/kokoro_af_bella.mp3 | American Female, rich |
| `af_nova` | 8.5s | /tmp/kokoro_af_nova.mp3 | American Female, bright |

## Selection Decision

**User chose `bm_fable`** for Baymax's warm British informal tone.

Ranking for Baymax character:
1. `bm_george` — warm British, measured, strong alternative
2. `bm_fable` — expressive, informal, good enthusiasm for tech
3. `bm_lewis` — articulate British, professional but friendly

## Key Technical Findings

- Model: `/root/.kokoro/models/thewh1teagle/kokoro-v1.0.fp16.onnx` (169 MB)
- Voices: `/root/.kokoro/voices/thewh1teagle/voices-v1.0.bin` (28 MB)
- Generation speed: ~0.95x real-time (5-10s audio in 5-10s wall time on VPS)
- Speed setting: 0.95 for natural pacing
- Output sample rate: 24kHz mono
