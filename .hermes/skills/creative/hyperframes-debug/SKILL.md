---
name: hyperframes-debug
description: Debug blank video issues in HyperFrames renders — scenes 1-9 blank, only last scene renders. Companion to hyperframes-troubleshooting. Prefer hyperframes-troubleshooting for blank/render issues as this skill contains outdated information.
---

# HyperFrames Debugging

**⚠ WARNING: This skill contains legacy information that may be outdated or actively wrong.** The hyperframes-troubleshooting skill is more current and accurate. Prefer it for all blank/render issues. The specific claim that "visibility kills ARE required despite the linter error" has been **proven incorrect** — adding visibility kills on clip elements causes the beginFrame blank-frame bug.

## Legacy Diagnosis

When renders show only some scenes (or only the last scene), scenes 1-9 blank:

### Diagnostic Command
```bash
for t in 1 3 6 10 15 22 30 40 50 56 58 63 67; do
  ffmpeg -y -i OUTPUT.mp4 -ss $t -vframes 1 -q:v 2 /tmp/scan_t${t}.jpg 2>/dev/null
  SZ=$(stat -c%s /tmp/scan_t${t}.jpg 2>/dev/null)
  echo "t=${t}s → ${SZ} bytes"
done
```
- 12460 bytes = blank white frame (no content rendered)
- 20000+ bytes = actual content

### Known Root Causes (verify against hyperframes-troubleshooting — some may be outdated)

1. **Duplicate GSAP timeline registration** — script has two `var tl = gsap.timeline(...)` declarations. First (empty) is registered with `window.__timelines['main']`, second (with all animations) is not. Fix: single `tl`, register AFTER all animations. ✅ CURRENT — still valid.

2. **HyperFrames 0.7.5 `static-frame dedup` regression** — ✅ CURRENT: Version 0.7.5 introduced a regression where animated frames in scenes 1–9 are incorrectly marked as duplicates of frame 0. The render shows only the last scene with content; earlier scenes show a static blank background. The `--no-static-dedup` flag does NOT bypass this. Fix: use pre-rendered scenes + ffmpeg concat, or per-scene isolate + stitch, or pin to `hyperframes@0.7.3`. See `hyperframes-troubleshooting` for the full workaround.

3. **`visibility: hidden` on clip elements conflicts with HyperFrames lifecycle** — ❌ LEGACY/MISLEADING: This skill previously said visibility kills were required despite the linter error. The hyperframes-troubleshooting skill proved this is WRONG. Adding visibility kills on clip elements causes the beginFrame blank-frame bug. The correct fix is to REMOVE visibility tweens, not add them.

4. **Missing `data-duration` on `<body>`** — ✅ CURRENT — HyperFrames runtime needs this to determine composition length.

5. **beginFrame API capture bug** — Legacy description. In 0.7.5 this is superseded by the `static-frame dedup` regression. The 0.7.5 behavior (minimal test works, full composition fails) is the same pattern but different root cause.

6. **Extra HTML files in project folder** — ✅ CURRENT: `index_full_backup.html`, `index_minimal.html` etc. get picked up as extra entry points causing "multiple_root_compositions" errors.

### Deprecated Pattern (do not use)

```javascript
// WRONG — this skill previously recommended this; it causes the blank-frame bug:
tl.to('#scene', { opacity: 0 }, t);
tl.set('#scene', { visibility: 'hidden' }, t + 0.25);  // ❌ DON'T DO THIS
```

The correct approach: let HyperFrames manage clip visibility via `data-start`/`data-duration`. Remove all `visibility` tweens from clip elements.

### Quick Test: Minimal 3-Scene Composition

See hyperframes-troubleshooting for the authoritative minimal test template. The key pattern that works: use `class="clip scene"` with separate `.clip` and `.scene` CSS rules, and `--no-clip-visibility` flag.
