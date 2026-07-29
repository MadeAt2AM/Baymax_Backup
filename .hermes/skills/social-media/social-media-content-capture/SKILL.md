---
name: social-media-content-capture
description: "Transcribe social video/audio URLs into timestamped text."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [social-media, transcription, video, audio, instagram, youtube, tiktok, twitter, groq, whisper, yt-dlp, ffmpeg]
---

# Social Media Content Capture

End-to-end pipeline for downloading social media video/audio content and producing timestamped transcripts. Triggered when the user wants the *text* from a reel/short/podcast, not just the metadata.

## When to use

Use when the user asks for any of:

- "Transcribe this reel / video / TikTok / tweet video"
- "Get me the text from this Instagram post"
- "Pull the captions / content from this URL"
- "Transcribe this podcast episode"

**Not for:** tool installation (use `agent-reach`), pure metadata scraping without audio, or content *creation* (use `content-creation-skills`).

## Pipeline (4 stages)

### Stage 1 — Pick the right tool to fetch the media

| Source | Tool to try first | Fallback if first tool fails |
|---|---|---|
| Instagram reel/post | `opencli instagram download` (requires bridge) | `yt-dlp --cookies-from-browser chrome -o "x.%(ext)s" <url>` |
| YouTube (incl Shorts) | `yt-dlp` (no auth needed) | — |
| TikTok | `yt-dlp --cookies-from-browser chrome` | — |
| Twitter/X video | `yt-dlp --cookies-from-browser chrome` or `twitter` CLI | — |
| Podcast (xiaoyuzhou, etc) | `bash ~/.agent-reach/tools/xiaoyuzhou/transcribe.sh <url>` | extract audio first → Stage 3 |

**Auth check first:** Before any Instagram call, run:

```bash
source ~/.agent-reach-venv/bin/activate
opencli instagram whoami -f json --window background --site-session persistent
```

If you get `Browser Bridge extension not connected` → bridge is offline → skip OpenCLI and go straight to `yt-dlp --cookies-from-browser chrome`. Don't waste a turn re-trying OpenCLI.

### Stage 2 — Extract clean audio (mandatory before Groq Whisper)

Groq's `/audio/transcriptions` accepts mp3, mp4, m4a, wav, webm — but a vertical 1080×1920 mp4 with embedded audio has triggered Cloudflare 1010 in practice. **Always pre-extract to mono 16kHz:**

```bash
ffmpeg -hide_banner -loglevel error -i input.mp4 \
  -vn -ac 1 -ar 16000 -c:a pcm_s16le audio.wav
# Smaller variant: -c:a libopus -b:a 64k audio.ogg
```

Mono 16kHz is the optimal input shape for Whisper (matches its training distribution).

### Stage 3 — Transcribe (Groq Whisper, Cloudflare-safe)

Use the helper at `scripts/transcribe_groq.py` from this skill:

```bash
source ~/.agent-reach-venv/bin/activate
python3 ~/.hermes/skills/social-media/social-media-content-capture/scripts/transcribe_groq.py \
  audio.wav transcripts/output.txt
```

The helper sets `User-Agent: curl/8.5.0` to bypass Cloudflare 1010. Output format: timestamped segments + clean full text.

**If Groq is unavailable**, fall back to local Faster-Whisper (already installed on this host):

```python
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, _ = model.transcribe("audio.wav")
for s in segments: print(f"[{s.start:6.2f} - {s.end:6.2f}] {s.text}")
```

### Stage 4 — Organize + hand back

- Move source video → `media/`
- Move transcript → `transcripts/`
- If the user wants a structured output (spec sheet, summary, action plan), write it next to the transcript and link the source file in a header block.
- Delete intermediate ffmpeg files (the `.ogg` / `.wav` you made just for transcription).

## Pitfalls

### OpenCLI bridge offline (most common Instagram failure)

Symptom: `opencli instagram whoami` returns `BROWSER_CONNECT: Browser Bridge extension not connected`. The OpenCLI daemon is running but no Chrome extension is talking to it.

**Fix:** skip OpenCLI entirely. `yt-dlp --cookies-from-browser chrome` reads Chrome's encrypted cookie store directly using the OS keyring — it decrypts the `sessionid` HttpOnly cookie that rookiepy cannot.

```bash
yt-dlp --cookies-from-browser chrome -o "reel.%(ext)s" "https://www.instagram.com/reel/..."
```

Works for Instagram, Twitter, TikTok, Reddit, and anything else Chrome has logged-in cookies for.

### rookiepy fails on Instagram sessionid

`agent-reach configure --from-browser chrome` extracts Twitter/X, Xiaohongshu, and Xueqiu cookies successfully — but Instagram's `sessionid` is encrypted with a Chrome v20+ key that rookiepy doesn't decode. The skill reports Instagram as "configured" but it isn't. Always use yt-dlp's native Chrome keyring extractor instead.

### Groq Cloudflare 1010

Symptom: `Groq HTTP 403: error code: 1010` on multipart upload. The request is well-formed and authorized, but Cloudflare blocks the default Python `urllib` User-Agent.

**Fix:** send `User-Agent: curl/8.5.0` (or any browser-style UA). Already baked into `scripts/transcribe_groq.py`. If you hit this with a different client (curl, requests, etc.), add the header manually.

### xiaoyuzhou transcribe.sh is URL-locked

`~/.agent-reach/tools/xiaoyuzhou/transcribe.sh` only accepts Xiaoyuzhou URLs (positional arg validation enforces this). For local audio files, Instagram reels, YouTube, etc., use `scripts/transcribe_groq.py` from this skill directly.

### Groq file format gotcha

The `.mp4` extension can trigger Cloudflare blocks even after audio extraction. `.wav` and `.ogg` are reliable. Always extract first with ffmpeg, don't try to upload the raw reel.

### Whisper timestamps for short reels

Whisper sometimes returns absurdly long segments on short reels (one segment covering the whole 60s). If you need sentence-level timestamps, split the audio at natural pauses or use word-level timestamps (`word_timestamps=True` in faster-whisper).

## Verification

After transcription, always:

1. Read the first 5 lines of the output to confirm the content makes sense
2. Sanity-check segment count against duration (a 60s reel typically yields 8–15 segments)
3. If the user gave a URL and asked for downstream work (spec sheet, summary, action items), produce that — don't just dump the transcript. Link back to the transcript file path so the user can review raw output.

## Linked files

- `scripts/transcribe_groq.py` — Cloudflare-safe Groq Whisper transcription helper (Python stdlib only, no `requests` dep)
- `references/instagram-reel-recipe.md` — full worked example: Greg Isenberg reel → transcript → spec sheet
