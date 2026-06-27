---
name: hyperframes
description: Create HTML-based video compositions, animated title cards, social overlays, captioned talking-head videos, audio-reactive visuals, and shader transitions using HyperFrames. HTML is the source of truth for video. Use when the user wants a rendered MP4/WebM from an HTML composition, wants to animate text/logos/charts over media, needs captions synced to audio, wants TTS narration, or wants to convert a website into a video.
version: 1.0.0
author: heygen-com
license: Apache-2.0
platforms: [linux, macos, windows]
prerequisites:
  commands: [node, ffmpeg, npx]
metadata:
  hermes:
    tags: [creative, video, animation, html, gsap, motion-graphics]
    related_skills: [manim-video, meme-generation]
    category: creative
    requires_toolsets: [terminal]
---

# HyperFrames

HTML is the source of truth for video. A composition is an HTML file with `data-*` attributes for timing, a GSAP timeline for animation, and CSS for appearance. The HyperFrames engine captures the page frame-by-frame and encodes to MP4/WebM with FFmpeg.

**Complement to `manim-video`:** Use `manim-video` for mathematical/geometric explainers (equations, 3B1B-style). Use `hyperframes` for motion-graphics, talking-head with captions, product tours, social overlays, shader transitions, and anything driven by real video/audio media.

## Hard Rules Before Writing Any Code

### `paused: true` is Mandatory — Not Optional

Every GSAP timeline in every HyperFrames composition **must** use `paused: true`. This is not a style preference or soft guideline.

**Why it matters:** `paused: false` causes animations to fire immediately at wall-clock t=0 when the headless browser opens the page. The HyperFrames player clock starts a moment later. By the time HyperFrames requests frame 1 (t=0.033s), all animations have already completed. Every extracted frame looks identical — static blank/white content, no motion. The `static-dedup` feature then marks these as "reusable duplicates," compounding the damage.

**Confirmed in session (June 2026):** Original Hermes Skills Reel renders showed all frames at ~12KB (blank) because all 11 scene timelines used `paused: false`. After switching to `paused: true`, frame sizes varied correctly (43KB–92KB at different timestamps) and motion was confirmed. The player controls playback — GSAP must wait.

```js
// ✅ CORRECT
const tl = gsap.timeline({ paused: true });

// ❌ WRONG — every frame renders at t=0 state
const tl = gsap.timeline({ paused: false });
```

This applies to **every timeline in every composition**, including per-scene isolated HTMLs rendered via `hyperframes render -c scenes/sceneN.html`.

---

## When to Use

- User asks for a rendered video from text, a script, or a website
- Animated title cards, lower thirds, or typographic intros
- Captioned narration video (TTS + captions synced to waveform)
- Audio-reactive visuals (beat sync, spectrum bars, pulsing glow)
- Scene-to-scene transitions (crossfade, wipe, shader warp, flash-through-white)
- Social overlays (Instagram/TikTok/YouTube style)
- Website-to-video pipeline (capture a URL, produce a promo)
- Any HTML/CSS/JS animation that must render deterministically to a video file

Do **not** use this skill for:
- Pure math/equation animation (→ `manim-video`)
- Image generation or memes (→ `meme-generation`, image models)
- Live video conferencing or streaming

## Quick Reference

```bash
npx hyperframes init my-video               # scaffold a project
cd my-video
npx hyperframes lint                        # validate before preview/render
npx hyperframes preview                     # live-reload browser preview (port 3002)
npx hyperframes render --output final.mp4   # render to MP4
npx hyperframes doctor                      # diagnose environment issues
```

Render flags: `--quality draft|standard|high` · `--fps 24|30|60` · `--format mp4|webm` · `--docker` (reproducible) · `--strict`.

Full CLI reference: [references/cli.md](references/cli.md).

## Setup (one-time)

```bash
bash "$(dirname "$(find ~/.hermes/skills -path '*/hyperframes/SKILL.md' 2>/dev/null | head -1)")/scripts/setup.sh"
```

> **CLI not found after install?** If `hyperframes: command not found` but npm reported success, Hermes may be using a custom npm prefix. Check with:
> ```bash
> npm config get prefix   # usually /root/.hermes/node
> ls "$(npm config get prefix)/bin/hyperframes"   # verify it exists
> ```
> Run via full path: `/root/.hermes/node/bin/hyperframes doctor`, or add `PATH="/root/.hermes/node/bin:$PATH"` to your shell profile.

> **Installing from a GitHub URL:** Pass the **raw** URL (`raw.githubusercontent.com`), NOT the blob/UI URL (`github.com/.../blob/main/...`). Blob URLs time out on large files. For skills with `references/` subdirectories, download them manually after the SKILL.md installs: `curl -sL raw.githubusercontent.com/<user>/<repo>/main/<path> -o ~/.hermes/skills/<category>/<skill>/<path>`.

The script:
1. Verifies Node.js >= 22 and FFmpeg are installed (prints fix instructions if not).
2. Installs the `hyperframes` CLI globally (`npm install -g hyperframes@>=0.4.2`).
3. Pre-caches `chrome-headless-shell` via Puppeteer — **required** for best-quality rendering via Chrome's `HeadlessExperimental.beginFrame` capture path.
4. Runs `npx hyperframes doctor` and reports the result.

See [references/troubleshooting.md](references/troubleshooting.md) if setup fails.

## Procedure

### 1. Plan before writing HTML

Before touching code, articulate at a high level:
- **What** — narrative arc, key moments, emotional beats
- **Structure** — compositions, tracks (video/audio/overlays), durations
- **Visual identity** — colors, fonts, motion character (explosive / cinematic / fluid / technical)
- **Hero frame** — for each scene, the moment when the most elements are simultaneously visible. This is the static layout you'll build first.

**Visual Identity Gate (HARD-GATE).** Before writing ANY composition HTML, a visual identity must be defined. Do NOT write compositions with default or generic colors (`#333`, `#3b82f6`, `Roboto` are tells that this step was skipped). Check in order:

1. **`DESIGN.md` at project root?** → Use its exact colors, fonts, motion rules, and "What NOT to Do" constraints.
2. **User named a style** (e.g. "Swiss Pulse", "dark and techy", "luxury brand")? → Generate a minimal `DESIGN.md` with `## Style Prompt`, `## Colors` (3-5 hex with roles), `## Typography` (1-2 families), `## What NOT to Do` (3-5 anti-patterns).
3. **None of the above?** → Ask 3 questions before writing any HTML:
   - Mood? (explosive / cinematic / fluid / technical / chaotic / warm)
   - Light or dark canvas?
   - Any brand colors, fonts, or visual references?

   Then generate a `DESIGN.md` from the answers. Every composition must trace its palette and typography back to `DESIGN.md` or explicit user direction.

### 2. Scaffold

```bash
npx hyperframes init my-video --non-interactive
```

Templates: `blank`, `warm-grain`, `play-mode`, `swiss-grid`, `vignelli`, `decision-tree`, `kinetic-type`, `product-promo`, `nyt-graph`. Pass `--example <name>` to pick one, `--video clip.mp4` or `--audio track.mp3` to seed with media.

### 3. Layout before animation

Write the static HTML+CSS for the **hero frame first** — no GSAP yet. The `.scene-content` container must fill the scene (`width:100%; height:100%; padding:Npx`) with `display:flex` + `gap`. Use padding to push content inward — never `position: absolute; top: Npx` on a content container (content overflows when taller than the remaining space).

Only after the hero frame looks right, add `gsap.from()` entrances (animate **to** the CSS position) and `gsap.to()` exits (animate **from** it).

See [references/composition.md](references/composition.md) for the full data-attribute schema and composition rules.

### 4. Animate with GSAP

Every composition must:
- Register its timeline: `window.__timelines["<composition-id>"] = tl`
- Start paused: `gsap.timeline({ paused: true })` — the player controls playback
- Use finite `repeat` values (no `repeat: -1` — breaks the capture engine). Calculate: `repeat: Math.ceil(duration / cycleDuration) - 1`
- Be deterministic — no `Math.random()`, `Date.now()`, or wall-clock logic. Use a seeded PRNG if you need pseudo-randomness.
- Build synchronously — no `async`/`await`, `setTimeout`, or Promises around timeline construction.

**GSAP stagger — use the positional parameter, NOT the `stagger` key inside vars.**

Correct:
```js
// Stagger as 4th positional argument (stagger in ms between each element)
root.from('.agent-node', { opacity: 0, y: -200, scale: 0, duration: 0.5, ease: 'power3.out' }, 30.6, 0.04);

// Stagger with 'random' from — still positional
root.from('.team-node', { opacity: 0, scale: 0, duration: 0.4, ease: 'back.out(1.7)' }, 38.8, 0.025);
```

Wrong (causes `Cannot create property 'runBackwards' on number` at validate time):
```js
root.from('.agent-node',
  { opacity: 0, y: -200, duration: 0.5, stagger: { each: 0.04, from: 'random' } },  // ❌ stagger inside vars
  30.6
);
```

The `stagger` key inside the `vars` object conflicts with GSAP's stagger parser when passed as a positional argument. Always pass stagger as the 4th positional argument. This means: `target, vars, position, stagger`.

See [references/gsap.md](references/gsap.md) for the core GSAP API (tweens, eases, stagger, timelines).

### 5. Transitions between scenes

Multi-scene compositions require transitions. Rules:
1. **Always use a transition between scenes** — no jump cuts.
2. **Always use entrance animations** on every scene element (`gsap.from(...)`).
3. **Never use exit animations** except on the final scene — the transition IS the exit.
4. The final scene may fade out.

Use `npx hyperframes add <transition-name>` to install shader transitions (`flash-through-white`, `liquid-wipe`, etc.). Full list: `npx hyperframes add --list`.

### 6. Audio, captions, TTS, audio-reactive, highlighting

- **Audio:** always a separate `<audio>` element (video is `muted playsinline`).
- **TTS:** `npx hyperframes tts "Script text" --voice af_nova --output narration.wav`. List voices with `--list`. Voice ID first letter encodes language (`a`/`b`=English, `e`=Spanish, `f`=French, `j`=Japanese, `z`=Mandarin, etc.) — the CLI auto-infers the phonemizer locale; pass `--lang` only to override. Non-English phonemization requires `espeak-ng` installed system-wide.
- **Captions:** `npx hyperframes transcribe narration.wav` → word-level transcript. Pick style from the transcript tone (hype / corporate / tutorial / storytelling / social — see the table in `references/features.md`). **Language rule:** never use `.en` whisper models unless the audio is confirmed English — `.en` translates non-English audio instead of transcribing it. Every caption group MUST have a hard `tl.set(el, { opacity: 0, visibility: "hidden" }, group.end)` kill after its exit tween — otherwise groups leak visible into later ones.
- **Audio-reactive visuals:** pre-extract audio bands (bass / mid / treble) and sample per-frame inside the timeline with a `for` loop of `tl.call(draw, [], f / fps)` — a single long tween does NOT react to audio. Map bass → `scale` (pulse), treble → `textShadow`/`boxShadow` (glow), overall amplitude → `opacity`/`y`/`backgroundColor`. Avoid equalizer-bar clichés — let content guide the visual, audio drive its behavior.
- **Marker-style highlighting:** highlight, circle, burst, scribble, sketchout effects for text emphasis are deterministic CSS+GSAP — see `references/features.md#marker-highlighting`. Fully seekable, no animated SVG filters.
- **Scene transitions:** every multi-scene composition MUST use transitions (no jump cuts). Pick from CSS primitives (push slide, blur crossfade, zoom through, staggered blocks) or shader transitions (`flash-through-white`, `liquid-wipe`, `cross-warp-morph`, `chromatic-split`, etc.) via `npx hyperframes add`. Mood and energy tables live in `references/features.md#transitions`. Do not mix CSS and shader transitions in the same composition.

### 7. Lint, validate, inspect, preview, render

```bash
npx hyperframes lint              # catches missing data-composition-id, overlapping tracks, unregistered timelines
npx hyperframes validate          # WCAG contrast audit at 5 timestamps
npx hyperframes inspect           # visual layout audit — overflow, off-frame elements, occluded text
npx hyperframes preview           # live browser preview
npx hyperframes render --quality draft --output draft.mp4    # fast iteration
npx hyperframes render --quality high --output final.mp4     # final delivery
```

`hyperframes validate` samples background pixels behind every text element and warns on contrast ratios below 4.5:1 (or 3:1 for large text). `hyperframes inspect` is the layout-side companion — runs the page at multiple timestamps and flags issues that a static lint can't see (a caption that wraps past the safe area only at 4.5s, a card that overflows when its title is the longest variant, an element that ends up behind a transition shader). Run `inspect` especially on compositions with speech bubbles, cards, captions, or tight typography.

### 8. Delivery — getting the MP4 to the user

`hyperframes publish` uploads to the HeyGen cloud and returns a studio link — it does NOT produce a direct MP4 download URL. For the actual video file, always use the local render output:

```bash
npx hyperframes render --quality high --output final.mp4
```

The MP4 is at `$(pwd)/final.mp4` (or wherever `--output` pointed). To get it to the user:
1. **Local network / SCP** — if the user has SSH/SFTP access to the host, `scp user@host:/path/to/final.mp4 .` is the cleanest.
2. **Python static server** — `python3 -m http.server 8787 --directory /path/to/project/` (run in background with `background=true`). Give the user `http://<host>:8787/final.mp4`. Note: this port must be externally reachable.
3. **Telegram** — if Hermes is wired to a Telegram bot, use `send_message` to push the file to the user's Telegram chat_id.
4. **Cloud storage / transfer service** — as a last resort. `transfer.sh` was blocked in this environment.
   - **Catbox.moe (confirmed working):** `curl -F "reqtype=fileupload" -F "fileToUpload=@final.mp4" https://catbox.moe/user/api.php` — returns a direct download URL like `https://files.catbox.moe/qk52r3.mp4`. Fast, no account needed, works reliably for files up to 200MB.
   - WeTransfer: `curl --upload-file ./final.mp4 https://transfer.sh/final.mp4`
   - tmpfiles.org: browser upload at https://tmpfiles.org/

Do NOT promise the user a direct URL from `hyperframes publish` — that link is for studio editing, not file delivery.

### 9. Website-to-video (if the user gives a URL)

Use the 7-step capture-to-video workflow in [references/website-to-video.md](references/website-to-video.md): capture → DESIGN.md → SCRIPT.md → storyboard → composition → render → deliver.
## Pitfalls

- **`HeadlessExperimental.beginFrame' wasn't found`** — Chromium 147+ removed this protocol. Ensure you're on `hyperframes@>=0.4.2` (auto-detects and falls back to screenshot mode). Escape hatch: `export PRODUCER_FORCE_SCREENSHOT=true`. See [hyperframes#294](https://github.com/heygen-com/hyperframes/issues/294) and [references/troubleshooting.md](references/troubleshooting.md).
- **`position: absolute` clips + `data-composition-id` on `<body>` → blank renders in beginFrame capture.** If clip elements use `position: absolute` and the composition renders only the last scene while early scenes are blank (even after removing all `visibility` tweens), try switching clips to `position: fixed`. This was observed empirically: `position: fixed` clips with `--no-clip-visibility` work correctly while `position: absolute` clips with the same flags do not. Hypothesis: `position: absolute` clips are affected by body overflow/clipping rules that interfere with the headless browser's frame capture at early timeline positions.
  ```css
  /* Use this for clips */
  .clip { position: fixed; top: 0; left: 0; width: 1080px; height: 1920px; }
  /* Not this */
  .clip { position: absolute; top: 0; left: 0; width: 1080px; height: 1920px; }
  ```
  — the jsDelivr npm package path for `@fontsource` fonts is `https://cdn.jsdelivr.net/npm/@fontsource/<package>@<version>/files/<file>` — NOT the bare npm CDN (`https://cdn.jsdelivr.net/npm/@fontsource/<package>@<version>` alone). **Version-specific files go stale** — jsDelivr pins exact file paths per version, so a version like `@5.0.18` may have a file that was later moved or removed in `@5.1.0`. If a font URL returns 404, bump the patch version (e.g. `@5.0.18` → `@5.1.0`). Always verify with `curl -sI <url>` before shipping.
  ```css
  @font-face {
    font-family: 'Space Grotesk';
    src: url('https://cdn.jsdelivr.net/npm/@fontsource/space-grotesk@5.1.0/files/space-grotesk-latin-800-normal.woff2') format('woff2');
    font-weight: 800;
  }
  ```
  GitHub-hosted font repos (e.g. `cdn.jsdelivr/gh/...`) are unreliable — prefer `@fontsource` via jsDelivr npm.
- **`data-composition-id` on a `#stage` child div (not `<body>`) — correct pattern for complex/multi-scene compositions.** For 9:16 portrait or multi-scene compositions, the blueprint linter's check for root attributes targets `<body>` directly — but `<body>` can hold only `data-composition-id` (to name the composition) while the actual composition metadata (`data-width`, `data-height`, `data-start`, `data-duration`) lives on a `#stage` child div. This avoids the linter incorrectly flagging `root_missing_dimensions` when the body has no width/height of its own. Pattern:
  ```html
  <body data-composition-id="main">
    <div id="stage"
         data-composition-id="main"
         data-width="1080"
         data-height="1920"
         data-start="0"
         data-duration="27">
      <!-- scenes go here -->
    </div>
  </body>
  ```
  The render succeeds with this pattern even when lint reports `root_missing_composition_id` or `root_missing_dimensions` — those are false positives from the blueprint linter not finding attributes it expected on `<body>` directly.
- **`gsap_animates_clip_element` for scene exit — use inner content div, not the clip.** The lint error `GSAP animation sets visibility on a clip element` fires when you try to fade out the final scene. The fix: wrap scene content in an inner div (`#sceneN-content`) and animate that for opacity fades. Apply `tl.set('#sceneN', { visibility: 'hidden' }, endTime)` for the hard kill on the clip itself. Pattern:
  ```html
  <div id="scene6" class="scene clip" data-start="21" data-duration="6" data-track-index="6">
    <div id="scene6-content">
      <!-- CTA content -->
    </div>
  </div>
  ```
  ```js
  root.to('#scene6-content', { opacity: 0, duration: 1.2, ease: 'power2.in' }, 25.8);
  root.set('#scene6', { visibility: 'hidden' }, 27.0); // hard kill on clip
  ```
- **`hyperframes lint` exits code 0 even with errors — use `--strict` to make them fatal.** The lint command reports `✗` errors but still exits 0, allowing the pipeline to continue. `hyperframes render` also continues past lint issues by default. To block on errors: `npx hyperframes lint --strict`. For render: `--strict` flag blocks the render. Without `--strict`, a successful render is possible even when lint reports errors (the errors are often false positives from the blueprint checker).
- **GSAP stagger inside `vars` object** — see the stagger rule in §4. Passing `stagger` as a key inside the `vars` object while also using a positional stagger argument causes `Cannot create property 'runBackwards' on number` at validate time. Always use the 4th positional argument for stagger.
- **`paused: false` on a multi-scene composition causes ALL scenes to render as static images.** If your GSAP timeline uses `paused: false` (animations start immediately on page load), the headless browser renders only the first few frames and then freezes — every frame extracted becomes identical. Always use `paused: true` and let the HyperFrames player control playback. This is especially critical when using the per-scene isolate workaround: each isolated scene HTML must have `paused: true` because the player starts each scene's timeline from t=0.
- **HyperFrames 0.7.5 regression breaks multi-scene single-HTML compositions.** Version 0.7.5 introduced a `static-frame dedup` regression where animated frames in scenes 1–9 are incorrectly marked as duplicates of frame 0. The render produces a video where only the last scene has content — all earlier scenes show a static blank background. The `--no-static-dedup` flag does NOT bypass this. Workarounds: (1) use pre-rendered scene files + ffmpeg concat if available; (2) use per-scene isolate + stitch; (3) pin to `hyperframes@0.7.3` with `npm install -g hyperframes@0.7.3`. A standalone minimal scene (single scene, short timeline) renders correctly with 0.7.5 — only complex multi-scene compositions are affected.
- **System Chrome (not `chrome-headless-shell`)** — renders hang for 120s then timeout. Run `npx puppeteer browsers install chrome-headless-shell` (setup.sh does this). `hyperframes doctor` reports which binary will be used.
- **`repeat: -1` anywhere** — breaks the capture engine. Always compute a finite repeat count.
- **`gsap.set()` on clip elements that enter later** — the element doesn't exist at page load. Use `tl.set(selector, vars, timePosition)` inside the timeline instead, at or after the clip's `data-start`.
- **`<br>` inside content text** — forced breaks don't know the rendered font width, so natural wrap + `<br>` double-breaks. Use `max-width` to let text wrap. Exception: short display titles where each word is deliberately on its own line.
- **Animating `visibility` or `display` on clip elements** — GSAP can't tween these on clip elements. Use `autoAlpha` on inner content divs instead.
- **Calling `video.play()` or `audio.play()`** — the framework owns playback. Never call these yourself.
- **Building timelines async** — the capture engine reads `window.__timelines` synchronously after page load. Never wrap timeline construction in `async`, `setTimeout`, or a Promise.
- **Standalone `index.html` wrapped in `<template>`** — hides all content from the browser. Only **sub-compositions** loaded via `data-composition-src` use `<template>`.
- **Using video for audio** — always muted `<video>` + separate `<audio>`.

## Verification

Before and after rendering:

1. **Lint + validate + inspect pass:** `npx hyperframes lint --strict && npx hyperframes validate && npx hyperframes inspect` (lint catches structural issues, validate catches contrast, inspect catches visual layout / overflow issues — see troubleshooting.md if warnings appear).
2. **Animation choreography** — for new compositions or significant animation changes, run the animation map. `npx hyperframes init` copies the skill scripts into the project, so the path is project-local:
   ```bash
   node skills/hyperframes/scripts/animation-map.mjs <composition-dir> \
     --out <composition-dir>/.hyperframes/anim-map
   ```
   Outputs a single `animation-map.json` with per-tween summaries, ASCII Gantt timeline, stagger detection, dead zones (>1s with no animation), element lifecycles, and flags (`offscreen`, `collision`, `invisible`, `paced-fast` <0.2s, `paced-slow` >2s). Scan summaries and flags — fix or justify each. Skip on small edits.
3. **File exists + non-zero:** `ls -lh final.mp4`.
4. **Duration matches `data-duration`:** `ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 final.mp4`.
5. **Visual check:** extract a mid-composition frame: `ffmpeg -i final.mp4 -ss 00:00:05 -vframes 1 preview.png`.
6. **Audio present if expected:** `ffprobe -v error -show_streams -select_streams a -of default=nw=1:nk=1 final.mp4 | head -1`.

If `hyperframes render` fails, run `npx hyperframes doctor` and attach its output when reporting.

## References

- [composition.md](references/composition.md) — data attributes, timeline contract, non-negotiable rules, typography/asset rules
- [cli.md](references/cli.md) — every CLI command (init, capture, lint, validate, inspect, preview, render, transcribe, tts, doctor, browser, info, upgrade, benchmark)
- [gsap.md](references/gsap.md) — GSAP core API for HyperFrames (tweens, eases, stagger, timelines, matchMedia)
- [motion-patterns.md](references/motion-patterns.md) — proven animation patterns: typewriter, cascading cards, flash transitions, elastic scale, spotlight sweep, progress bar, satellite node growth
- [features.md](references/features.md) — captions, TTS, audio-reactive, marker highlighting, transitions (load on demand)
- [website-to-video.md](references/website-to-video.md) — 7-step capture-to-video workflow
- [viral-promo-plan.md](references/viral-promo-plan.md) — 7-scene structure for short-form promo videos (YouTube Shorts, TikTok, Reels) — use when the user gives a script and wants a full video produced
- [troubleshooting.md](references/troubleshooting.md) — OpenClaw fix, env vars, common render errors
