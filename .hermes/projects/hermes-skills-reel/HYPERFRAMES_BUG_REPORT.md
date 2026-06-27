# [BUG] beginFrame capture returns blank/white frames for multi-scene compositions

## Bug Description

`hyperframes render` (which uses beginFrame capture mode) renders multi-scene compositions incorrectly when there are 10+ scenes with clip-level GSAP animations. Frames at timestamps corresponding to scenes 1-9 all render as identical blank/white 1080x1920 JPEG frames (~12KB), while the final scene renders correctly (~48KB).

This appears to be a beginFrame-specific issue — the underlying HTML/JS/animation plays correctly when viewed in a browser.

## Steps to Reproduce

1. Clone/create a multi-scene HyperFrames composition with 10+ scenes using clip-level GSAP timelines with `position: fixed` clips, `data-start`/`data-duration` attributes, and opacity-based transitions
2. Run `npx hyperframes render --quality draft --output output.mp4`
3. Extract frames at various timestamps using `ffmpeg -i output.mp4 -ss T -vframes 1 frame.jpg`
4. Observe that timestamps 0–57s show identical ~12KB blank frames, while t=60s+ shows correct content

## Environment

- OS: Linux (6.8.0-117-generic)
- HyperFrames version: 0.6.119
- Node.js: via npx
- Chrome: via Puppeteer (beginFrame capture)

## Root Cause Hypothesis

The beginFrame implementation seeks to each timestamp and re-renders from the GSAP timeline state at that time. For compositions with many overlapping clips and complex GSAP timelines, the seek logic appears to malfunction — consistently seeking to the wrong temporal state for timestamps before the final scene, but correctly rendering the final scene.

The static-frame deduplication in beginFrame (`static-dedup: reused X/2040 frame(s)`) marks early frames as duplicates of later ones, suggesting the seek lands on the wrong timeline position.

## Workaround

Render each scene as an isolated HTML file (single clip, no overlapping timelines), then concatenate with `ffmpeg -f concat -i concat.txt -c copy output.mp4`. This bypasses the seek issue entirely.

## Reproduction Assets

### Working Minimal Test (3 scenes — renders correctly)
File: `/root/.hermes/projects/hf-mini-test/index.html`

This mini test has:
- 3 clips with `class="clip scene"`
- `position: fixed; inset: 0;` on `.scene`
- `data-start`/`data-duration` on each clip
- GSAP timeline with opacity transitions
- Renders correctly at ALL timestamps

### Failing Full Composition (10 scenes — first 9 scenes blank in beginFrame)
File: `/root/.hermes/projects/hermes-skills-reel/index.html`

This composition has:
- 11 clips (10 scenes + final frame) with `class="clip scene"`
- `position: fixed; inset: 0;` on `.clip`
- `data-start`/`data-duration` on each clip
- GSAP timeline with opacity + position transitions
- **BUG**: Frames t=0–57s are identical blank ~12KB; only t=60+ renders correctly

## Comparison of Working vs Failing

| Aspect | Mini Test (Working) | Full Composition (Broken) |
|--------|---------------------|---------------------------|
| Scene count | 3 | 11 |
| Clips | `class="clip scene"` | `class="clip scene"` |
| Clip positioning | `position: fixed; inset: 0;` | `position: fixed; inset: 0;` |
| GSAP timeline | opacity transitions | opacity + position transitions |
| Transition divs | none | `#tr-flash-N` divs between scenes |
| Content | simple text | complex cards, grids, stats |
| beginFrame result | All scenes render | Only final scene renders |

## Tentative Fixes Attempted

The following did NOT fix the issue:
- Removing all `tl.set('#sceneN', { visibility: 'hidden' })` calls from timeline
- Using `position: fixed; inset: 0;` on `.clip` instead of `position: absolute; width: 1080px;`
- Adding `class="scene"` to all clip divs
- Using `--no-clip-visibility` flag
- Various combinations of `--no-low-memory-mode`

---

**File this at: https://github.com/NousResearch/hyperframes/issues/new**
Labels: `bug`, `beginframe`, `capture-mode`
