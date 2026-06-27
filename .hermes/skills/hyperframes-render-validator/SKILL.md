---
name: hyperframes-render-validator
description: Hyperframes video render protocol with mandatory screenshot validation before delivery. Prevents sending broken/misaligned videos.
category: creative
---

# Hyperframes Render + Validation Protocol

## When to Use
Every time you create a Hyperframes video — no exceptions. The render may complete without errors but produce blank/misaligned output. Screenshot validation is mandatory before delivery.

## Required Setup

### 1. Register GSAP Timelines (CRITICAL — `paused: true` IS NON-NEGOTIABLE)
Hyperframes drives animations by seeking the browser to each frame's timestamp and capturing. If `paused: false`, GSAP fires ALL animations on page load (wall-clock t=0), before HyperFrames' player clock exists. HyperFrames then sees every frame as identical to the t=0 state and marks them "reusable" — producing a static duplicate video. **Always use `paused: true`.**

```html
<script>
  window.__timelines = window.__timelines || {};
  window.__timelines['main'] = gsap.timeline({ paused: true });  <!-- paused: true ALWAYS -->
  const tl = window.__timelines['main'];
  // ... your animations using `tl` ...
</script>
```

The key `main` must match the `data-composition-id` on the `<body>` tag.

### 2. Self-Contained Per-Scene Isolation (Required for 6+ Scene Videos)
For complex multi-scene videos, render each scene as an isolated HTML file in a `scenes/` subdirectory:
- Its own `data-duration` set to ONLY its length (not total video duration)
- `paused: true` on the GSAP timeline
- All animations keyed to timestamps starting from 0 in the scene's local timeline
- A clean `index.html` shell in the project root (body only, no content)

This avoids two failure modes: (1) `paused: false` blank frames (animations fire before player clock), and (2) beginFrame seek failures in complex multi-scene timelines where the browser renders blank at early timestamps.

**Directory structure:**
```
project/
├── index.html          # clean shell — body ONLY has data attributes, no content
└── scenes/
    ├── scene1.html     # self-contained, one scene, paused:true
    ├── scene2.html
    └── ...
```

**index.html — pure container:**
```html
<body data-composition-id="main" data-width="1080" data-height="1920"
      data-start="0" data-duration="68">
</body>
```

**Each scene HTML — self-contained with `paused: true`:**
```html
<body data-composition-id="scene1" data-width="1080" data-height="1920"
      data-start="0" data-duration="4">
  <!-- scene content -->
  <script>
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({ paused: true });
    tl.to('.text', { opacity: 1, y: 0, duration: 0.5 });
    window.__timelines['scene1'] = tl;
  </script>
</body>
```

### 3. Composition Data Attributes
Put all `data-*` attributes on the `<body>`:
```html
<body
  data-composition-id="main"
  data-width="1080"
  data-height="1920"
  data-start="0"
  data-duration="3"
>
```

## Per-Scene Render Command
```bash
# Set up project dir with scene HTML as index.html
mkdir -p /root/PROJECT/projs/s{N}
cp /root/PROJECT/scenes/scene{N}.html /root/PROJECT/projs/s{N}/index.html

# Render
cd /root/PROJECT/projs/s{N}
npx hyperframes render . --quality high --output /root/PROJECT/renders/scene{N}.mp4
```

## Validation Step (MANDATORY — after every render)

### Extract verification frames
```bash
VERIFYDIR="/root/PROJECT/verify"
mkdir -p "$VERIFYDIR"

# For short scenes (3-6s): extract at 0.5s, 1.5s, peak timestamp
for ts in 0.5 1.5 2.5; do
  ffmpeg -ss "$ts" -i /root/PROJECT/renders/scene{N}.mp4 \
    -vframes 1 -q:v 2 "$VERIFYDIR/s{N}_${ts}s.jpg" -y 2>/dev/null
done

# For long scenes (9s): extract at multiple animation entry/exit points
for ts in 1.0 3.5 7.0 9.0; do
  ffmpeg -ss "$ts" -i /root/PROJECT/renders/scene{N}.mp4 \
    -vframes 1 -q:v 2 "$VERIFYDIR/s{N}_${ts}s.jpg" -y 2>/dev/null
done

# Check frame sizes — they should be non-zero and increasing as animations accumulate
ls -lh "$VERIFYDIR/"
```

### Visual inspection (use vision_analyze tool)
- Load each extracted frame with vision_analyze
- Ask specific questions about visible text and elements
- If any scene looks blank/wrong: diagnose and re-render THAT SCENE only

### Success criteria
- All frames non-zero size (>20KB typically)
- Visual content matches scene description
- No blank/misaligned scenes

## Stitching (ffmpeg concat)

### Create concat list
```bash
cat > /tmp/concat_list.txt << 'EOF'
file '/root/PROJECT/renders/scene1.mp4'
file '/root/PROJECT/renders/scene2.mp4'
file '/root/PROJECT/renders/scene3.mp4'
file '/root/PROJECT/renders/scene4.mp4'
file '/root/PROJECT/renders/scene5.mp4'
file '/root/PROJECT/renders/scene6.mp4'
EOF
```

### Encode
```bash
ffmpeg -f concat -safe 0 -i /tmp/concat_list.txt \
  -c:v libx264 -crf 17 -preset medium \
  -r 30 -pix_fmt yuv420p \
  /root/PROJECT/final.mp4
```

### Verify stitched output
```bash
# Check specs
ffprobe -v quiet -show_entries stream=width,height,duration,r_frame_rate \
  -of csv=p=0 /root/PROJECT/final.mp4

# Extract frames from PROBLEM SCENES in the final video (timestamps = cumulative)
# Scene 2 starts at t=3s, Scene 3 at t=6s, Scene 4 at t=15s, etc.
for ts in 4 8 16; do
  ffmpeg -ss "$ts" -i /root/PROJECT/final.mp4 \
    -vframes 1 -q:v 2 "/tmp/final_ts${ts}.jpg" -y 2>/dev/null
done
# vision_analyze each frame to confirm
```

## Delivery

### Catbox upload
```bash
curl -s -F "reqtype=fileupload" \
  -F "fileToUpload=@/root/PROJECT/final.mp4" \
  https://catbox.moe/user/api.php
```

### Telegram (Chris's home channel)
```bash
hermes send -t telegram "STATUS REPORT

Scene 1: [description]
Scene 2: [description]
...

Format: WxH, fps, duration
Download: https://files.catbox.moe/XXXXX.mp4"
```

## Version Regression: 0.7.5 Breaks Multi-Scene Single-HTML Compositions

**Critical:** HyperFrames 0.7.5 (released June 2026) introduced a regression that breaks multi-scene single-HTML compositions. The `static-frame dedup` marks animated frames for scenes 1–9 as duplicates of frame 0, producing a video where only the final scene (last ~8s) has content. The bug occurs **even when `paused: true` is correctly set**.

**Symptoms in render log:**
```
[initSession:screenshot] static-frame dedup: 977/2040 frame(s) reusable (48%, verified) (11918ms)
```
~977/2040 frames (48%) being "reused" means early scenes all look like the blank frame 0 state.

**Confirmed working workarounds (in priority order):**

1. **Pre-rendered scene files + ffmpeg concat** — If you have pre-rendered scene `.mp4` files from before the 0.7.5 update, assemble them with `ffmpeg concat`. These were rendered with a working version and remain valid.

2. **Per-scene isolate + stitch** — Render each scene as a standalone HTML file (see §Per-Scene Render Command above), then concatenate. Each scene's isolated render avoids the multi-scene timeline seek bug in 0.7.5.

**Version-pinning (preventative):** If you need the full single-HTML composition approach to work, pin to 0.7.3:
```bash
npm install -g hyperframes@0.7.3
```

**Note on `--no-static-dedup`:** This CLI flag exists but does NOT bypass the 0.7.5 dedup bug. The feature still runs and still marks early frames as reusable. The bug is in how the dedup logic evaluates frames, not in whether it runs.

## Common Failure Modes

| Problem | Cause | Fix |
|---------|-------|-----|
| Animations not playing in render | Missing `window.__timelines` registration | Add the registry setup before GSAP timeline |
| All frames identical / blank (static video) | `paused: false` — animations fire on page load, HyperFrames sees all frames as t=0 state | Change to `paused: true`; use per-scene isolation |
| Scenes 1–9 blank, only last scene has content | **HyperFrames 0.7.5 regression** — `static-frame dedup` misidentifies animated frames as duplicates | Use pre-rendered scenes + concat, or per-scene isolate + stitch, or pin to 0.7.3 |
| Scenes 2/3/4 invisible | Single-timeline approach breaks HyperFrames scene scoping | Split into per-scene HTML files, one per scene |
| Font not loading | `@import` in headless Chrome fails | Use `@fontsource` via jsDelivr CDN with `@font-face` |
| Blank scene in render | `data-duration` too short | Set to actual scene length, not total video length |

## File Locations
- Scene HTMLs: `/root/PROJECT/scenes/`
- Per-scene renders: `/root/PROJECT/renders/`
- Verification frames: `/root/PROJECT/verify/`
- Final stitched video: `/root/PROJECT/final.mp4`
