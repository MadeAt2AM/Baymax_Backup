# HyperFrames Session Log: hermes-skills-reel blank-frame bug (June 22 2026)

## Session: `20260622_145216_574833` (June 22, 2026, 02:24 PM)

## Render Command
```bash
cd /root/.hermes/projects/hermes-skills-reel
npx hyperframes render --no-clip-visibility --quality high --output fresh_render.mp4
```

## Environment
| Variable | Value |
|----------|-------|
| `HYPERFRAMES_CACHE_DIR` | `cache` |
| `PUPPETEER_SKIP_DOWNLOAD` | `true` |
| `PRODUCER_LOW_MEMORY_MODE` | `true` (auto-detected: 7941MB RAM < 8192MB threshold) |
| HyperFrames CLI | `0.7.3` |
| Node.js | `v22.22.3` |
| Chrome Headless Shell | `149.0.7827.22` |
| Platform | Linux x64 |

## Key Diagnostic Log Lines (capture startup)

```
[INFO] [Render] Pipeline started {"platform":"linux","nodeVersion":"v22.22.3","fps":{"num":30,"den":1},"format":"mp4","quality":"high","browserGpuMode":"auto","forceScreenshot":false,"protocolTimeout":300000,"browserTimeout":120000,"pageNavigationTimeout":60000,"playerReadyTimeout":45000}
[INFO] Compiled composition metadata {"entryFile":"index.html","staticDuration":68,"width":1080,"height":1920}
[INFO] [Render] Low-memory render profile active — screenshot capture, auto-worker calibration skipped, pinned to 1 worker.
[INFO] [Render:trace] phase=capture_streaming status=start workerCount=1 forceScreenshot=true
[BrowserManager] Browser launched (HeadlessChrome/149.0.7827.22, screenshot, gl=--use-gl=angle --use-angle=gl-egl, headlessShell=true, platform=linux)
[initSession:screenshot] page.goto start (0ms)
[initSession:screenshot] page.goto complete (134ms)
[initSession:screenshot] pollHfReady complete (146ms)
[initSession:screenshot] pollSubCompositionTimelines complete (149ms)
[initSession:screenshot] applyVideoMetadataHints complete (149ms)
[initSession:screenshot] pollVideosReady complete (150ms)
[initSession:screenshot] images ready + decoded (152ms)
[initSession:screenshot] fonts ready (297ms)
[initSession:screenshot] tailwind ready (298ms)
[initSession:screenshot] static-frame dedup: 977/2040 frame(s) reusable (48%, verified) (11918ms)
  ██████░░░░░░░░░░░░░░░░░░  25%  Starting frame capture
```

## The Smoking Gun

`static-frame dedup: 977/2040 frame(s) reusable (48%, verified) (11918ms)`

This line appears BEFORE any frames are captured — it's a pre-flight check that runs during `pollHfReady`. The 977 "reusable" frames were detected at t=0 (page load), before HyperFrames' player clock had started. This is the fingerprint of `paused: false` — GSAP fires all animations immediately, HyperFrames samples the canvas and sees identical state across all "unique" timestamps, marking them all as duplicates of the initial frame.

## Confirming Frame Content

Frame size comparison from `fresh_render.mp4`:

| Timestamp | Frame Size | Content |
|-----------|-----------|---------|
| t=1s | 13,250 bytes | Blank / white (the static-dedup frame) |
| t=5s | 13,250 bytes | Blank (identical — same dedup frame) |
| t=30s | 13,250 bytes | Blank (still the dedup frame) |
| t=45s | 13,250 bytes | Blank (still the dedup frame) |
| t=57s | 56,030 bytes | Actual content (scene 10 CTA) |
| t=60s | 56,040 bytes | Actual content (final frame) |

Frame size changes only at t=57s+ — everything before is the same 13KB blank frame being reused 977 times.

## Bug: `--no-clip-visibility` Did Not Fix It

Same 977/2040 reused frames. The `--no-clip-visibility` flag controls whether HyperFrames injects `visibility: hidden` on clip elements when their duration expires — it has no effect on whether GSAP fires animations on page load.

## Root Cause: `paused: false`

```js
// WRONG — in per_scene/scene1.html (and original index.html)
var tl = gsap.timeline({ paused: false });  // ← animations fire at wall-clock t=0

// CORRECT
var tl = gsap.timeline({ paused: true });   // ← animations wait for HyperFrames clock
```

## Low-Memory Mode Triggered

`PRODUCER_LOW_MEMORY_MODE=true` was auto-detected (7941MB RAM < 8192MB threshold). This forced:
- Single-worker capture (no parallelization)
- `forceScreenshot: true` (screenshot capture path, not videoExtract)

This is not a bug — it is correct behavior on memory-constrained hosts. The blank-frame bug would occur regardless of worker count.

## Files from This Session

| File | Location |
|------|----------|
| Main composition | `/root/.hermes/projects/hermes-skills-reel/index.html` (50KB, 1099 lines) |
| Mini test (working) | `/root/.hermes/projects/hf-mini-test/index.html` (5KB) |
| Bug report | `/root/.hermes/projects/hermes-skills-reel/HYPERFRAMES_BUG_REPORT.md` |
| Render log | `/tmp/hf_render_full.log` (captured to `/root/hf-bug-report/render_log.txt`) |
| Blank early frame | `/root/hf-bug-report/frame_blank_t1s.jpg` (13KB JPEG, 1080x1920) |
| Content later frame | `/root/hf-bug-report/frame_content_t60s.jpg` (56KB JPEG, 1080x1920) |
| Per-scene compositions | `/root/.hermes/projects/hermes-skills-reel/per_scene_v2/scene1/` |
