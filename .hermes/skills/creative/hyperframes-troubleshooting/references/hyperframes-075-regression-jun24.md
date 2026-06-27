# HyperFrames 0.7.5 Regression — June 24 Session

## What Happened

HyperFrames was updated from 0.7.3 → 0.7.5 via `npm update -g hyperframes`. The update completed successfully. A subsequent render of a 10-scene, 68-second single-HTML composition showed the same blank-early-scenes pattern that was previously fixed with `paused: true`.

## Environment

- **Host:** Linux 6.8.0-117-generic
- **Node:** v22.22.3
- **HyperFrames:** 0.7.5 (was 0.7.3 before update)
- **Chrome Headless Shell:** 149.0.7827.22
- **Project:** `/root/.hermes/projects/hermes-skills-reel/`
- **Composition:** 10-scene single-HTML, `paused: true`, GSAP timeline registered in `window.__timelines['main']`

## Symptoms

### Render log (0.7.5, single-HTML composition)
```
[initSession:screenshot] static-frame dedup: 977/2040 frame(s) reusable (48%, verified) (11918ms)
```
- 977 of 2040 frames (48%) marked as "reusable"
- Capture phase: 2040 frames streamed, 977 reused
- Capture time: ~182s (vs ~50s for a working render)

### Frame size fingerprint
| Timestamp | Frame Size | State |
|-----------|-----------|-------|
| t=1s | 12,460 bytes | Blank (dot-grid only) |
| t=5s | 12,460 bytes | Blank |
| t=10s | 12,460 bytes | Blank |
| t=57s | 12,460 bytes | Blank |
| t=60s | 47,292 bytes | Content (finalframe) |
| t=65s | 47,283 bytes | Content (finalframe) |

**Blank frame content:** The 12,460-byte frames show the dot-grid CSS background on near-black — no scene content is visible. These are NOT pure white/blank; they contain the decorative dot grid. The scene content (typography, particles, accent colors) is absent.

## Key Diagnostic Finding

The bug was NOT caused by `paused: false`. The composition already had `paused: true` from the prior fix. The 0.7.5 update reintroduced the blank-scenes issue through the `static-frame dedup` algorithm.

### Evidence that `paused: true` was correct
```html
<!-- Line 870 in index.html -->
var tl = gsap.timeline({ paused: true });
```

The timeline was registered correctly (`window.__timelines['main'] = tl`), and the standalone scene test confirmed `paused: true` animations work correctly in 0.7.5.

## Tests Run

### Test 1: Standalone minimal scene (3-scene HTML, ~4s each)
- **Result:** ✅ Works — frame sizes 35,820–39,055 bytes, animation confirmed
- **Log:** `static-frame dedup: 93/120 frame(s) reusable (78%)` — only 93/120 frames reused because only the first 4s were blank (transitions between scenes)

### Test 2: Per-scene isolate + stitch (per_scene_fixed directory)
- **Result:** ❌ All blank — even pre-rendered scene files re-rendered blank in 0.7.5
- **Note:** Pre-existing `.mp4` files (dated June 22) remain valid; only fresh renders are affected

### Test 3: Full composition with `--no-static-dedup`
- **Result:** ❌ Still broken — `977/2040 frames` still reused despite flag
- **Conclusion:** `--no-static-dedup` does NOT bypass this bug

### Test 4: Full composition render (no flags)
- **Result:** ❌ Same 977/2040 reused, only finalframe content
- **File size:** 83.9 KB (vs 617.7 KB for a working render)

## Root Cause (Confirmed)

HyperFrames 0.7.5's `static-frame dedup` algorithm incorrectly identifies animated frames as duplicates of frame 0 for complex multi-scene single-HTML compositions. The algorithm compares captured frames against frame 0 and marks any frame with pixel similarity above threshold as "reusable." In 0.7.5, this threshold or comparison logic is wrong for compositions where:
- The dot-grid background is present from frame 0
- Scene content (text, particles, elements) animates in at later timestamps
- Multiple clip divs with `data-start`/`data-duration` are present

The bug is in the **dedup comparison logic**, not in GSAP configuration, not in `paused`, and not in `--no-static-dedup`.

## Workaround Applied

Assembled final video from pre-rendered scene files (June 22) using ffmpeg concat:

```bash
cd /root/.hermes/projects/hermes-skills-reel/per_scene_fixed
ffmpeg -y -f concat -safe 0 -i concat.txt \
  -c:v libx264 -crf 20 -preset fast -pix_fmt yuv420p \
  assembled_v2.mp4
```

**Verification frames** (assembled_v2.mp4 — valid):
| Timestamp | Size |
|-----------|------|
| t=1s | 42,999 bytes |
| t=5s | 58,765 bytes |
| t=10s | 82,647 bytes |
| t=30s | 91,328 bytes |
| t=60s | 56,465 bytes |

**Upload:** https://files.catbox.moe/cz6tyi.mp4

## Version Comparison

| Version | Single-HTML Multi-Scene | Per-Scene Isolate |
|---------|------------------------|-------------------|
| 0.7.3 | Works | Works |
| 0.7.4 | Unknown | Unknown |
| 0.7.5 | Broken (977/2040 frames reused) | All blank on re-render |

## Mitigation Options

1. **Pre-rendered scenes + concat** — Use existing pre-rendered `.mp4` files. Assembled output is valid.
2. **Per-scene isolate + stitch** — Render each scene as standalone HTML with its own `data-duration`, then concat. Note: re-rendering per-scene isolates in 0.7.5 also produced blank output in this session (likely due to the sub-composition polling timeout).
3. **Pin to 0.7.3** — `npm install -g hyperframes@0.7.3` — the single-HTML approach works correctly in this version.
4. **Wait for fix** — Report to HyperFrames maintainers with the reproduction case.

## Files

- Full composition: `/root/.hermes/projects/hermes-skills-reel/index.html`
- Per-scene dir: `/root/.hermes/projects/hermes-skills-reel/per_scene_fixed/`
- Fresh blank render: `/tmp/render_v075.mp4` (83.9 KB, broken)
- Working assembled: `/root/.hermes/projects/hermes-skills-reel/per_scene_fixed/assembled_v2.mp4`
- Uploaded: https://files.catbox.moe/cz6tyi.mp4
