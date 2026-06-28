---
name: remotion
description: Remotion — video creation in React. Scaffold, build, render videos with React components.
metadata:
  tags: remotion, video, react, animation, composition
---

## When to use

Use this skill whenever you are dealing with Remotion code.

## Active project this session

**`/root/.hermes/projects/Remotion_ALL/`** — MadeAt2Am "4 Days: Noob to Claude Pro" B-roll package.

**Registered compositions (as of this session):**
| ID | Purpose | Duration |
|---|---|---|
| `ChronixelMotionSystem` | Visual reference still — Chronixel Motion Graphics System design rules | 150f |
| `4DayClaude` | **Full 90s timeline** — all 5 scenes in one comp via `Sequence` | 2700f |
| `4DayClaude-Day1-Scene` | Hook scene only | 151f |
| `4DayClaude-Day1-Scene2` | Day 1 scene only | 1050f |
| `4DayClaude-Day2-Scene3` | Day 2 scene only | 450f |
| `4DayClaude-Day3-Scene4` | Day 3 scene only | 600f |
| `4DayClaude-Day4-Scene5` | Day 4 scene only | 450f |

**Key files:**
- `src/ChronixelMotionSystem.tsx` — visual reference still (6-card glassmorphism layout, dark bg + grid, orange accents, Poppins ExtraBold)
- `src/4DayClaude.tsx` — main composition; exports `FourDayClaude` (consolidated Sequence-based timeline) + individual scene stubs for per-scene Studio scrubbing
- `src/Root.tsx` — registers all compositions

**Important — Composition structure:** One project = one composition with `Sequence` components inside. Do NOT create separate compositions per scene — that bloats the Studio sidebar and makes timeline stitching manual. Use `Sequence from={X} durationInFrames={Y}` to stitch scenes. Keep individual scene stub exports (`Scene1Hook_comp`, etc.) ONLY for per-scene scrubbing in Studio.

## Project location

Remotion projects live wherever you scaffold them. Always `cd /root/<project-name>` before running any Remotion CLI commands.

> ⚠️ **Critical rule:** Before starting a new Remotion project or composition, kill any existing Remotion Studio processes occupying port 3000. Conflicting studios silently serve the wrong project.
> ```bash
> # Find and kill old remotion studio processes
> ps aux | grep "remotion studio" | grep -v grep
> kill <pid>
> ss -tlnp | grep 3000   # verify port is free
> ```

**TypeScript/React imports — critical:** Always import `React` from `"react"`, not from `"remotion"`. Remotion does not re-export the React namespace. The correct pattern:

```tsx
import React from "react";
import { useCurrentFrame, interpolate, Easing, AbsoluteFill } from "remotion";
// NOT: import React from "remotion"     ← WRONG, causes "Namespace has no exported member 'FC'" errors
// NOT: import { React.FC } from "remotion" ← also wrong
```

Use `React.FC<Props>` for typing functional components. Other React types (`React.useEffect`, `React.useState`, etc.) also come from `"react"`.

**Easing:** Use `Easing.bezier()` from `"remotion"` only. Do NOT import from `remotion-motion` — that package is not included by default.

**Composition IDs:** Remotion composition IDs only permit `a-z, A-Z, 0-9, CJK characters, and -`. Underscores (`_`) are forbidden and will throw at registration time. Use hyphens (`-`) as word separators.

**Puppeteer noise on still renders:** The error `Protocol error (Target.closeTarget): No target found for targetId` is a known non-fatal Puppeteer/Remotion race condition on still renders. It does not indicate a render failure — check for the output file (`out/<composition-id>.png`) to confirm success.

## New project setup

When scaffolding a new Remotion project:

```bash
npx create-video@latest --yes --blank --no-tailwind <project-name>
cd /root/<project-name>
npm i
npx remotion skills add   # only needed if the project has a skills setup
npm run dev
```

Then immediately start the studio and give the user the link — **do not scaffold and leave it running without surfacing the URL**.

## Starting Remotion Studio

**⚠️ Every Remotion session: start Studio first and give the user the link immediately.**

**CRITICAL — Always point Studio at the current working project:** Before creating a new project or composition, kill ALL existing Remotion Studio processes. A stale studio on port 3000 silently serves the old project folder — the user sees an empty sidebar with no composition. Today's session proved this: port 3000 served `/root/my-video` while we were working in `/root/claude-code-reel`.

```bash
# 1. Kill ALL existing remotion studio processes
ps aux | grep "remotion studio" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 2

# 2. Verify port 3000 is free
ss -tlnp | grep 3000 || echo "port 3000 is free"

# 3. Now start the new studio pointing at the current project
cd /root/<project-name> && CHROME_BIN=/snap/bin/chromium npx remotion studio --listen
```

**⚠️ The `--listen` flag is required** — without it the studio binds to localhost only and is inaccessible from remote browsers.

Studio runs on port **3000**. After starting, get the host IP and give the user:

```
http://<host-ip>:3000
```

To get the host IP:
```bash
curl -s ifconfig.me
```

If port 3000 is blocked by the cloud firewall, set up an Nginx reverse proxy with HTTPS (see `references/nginx-proxy.md`).

## Key commands

| Command | What it does |
|---|---|
| `cd /root/<project-name> && CHROME_BIN=/snap/bin/chromium npx remotion studio --listen` | Start Remotion Studio (live preview) — always with `--listen` |
| `cd /root/<project-name> && npx remotion still <composition-id> --scale=0.25 --frame=30` | Render single frame (for verification) |
| `cd /root/<project-name> && CHROME_BIN=/snap/bin/chromium npx remotion render <composition-id>` | Render full video |
| `cd /root/<project-name> && npm run build` | Bundle the project |

## Core concepts

- Videos are React components defined in `src/`
- `src/Root.tsx` registers all `<Composition>` entries (width, height, fps, duration)
- Use `useCurrentFrame()` and `interpolate()` for animations
- Prefer `interpolate()` over `spring()` unless physics-based motion is needed
- Use `Easing.bezier()` for custom easing curves
- CSS transitions/animations and Tailwind animation classes are FORBIDDEN — they will not render
- Place assets in `public/` folder, reference with `staticFile()`
- `<Img>` for images, `<Video>` from `@remotion/media` for video, `<Audio>` from `@remotion/media` for audio

## Animation pattern

```tsx
import { useCurrentFrame, interpolate, Easing } from "remotion";

const FadeIn = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return <div style={{ opacity }}>Hello World!</div>;
};
```

## CSS transform pattern (for Remotion Studio editability)

```tsx
style={{
  scale: interpolate(frame, [0, 100], [0, 1]),
  translate: interpolate(frame, [0, 100], ["0px 0px", "100px 100px"]),
  rotate: interpolate(frame, [0, 100], ["20deg", "90deg"]),
}}
```

## Defining compositions

```tsx
// src/Root.tsx
import { Composition } from "remotion";
import { MyComposition } from "./MyComposition";

export const RemotionRoot = () => {
  return (
    <Composition
      id="MyComposition"
      component={MyComposition}
      durationInFrames={100}
      fps={30}
      width={1080}
      height={1080}
    />
  );
};
```

## Sequences

```tsx
import { Sequence, AbsoluteFill } from "remotion";

<AbsoluteFill>
  <Sequence from={1 * fps} durationInFrames={2 * fps} layout="none">
    <Title />
  </Sequence>
</AbsoluteFill>
```

## Adding media

```tsx
import { Img, staticFile } from "remotion";
<Img src={staticFile("logo.png")} style={{ width: 100, height: 100 }} />

import { Video } from "@remotion/media";
<Video src={staticFile("video.mp4")} style={{ opacity: 0.5 }} />

import { Audio } from "@remotion/media";
<Audio src={staticFile("audio.mp3")} />
```

## TailwindCSS

Tailwind v4 is enabled via `@remotion/tailwind-v4`. Import CSS in entry:
```tsx
import "./index.css";
```

## System requirements

- Node 18+ or Bun 1.0+
- Chrome/Chromium (for rendering) — installed at `/snap/bin/chromium`
- FFmpeg — installed at `/usr/bin/ffmpeg`
- GLIBC 2.35+ (Ubuntu 24.04 has 2.39 ✓)

## Chromium path

When rendering videos, set `CHROME_BIN` env var:
```bash
export CHROME_BIN=/snap/bin/chromium
```
Or prefix commands: `CHROME_BIN=/snap/bin/chromium npx remotion render ...`

The Remotion config at `/root/<project-name>/remotion.config.ts` does not set a browser path via Node APIs — the `CHROME_BIN` env var is the mechanism to point Remotion at the Snap Chromium binary.
## Verification before showing the user

**Every time you make code changes, verify before reporting success:**

```bash
cd /root/<project-name> && npx tsc --noEmit
```

Zero TypeScript errors required. If there are errors, fix them before continuing.

Then do a live Remotion bundler check — `tsc` alone is not sufficient, as some errors (duplicate declarations, import misconfigurations) only surface at esbuild bundle time:

```bash
cd /root/<project-name> && CHROME_BIN=/snap/bin/chromium npx remotion still <composition-id> --scale=0.25 --frame=10
```

Confirm the output PNG is valid: `file out/<composition-id>.png`

**⚠️ If Remotion Studio was already running when you made code changes**, it may serve stale bundles. The studio hot-reloads on file save, but if you suspect a stale state restart the studio:

```bash
ps aux | grep "remotion studio" | grep -v grep   # find PID
kill <pid>   # kill stale studio
cd /root/<project-name> && CHROME_BIN=/snap/bin/chromium npx remotion studio --listen  # restart fresh
```

## Common TypeScript pitfalls

These will cause `tsc --noEmit` failures or esbuild bundle failures. Fix them before rendering:

- **Duplicate component declarations** — if you accidentally write the same `const Component = () => {...}` twice (e.g. from a botched patch), TypeScript will report `Cannot redeclare block-scoped variable 'X'`. Find and remove the duplicate. This can slip past `tsc --noEmit` in some module shapes — always verify with `remotion still` as well.
- **Unused variables** — TypeScript treats `const x = ...` where `x` is never read as an error (`TS6133`). Either remove the line or prefix with `_x` if it's intentionally computed but not yet used.
- **Wrong import names** — always check what's actually exported from `remotion` before importing. `useAnimatedStyle` does not exist in the `remotion` package — it belongs to `react-native-reanimated`. If you see `Module '"remotion"' has no exported member 'X'`, remove `X` from your import list.
- **`useVideoConfig` only needed when using `fps`** — if you destructure `fps` from `useVideoConfig()` but never use `fps` in the component, remove the destructure. An unused import of `useVideoConfig` also causes `TS6133`.
- **`spring` and `useAnimatedStyle`** — these are **not** re-exports from `remotion`. Use `interpolate()` for all animation unless you have a specific physics-spring need, in which case use `@remotion/gap` or calculate it manually with `interpolate`.
- **Botched patches leaving the file in a broken state** — when a patch partially applies, it can leave you with two partial definitions of the same component or duplicate imports. Run `tsc --noEmit` AND `remotion still` after every edit cycle. If you see strange errors after what should have been a simple fix, read the file from scratch with `read_file` (not a partial offset read) to see its true current state.

## Rules reference

For specialized topics, load these rules:

| Topic | Rule file |
|---|---|
| Video layout & text sizing | `/root/.hermes/skills/remotion/rules/video-layout.md` |
| Subtitles/captions | `/root/.hermes/skills/remotion/rules/subtitles.md` |
| FFmpeg | `/root/.hermes/skills/remotion/rules/ffmpeg.md` |
| Silence detection | `/root/.hermes/skills/remotion/rules/silence-detection.md` |
| Audio visualization | `/root/.hermes/skills/remotion/rules/audio-visualization.md` |
| Effects | `/root/.hermes/skills/remotion/rules/effects.md` |
| 3D (Three.js) | `/root/.hermes/skills/remotion/rules/3d.md` |
| Google Fonts | `/root/.hermes/skills/remotion/rules/google-fonts.md` |
| Lottie | `/root/.hermes/skills/remotion/rules/lottie.md` |
| TailwindCSS | `/root/.hermes/skills/remotion/rules/tailwind.md` |
| Text animations | `/root/.hermes/skills/remotion/rules/text-animations.md` |
| Timing | `/root/.hermes/skills/remotion/rules/timing.md` |
| Transitions | `/root/.hermes/skills/remotion/rules/transitions.md` |
| Voiceover (ElevenLabs) | `/root/.hermes/skills/remotion/rules/voiceover.md` |
| Parameters/Zod schema | `/root/.hermes/skills/remotion/rules/parameters.md` |
| Measuring DOM nodes | `/root/.hermes/skills/remotion/rules/measuring-dom-nodes.md` |
| Measuring text | `/root/.hermes/skills/remotion/rules/measuring-text.md` |
| GIFs | `/root/.hermes/skills/remotion/rules/gifs.md` |
| Images | `/root/.hermes/skills/remotion/rules/images.md` |
| Videos (advanced) | `/root/.hermes/skills/remotion/rules/videos.md` |
| Audio (advanced) | `/root/.hermes/skills/remotion/rules/audio.md` |
| Compositions (advanced) | `/root/.hermes/skills/remotion/rules/compositions.md` |
| Calculate metadata | `/root/.hermes/skills/remotion/rules/calculate-metadata.md` |
| Transparent videos | `/root/.hermes/skills/remotion/rules/transparent-videos.md` |
| Trimming | `/root/.hermes/skills/remotion/rules/trimming.md` |
| Sequencing | `/root/.hermes/skills/remotion/rules/sequencing.md` |
| Local fonts | `/root/.hermes/skills/remotion/rules/local-fonts.md` |
| HTML in Canvas | `/root/.hermes/skills/remotion/rules/html-in-canvas.md` |
| Light leaks | `/root/.hermes/skills/remotion/rules/light-leaks.md` |
| Maps (MapLibre) | `/root/.hermes/skills/remotion/rules/maplibre.md` |
| Get audio duration | `/root/.hermes/skills/remotion/rules/get-audio-duration.md` |
| Get video dimensions | `/root/.hermes/skills/remotion/rules/get-video-dimensions.md` |
| Get video duration | `/root/.hermes/skills/remotion/rules/get-video-duration.md` |
| Import SRT captions | `/root/.hermes/skills/remotion/rules/import-srt-captions.md` |
| Transcribe captions | `/root/.hermes/skills/remotion/rules/transcribe-captions.md` |
| Display captions | `/root/.hermes/skills/remotion/rules/display-captions.md` |
| SFX | `/root/.hermes/skills/remotion/rules/sfx.md` |
| Claude Code Reel reference | `references/claude-code-reel-composition.md` |
| Chronixel Motion Graphics System | `references/chronixel-motion-system.md` |
