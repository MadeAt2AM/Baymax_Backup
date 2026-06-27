---
name: hyperframes-troubleshooting
description: Debug and fix blank/black video renders, lint errors, and GSAP animation issues in HyperFrames compositions. Load this skill when a HyperFrames render produces a blank or black video, or when lint reports gsap_animates_clip_element errors. The companion skill to 'hyperframes' — this skill covers diagnostics and fixes, not creation workflows.
version: 1.1.0
author: baymax (Hermes agent)
license: MIT
platforms: [linux]
prerequisites:
  commands: [ffmpeg, npx]
metadata:
  hermes:
    tags: [hyperframes, video, debugging, gsap, render-fix]
    category: creative
    requires_toolsets: [terminal]
---

# HyperFrames Troubleshooting

Debug a HyperFrames render that produces a blank/black video, or fix lint errors before rendering.

**Load this skill alongside `hyperframes` when debugging render failures.**

## Diagnostic Workflow

### Step 1 — Run lint first

Always start here. The linter tells you exactly what's wrong structurally:

```bash
cd /path/to/project && npx hyperframes lint
```

Fix all `✗` errors before touching anything else. Common errors and their fixes are below.

### Step 2 — Check for multiple root compositions

```bash
ls /path/to/project/*.html
```

If you see `index_full_backup.html`, `index_minimal.html`, or any extra `.html` file alongside `index.html`, the linter will report `multiple_root_compositions`. **Delete or rename the extras before rendering** — the renderer picks up all `data-composition-id` HTML files in the project root.

### Step 3 — Extract frames to confirm blank output

```bash
ffmpeg -i output.mp4 -ss 3 -vframes 1 preview.jpg   # early frame
ffmpeg -i output.mp4 -ss 30 -vframes 1 preview.jpg  # mid frame
ffmpeg -i output.mp4 -ss 55 -vframes 1 preview.jpg  # late frame
```

Blank frames are ~12KB (uniform white). Frames with actual content are 40KB+.

### Step 4 — Check pixel values

```bash
# Compare file sizes — blank frames are small and uniform
for t in 2 10 30 50; do
  ffmpeg -y -i output.mp4 -ss $t -vframes 1 /tmp/frame_t${t}.jpg
  echo "t=${t}s → $(stat -c%s /tmp/frame_t${t}.jpg) bytes"
done
```

If ALL frames are ~12KB, the composition is rendering blank. If only early scenes are blank but later scenes have content, the issue is animation timing or clip lifecycle.

---

## Common Errors and Fixes

### `✗ gsap_animates_clip_element` (10 errors for 10 scenes)

**Error text:** `GSAP animation sets visibility on a clip element. Selector "#scene1" resolves to <div id="scene1" class="clip">`

**Root cause:** You added `tl.set('#sceneN', { visibility: 'hidden' })` on clip elements to hide scenes after they exit. This **fights the HyperFrames framework's own clip lifecycle**. HyperFrames manages clip visibility automatically via `data-start`/`data-duration` — when a clip's duration expires, the framework hides it. Overriding visibility from GSAP corrupts the lifecycle during rendering, causing scenes to appear blank.

**Fix:** Remove ALL `tl.set('#sceneN', { visibility: 'hidden' })` calls from the GSAP timeline. Let the framework handle when clips disappear.

**Before (WRONG):**
```js
tl.to('#scene1', { opacity: 0, duration: 0.2 }, 4.0);
tl.set('#scene1', { visibility: 'hidden' }, 4.2);  // ❌ REMOVE THIS
tl.set('#scene2', { opacity: 1 }, 4.2);
```

**After (CORRECT):**
```js
tl.to('#scene1', { opacity: 0, duration: 0.2 }, 4.0);
tl.set('#scene2', { opacity: 1 }, 4.0);
// No visibility tween — framework auto-hides scene1 when scene2 starts
```

The rule: **never animate `visibility` or `display` on clip elements from GSAP**. The framework owns clip lifecycle.

### `✗ root_missing_composition_id` / `✗ root_missing_dimensions`

**Root cause:** Extra HTML files in the project root, OR the linter expects `data-*` attributes directly on `<body>` but the composition uses a `#stage` child div. The blueprint linter is not always accurate — it may flag these even when the `#stage` pattern (below) is used and the render succeeds.

**Correct pattern for complex/multi-scene compositions:** Put `data-composition-id` on `<body>` (to name the composition for the runtime), and put the rest of the composition metadata on a `#stage` child div:
```html
<body data-composition-id="main">
  <div id="stage"
       data-composition-id="main"
       data-width="1080"
       data-height="1920"
       data-start="0"
       data-duration="27">
    <!-- all scenes here -->
  </div>
</body>
```
**Note:** This pattern renders correctly even when lint reports `✗ root_missing_composition_id` — the lint error is a false positive from the blueprint checker. The render pipeline reads the `#stage` div at runtime and ignores the lint complaint. Always verify with `ffprobe` on the output file rather than trusting lint output alone.

### `⚠ overlapping_gsap_tweens` on `#s10arrow`

**Error:** Two GSAP tweens overlap on `#s10arrow` for `y` between 58.40s and 58.90s.

**Fix:** Add `overwrite: "auto"` to the second tween, or shorten the first tween's duration.

### `✗ scene_layer_missing_visibility_kill` (appears AFTER removing visibility tweens)

# HyperFrames Troubleshooting & Workaround Skill

## Known Issue: beginFrame Blank Frames in Multi-Scene Compositions (0.7.5 Regression)

**Symptom**: When rendering a multi-scene HyperFrames composition (10+ scenes), `hyperframes render` produces a video where only the last scene has visible content. All earlier scenes render as a static dot-grid background (~12KB per frame) while the final scene renders correctly (~47–55KB per frame).

**Root Cause — HyperFrames 0.7.5 Regression:** The `static-frame dedup` feature misidentifies animated frames as duplicates of frame 0. The headless browser seek works correctly (all frame numbers are captured), but the dedup logic marks scenes 1–9 as reusable based on pixel-similarity checks against the blank frame 0 state. This happens **even when `paused: true` is correctly set** — the regression is in the dedup algorithm's handling of multi-scene timelines, not in the GSAP configuration.

**Confirmed in render log as:**
```
[initSession:screenshot] static-frame dedup: 977/2040 frame(s) reusable (48%, verified) (11918ms)
```
~977/2040 frames (48%) being "reused" = first 57s of frames all look like blank frame 0.

**Frame size fingerprint for this bug:**
- Blank (bug): ~12,460 bytes per frame (uniform dot-grid on near-black)
- Content (working): 40,000–92,000+ bytes per frame (scene content with particles/typography)

**Note on `--no-static-dedup`:** This flag does NOT bypass the bug. The dedup logic still runs and still marks early frames as duplicates. The bug is in how dedup evaluates frames, not in whether it runs.

**Three working approaches (pick one):**

1. **Pre-rendered scene files + ffmpeg concat** — If pre-rendered scene `.mp4` files exist from before 0.7.5, assemble with `ffmpeg concat`. These are from a working version and are valid.

2. **Per-scene isolate + stitch** — Each scene is a standalone HTML with its own `data-duration`. Renders correctly because each isolated timeline is simple. Then concatenate with ffmpeg. See §Per-Scene HTML Workflow below.

3. **Pin to 0.7.3** — `npm install -g hyperframes@0.7.3`. The single-HTML composition approach works in 0.7.3. The 0.7.5 update broke this workflow.

**Confirmed affected:** HyperFrames 0.7.5 on Linux. The standalone 3-scene test (minimal HTML, single `paused: true` timeline) works correctly with 0.7.5 — meaning the core engine is fine, but complex multi-scene compositions trigger the dedup regression.

---

## Validation Checklist for Any HyperFrames Render

Before considering a render "done", always validate:
1. Frame count: `ffprobe -v quiet -show_entries stream=nb_frames -of csv=p=0 output.mp4`
2. Duration: `ffprobe -v quiet -show_entries format=duration -of csv=p=0 output.mp4`
3. Non-blank frames at multiple timestamps (especially early timestamps):
   ```bash
   for t in 0 1 2 4 8 12 16 20 30 40 50 60; do
     ffmpeg -y -i output.mp4 -ss ${t} -vframes 1 -q:v 2 /tmp/frame_t${t}.jpg
     SZ=$(stat -c%s /tmp/frame_t${t}.jpg)
     echo "t=${t}s → ${SZ} bytes"
   done
   ```
   - Real content: >30KB typically
   - Blank/white: ~12KB
4. Frame size consistency: if ALL frames are identical size, that's a red flag
5. Compare against known-good render: `md5sum frame.jpg`

---

## Workflow: Per-Scene Isolate + Stitch (Confirmed Working Workaround)

**IMPORTANT:** Before applying any fixes, check if this bug already exists in your original renders. Extract frames from any pre-existing render of the same composition — if t=0–57 are blank but t=60+ have content, the bug is pre-existing and NOT caused by any CSS or visibility changes you've made.

If `hyperframes render` produces blank frames for early timestamps but correct content later (the `static-dedup` pattern shows high frame reuse), use the per-scene isolate + stitch workaround:

1. **Create isolated per-scene HTML files** — each scene has its own HTML with `data-start="0"` and `data-duration="{scene_duration}"`. GSAP timelines use relative timestamps starting from 0. Only one scene's clip div exists per file. See `references/beginframe-blank-debugging.md` for the full procedure.

2. **Render each scene** from the project root:
   ```bash
   npx hyperframes render . -c scenes/scene1.html -o scene1.mp4
   npx hyperframes render . -c scenes/scene2.html -o scene2.mp4
   # ... etc.
   ```

3. **Verify motion** by checking frame sizes at different timestamps per scene (different sizes = animation working).

4. **Concatenate with ffmpeg** using `concat.txt` — see `references/beginframe-blank-debugging.md`.

For the quick diagnostic test: build a minimal 3-scene composition with NO `visibility` tweens on clips, using `class="clip scene"` with `position:fixed; inset:0` on both classes.
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1080, height=1920" />
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { width: 1080px; height: 1920px; overflow: hidden; background: #0a0a0f; }
    .clip { position: fixed; inset: 0; pointer-events: none; z-index: 1; }
    .scene { position: fixed; inset: 0; display: flex; flex-direction: column;
             align-items: center; justify-content: center; }
  </style>
</head>
<body data-composition-id="main" data-width="1080" data-height="1920"
      data-start="0" data-duration="12">
  <div id="scene1" class="clip scene" data-start="0" data-duration="4" data-track-index="1">
    <h1 style="font-size:88px;font-weight:800;color:#fff;">100+ Skills</h1>
  </div>
  <div id="scene2" class="clip scene" data-start="4" data-duration="4" data-track-index="1" style="opacity:0;">
    <h1 style="font-size:64px;font-weight:800;color:#fff;">Too Many Tools?</h1>
  </div>
  <div id="scene3" class="clip scene" data-start="8" data-duration="4" data-track-index="1" style="opacity:0;">
    <h1 style="font-size:64px;font-weight:800;color:#fff;">The Framework</h1>
  </div>
  <script>
    window.__timelines = window.__timelines || {};
    var tl = gsap.timeline({ paused: true });
    tl.set('#scene1', { opacity: 1 }, 0);
    tl.to('#scene1', { opacity: 0, duration: 0.3 }, 4.0);
    tl.set('#scene2', { opacity: 1 }, 4.0);
    tl.to('#scene2', { opacity: 0, duration: 0.3 }, 8.0);
    tl.set('#scene3', { opacity: 1 }, 8.0);
    tl.to('#scene3', { opacity: 0, duration: 0.5 }, 11.5);
    window.__timelines['main'] = tl;
  </script>
</body>
</html>
```

**Key pattern:** Use `class="clip scene"` with TWO separate CSS classes:
- `.clip { position: fixed; inset: 0; }` — manages viewport coverage only
- `.scene { position: fixed; inset: 0; display: flex; ... }` — manages layout

This separation allows `.scene` to fully stretch to viewport dimensions without conflict from explicit width/height constraints. Works with `--no-clip-visibility` flag.

## The `static-dedup` Diagnostic Pattern

When running a render, check the render log for this pattern:

```
[static-dedup] reused 977/2040 frame(s) (48%), est. ~94769ms saved
```

**What the reuse percentage tells you:**

- High reuse (40–50% on a 68s video): Almost all early frames look like the blank t=0 state. This is the 0.7.5 regression — the dedup algorithm incorrectly marks animated frames as duplicates of frame 0. Only the last 8–10 seconds of content are unique frames.

- Low reuse (e.g. 0–10%): Most frames are genuinely unique — the animation system is working correctly across the full timeline.

- Zero reuse with all frames at ~12KB: The animation system is completely broken (likely `paused: false`, or `window.__timelines` never registered).

**Concrete example (0.7.5 regression):**
- Video: 68s at 30fps = 2040 frames
- Log shows: `reused 977/2040 frames` (48%) for first 57s
- Only 320 frames are unique (t=57–68s)
- Frame size check: t=0–57s = ~12KB (blank dot-grid), t=57–68s = 40–55KB (content)

**IMPORTANT — the `--no-static-dedup` flag does not fix this.** Even when passed, the dedup logic still runs and marks early frames as reusable. The bug is in how dedup evaluates pixel similarity against frame 0, not in whether dedup runs.

## Progressive Isolation Technique (for unknown blank-frame causes)

When a minimal test works but the full composition fails AND you are NOT on 0.7.5 (or you need to identify a different root cause), use this to find the breaking element:

1. Build a **minimal 3-scene test** that mirrors the full composition's patterns (same `.clip` class, same `position:fixed`, same transition flash div pattern, same particle system structure)
2. Verify it renders correctly: `npx hyperframes render --no-clip-visibility --quality draft --output mini.mp4`
3. Extract frames: `for t in 1 3 5 7 9; do ffmpeg -y -i mini.mp4 -ss $t -vframes 1 /tmp/m${t}.jpg; echo "t=${t}s → $(stat -c%s /tmp/m${t}.jpg) bytes"; done`
4. If all timestamps are 30–40KB+: the minimal test works
5. Progressively add ONE element from the full composition to the minimal test, re-rendering each time, until something breaks. Candidate elements to test individually:
   - Transition flash divs (`#tr-flash-1` through `#tr-flash-N`)
   - Dot-grid background (CSS `body::before`)
   - Particle system (the `#particles` div and its JS)
   - More complex scene content (nested divs, emoji characters, Malayalam text)
   - Increased number of scenes (go from 3 → 5 → 7 → 10)
   - CSS `body { width: 1080px; height: 1920px; }` vs `html, body { width: 1080px; height: 1920px; overflow: hidden; }`

**Note:** This technique is for diagnosing unknown blank-frame causes. If you are on HyperFrames 0.7.5+ and the full composition fails while a minimal test works, the issue is almost certainly the 0.7.5 regression described above — not an element in your HTML. Do not spend time progressively isolating. Use the pre-rendered scenes + concat workaround, or pin to 0.7.3.

## The `--no-clip-visibility` Flag: What It Actually Does

**What it does:** Suppresses HyperFrames' automatic injection of `visibility: hidden` on clip elements when their `data-duration` expires. This allows GSAP to fully control opacity without the framework fighting it.

**What it does NOT do:** Fix `paused: false` causing blank frames. The `--no-clip-visibility` flag is unrelated to the `static-dedup` blank-frame bug.

**The actual blank-frame mechanism** (important for debugging):

```
1. Browser opens page → GSAP timeline with paused:false fires ALL animations at wall-clock t=0
2. HyperFrames starts player clock at t=0, seeks to frame 1 (t=0.033s)
3. HyperFrames asks browser: "what does the canvas look like at t=0.033s?"
4. Browser answers: "exactly what GSAP rendered at t=0" (animations already complete)
5. static-dedup sees this frame matches the prior one → marks it "reusable" (duplicate)
6. Repeat for ALL frames until scene exit — every frame looks like t=0 state
7. Result: ~977/2040 frames marked "reusable" in the log, all showing identical blank/white content
```

**The `--no-clip-visibility` flag only matters when:** your composition uses `tl.set('#sceneN', { visibility: 'hidden' })` to hide exited scenes. That pattern fights the framework's lifecycle and causes visual glitches in playback. The flag suppresses the framework's visibility injection so GSAP's opacity tweens work cleanly.

**When to use it:** Composition has native clip lifecycle with `visibility: hidden` kill tweens that you want GSAP to own exclusively.

**When NOT to use it:** As a fix for `paused: false` blank frames — that is a separate bug with a separate cause.

---

## Anti-Patterns That Cause Blank Renders

1. **`paused: false` in the GSAP timeline (THE most common cause of static/uniform frames)** — causes animations to fire immediately on page load in the headless browser, before the HyperFrames player clock starts. All frames render at t=0 state = identical static frames across every timestamp. **Always use `paused: true`.**

   ```js
   // ❌ WRONG — animation fires before player clock
   const tl = gsap.timeline({ defaults: { ease: 'power2.out' } })

   // ✅ CORRECT — waits for HyperFrames player
   const tl = gsap.timeline({ paused: true, defaults: { ease: 'power2.out' } })
   ```

   **Confirmed in hermes-skills-reel session:** Original renders showed all frames at identical small file size (~12KB) because `paused: false` was set. After changing to `paused: true` on all 11 scene timelines, frame sizes varied correctly (43KB–92KB at different timestamps) and motion was confirmed.

2. **`tl.set('#sceneN', { visibility: 'hidden' })` on any element with `class="clip"`** — kills the framework's clip lifecycle
3. **Duplicate `var tl = gsap.timeline({ paused: true })` declarations** — the first (empty) `tl` gets registered with `window.__timelines`, the second (with all animations) never gets registered. Always create ONE timeline and add all animations to it.
4. **Multiple `index*.html` files in project root** — renderer picks up all as entry points, causes `multiple_root_compositions` lint error and duplicate audio playback. Move all scene HTMLs into a `scenes/` subdirectory.
5. **Missing `data-duration` on `<body>`** — HyperFrames can't detect composition length
6. **`opacity:0` on clip elements as initial state** — use `tl.set('#sceneN', { opacity: 1 }, startTime)` inside the timeline instead
7. **`Math.random()` in particle systems** — use seeded PRNG (`mulberry32`) for deterministic output

## Per-Scene HTML Workflow (Confirmed Fix for Multi-Scene Compositions)

When a composition has 10+ scenes and lint shows `missing_timeline_registry`, `multiple_root_compositions`, or frame sizes are all identical (no motion), isolate each scene:

**Directory structure:**
```
project/
├── index.html          # clean shell — body ONLY has data attributes, no content
└── scenes/
    ├── scene1.html     # self-contained, one scene
    ├── scene2.html
    └── ...
```

**index.html — pure container, no GSAP, no content:**
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1080, height=1920" />
</head>
<body
  data-composition-id="main"
  data-width="1080"
  data-height="1920"
  data-start="0"
  data-duration="68"
>
</body>
</html>
```

**Each scene HTML — self-contained with `paused: true`:**
```html
<body
  data-composition-id="scene1"
  data-width="1080"
  data-height="1920"
  data-start="0"
  data-duration="4"
>
  <!-- scene content -->
  <script>
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({ paused: true });
    tl.to('.text', { opacity: 1, y: 0, duration: 0.5 });
    window.__timelines['scene1'] = tl;
  </script>
</body>
```

**Render each scene individually:**
```bash
npx hyperframes render . -c scenes/scene1.html -o scene1.mp4
# Run in parallel for speed:
npx hyperframes render . -c scenes/scene1.html -o scene1.mp4 &
npx hyperframes render . -c scenes/scene2.html -o scene2.mp4 &
# ... etc.
```

**Stitch with ffmpeg concat:**
```
file 'scene1.mp4'
file 'scene2.mp4'
...
```
```bash
ffmpeg -y -f concat -safe 0 -i concat.txt \
  -c:v libx264 -crf 18 -preset fast \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1" \
  -r 30 -movflags +faststart \
  output.mp4
```

**Always verify motion after rendering** — compare frame sizes at different timestamps:
```bash
for t in 1 3 5; do
  ffmpeg -y -i scene.mp4 -ss $t -vframes 1 -q:v 2 /tmp/f${t}.jpg
  echo "t=${t}s → $(stat -c%s /tmp/f${t}.jpg) bytes"
done
# Different sizes = motion present; identical sizes = static (bug)
```

## References

- [hyperframes SKILL.md](../hyperframes/SKILL.md) — creation workflow, setup, lint/validate/inspect/render pipeline
- [hyperframes/composition.md](../hyperframes/references/composition.md) — data attributes, timeline contract, non-negotiable rules
- [hyperframes/troubleshooting.md](../hyperframes/references/troubleshooting.md) — env vars, common render errors, `hyperframes doctor` output interpretation
- **beginframe-blank-debugging.md** — concrete session findings from debugging the hermes-skills-reel beginFrame bug (progressive isolation technique, frame size reference, remaining open questions)
- **hermes-skills-reel-blank-bug-jun22.md** — full session log, render environment, `static-dedup` mechanism explained with exact log fingerprint (977/2040 reused), frame size table, `--no-clip-visibility` mechanism, `PRODUCER_LOW_MEMORY_MODE` context
