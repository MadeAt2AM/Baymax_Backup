# beginFrame Blank-Frame Debugging — hermes-skills-reel Session

## Key Finding

**The bug predates all our changes.** `final_nolm.mp4` (the original unmodified render from before any fixes were applied) shows t=0–57s as 12KB blank frames and t=60–68s as content (46–47KB). This was NOT caused by any of our CSS/visibility changes — the composition was always broken.

Frame size reference:
- Blank/white: ~12KB (t=0–57 in original render)
- Content: 40–57KB (t=57–68 in original render, t=60+ in all new renders)

## What We Tried (All Failed for the full composition)

| Attempt | Result |
|---------|--------|
| Removed all 10 `visibility` tweens from clip elements | No change |
| Changed `.clip` from `position:absolute` to `position:fixed` | No change |
| Changed `.clip` from `position:fixed; top:0; left:0; width:1080px; height:1920px` to `position:fixed; inset:0` | No change |
| Added `class="scene"` to all clip divs | No change |
| `--no-clip-visibility` flag | No change for full composition |
| `--no-low-memory-mode` combinations | No change |
| `--no-clip-visibility --no-low-memory-mode` together | No change |

## What Works

The minimal 3-scene test (`hf-mini-test/index.html`) renders correctly at ALL timestamps (32–39KB per frame) with `--no-clip-visibility --no-low-memory-mode --quality draft`. The minimal test uses:
- Same GSAP 3.14.2
- Same `position:fixed` clip positioning
- Same `data-start`/`data-duration` attributes
- Same `window.__timelines['main']` registration pattern
- Same opacity fade transitions via flash divs

**Per-scene isolate approach also works**, and is the confirmed workaround for the full composition. Key requirement: `paused: true` in per-scene HTML files. If `paused: false` is used, all output frames are identical still images (animations fire before capture begins).

## Separate Discovery: `paused: false` in Per-Scene Files

**Symptom:** Per-scene renders with `gsap.timeline({ paused: false })` produce identical frames at all timestamps.

**Root cause:** `paused: false` fires animations immediately on page load in the headless browser, before HyperFrames' capture begins. The GSAP timeline runs to completion while the browser is still initializing — every captured frame shows the fully-animated end state.

**Fix:** Always `paused: true`. The HyperFrames player controls when playback starts, and it begins at t=0 relative to the isolated scene's `data-duration`.

## The Discrepancy

The full composition (11 clips, 68s, 66 animated elements) fails consistently.
The mini test (3 clips, 12s, 12 animated elements) works perfectly.

Structural differences between them:

| Element | Full Composition | Mini Test |
|---------|-----------------|-----------|
| `.clip` class | `class="clip"` | `class="clip scene"` |
| Clip layout | Inline `style="display:flex..."` on clip div | Separate `.scene { position:fixed; inset:0; display:flex... }` class |
| `.scene` CSS | `position:absolute; inset:0;` | `position:fixed; inset:0;` |
| `#tr-flash-N` | 9 divs with `position:fixed; z-index:990` | 2 divs with same pattern |
| Particle system | JS-driven particle div with seeded PRNG | None |
| Background | Dot-grid via `body::before` | Solid `#0a0a0f` |
| Scene content | Complex nested divs, emoji, Malayalam text | Simple text |

## Static-Dedup Pattern

```
[initSession:beginframe] static-frame dedup: disabled (capture mode beginframe, not screenshot) (289ms)
[static-dedup] reused 1720/2040 frame(s) (48%), est. ~94769ms saved
```

This means:
- 68s × 30fps = 2040 total frames
- 1720 frames marked as "reused" (these are the blank t=0–57 frames)
- Only 320 unique frames (t=57–68s actually captured as unique content)

The `[initSession:beginframe]` line confirms beginFrame capture is active.
The `static-dedup disabled` message confirms deduplication was OFF — the renderer genuinely tried to capture each frame separately.

## Files

- `/root/.hermes/projects/hermes-skills-reel/index.html` — main composition (11 clips, 68s)
- `/root/.hermes/projects/hf-mini-test/index.html` — working minimal test (3 clips, 12s)
- `/root/.hermes/projects/hermes-skills-reel/final_nolm.mp4` — original render (935KB)
- `/root/.hermes/projects/hermes-skills-reel/per_scene_fixed/hermes_skills_v2.mp4` — final fixed render using per-scene isolate workaround (2.14MB, 68s, motion confirmed at all timestamps)

## Root Cause Summary

beginFrame seek in the headless browser renders blank at early timestamps for complex multi-scene (10+) compositions, even when GSAP and HTML are correct. The seek IS happening (all frame numbers captured) but the browser renders a blank canvas at those positions for the full composition.

**Confirmed working workaround:** Per-scene isolate + ffmpeg concat (see below).

---

## Correct Per-Scene Isolate + Stitch Workaround

### Step 1 — Create isolated per-scene HTML files

Each scene gets its own HTML file with:
- Its own `<body data-composition-id="main" data-start="0" data-duration="{scene_duration}">`
- **Only that scene's clip div** in the DOM (no other scene divs)
- GSAP timeline with animation times RELATIVE to t=0 (not absolute video timestamps)
- `paused: true` — the player starts at t=0 inside the isolated file

```
Project structure:
  my-video/
    index.html           ← empty container (data-composition-id on body, no clip divs)
    scenes/
      scene1.html        ← isolated 4s scene
      scene2.html        ← isolated 4s scene
      ...
    scene1.mp4
    scene2.mp4
    ...
    final.mp4
```

**Critical rules for per-scene HTML files:**
- `data-duration` = the scene's own duration (e.g. 4, 7, 8 — NOT the cumulative absolute time)
- GSAP timeline positions are RELATIVE to the scene start (scene 3 starting at t=8 in the full video → timeline positions 0.2, 0.5, 1.2 in the isolated 4s file)
- All `tl.set('#sceneN', ...)` and `tl.from/to(...)` use relative timestamps starting from 0
- `window.__timelines['main'] = tl` must be registered
- GSAP timeline is ALWAYS `gsap.timeline({ paused: true })` — never `paused: false`
- The `tl.to('#sceneN', { opacity: 0, duration: 0.2 }, duration - 0.2)` exit tween fires at the end of the scene's own timeline

### Step 2 — Render each scene

```bash
# Render from the PROJECT ROOT directory, use -c to target the scene HTML
cd /path/to/my-video
npx hyperframes render . -c scenes/scene1.html -o scene1.mp4
npx hyperframes render . -c scenes/scene2.html -o scene2.mp4
# ... repeat for all scenes
```

**Common error:** `✗ Not a directory: /path/to/scene1.html`
→ Cause: passed the HTML file path directly instead of the project root + `-c scenes/scene1.html`

**Common error:** `✗ No composition found`
→ Cause: no `index.html` in the project root, OR extra HTML files with `data-composition-id` in the project root alongside `index.html`. Create a minimal `index.html` with just the body attributes (no clip divs).

**Important lint warnings to ignore:** `root_missing_composition_id`, `root_missing_dimensions`, `missing_timeline_registry`, `multiple_root_compositions` — these fire because per-scene files don't have all the main project's clips. Use `--strict` to override if needed.

### Step 3 — Verify motion before stitching

Always check frames are NOT identical before concat:
```bash
for scene in scene1 scene2 scene3; do
  SZ1=$(ffmpeg -y -i ${scene}.mp4 -ss 1 -vframes 1 -q:v 2 /tmp/${scene}_t1.jpg 2>/dev/null && stat -c%s /tmp/${scene}_t1.jpg)
  SZ2=$(ffmpeg -y -i ${scene}.mp4 -ss 3 -vframes 1 -q:v 2 /tmp/${scene}_t2.jpg 2>/dev/null && stat -c%s /tmp/${scene}_t2.jpg)
  echo "${scene}: t=1s → ${SZ1} bytes, t=3s → ${SZ2} bytes"
done
# Different byte sizes = motion confirmed
```

### Step 4 — Concatenate with ffmpeg

```bash
cat > concat.txt << 'EOF'
file 'scene1.mp4'
file 'scene2.mp4'
file 'scene3.mp4'
file 'scene4.mp4'
file 'scene5.mp4'
file 'scene6.mp4'
file 'scene7.mp4'
file 'scene8.mp4'
file 'scene9.mp4'
file 'scene10.mp4'
file 'finalframe.mp4'
EOF

ffmpeg -y -f concat -safe 0 -i concat.txt \
  -c:v libx264 -crf 18 -preset fast \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1" \
  -r 30 -movflags +faststart \
  final.mp4
```

### Step 5 — Validate final output

```bash
# Duration check
ffprobe -v quiet -show_entries format=duration,size -of csv=p=0 final.mp4

# Motion check at multiple timestamps
for t in 1 5 12 20 30 42 57 65; do
  SZ=$(ffmpeg -y -i final.mp4 -ss $t -vframes 1 -q:v 2 /tmp/fv_t${t}.jpg 2>/dev/null && stat -c%s /tmp/fv_t${t}.jpg)
  echo "t=${t}s → ${SZ} bytes"
done
# Real content: >30KB typically; blank/white: ~12KB
```

## Related Skills

- [hyperframes SKILL.md](../hyperframes/SKILL.md) — creation workflow, setup, lint/validate/inspect/render pipeline
- [hyperframes/composition.md](../hyperframes/references/composition.md) — data attributes, timeline contract, non-negotiable rules
- [hyperframes/troubleshooting.md](../hyperframes/references/troubleshooting.md) — env vars, common render errors, `hyperframes doctor` output interpretation
