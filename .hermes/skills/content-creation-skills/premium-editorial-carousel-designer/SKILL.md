---
name: premium-editorial-carousel-designer
description: "Use when designing the visual system for an Instagram, LinkedIn, or X carousel. Enforces the permanent Premium Editorial design language — magazine-meets-product-launch — for every slide. Covers palette, typography, canvas, hook slide, educational slide, CTA slide, image rendering, motion language, and the consistency checklist. Pair with carousel-copy so every slide plan ships with copy and visual in one pass. Triggers: carousel design, premium carousel, editorial carousel, IG carousel design, LinkedIn carousel design, X carousel design, hook slide, CTA slide, slide layout, visual system for carousels, carousel image prompt."
version: 1.0.0
author: CYBERSLIDE / MadeAt2Am
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [carousel, design, visual, editorial, premium, social-media, brand]
    related_skills: [carousel-copy, brandkit, imagegen-frontend-web]
---

# Premium Editorial Carousel Designer

Generate premium social media carousel designs that look like high-end editorial magazines mixed with product launch presentations. The output must be optimized for LinkedIn, Instagram, and X. The first slide must stop scrolling immediately. Every remaining slide must educate visually with one clear idea. The carousel should feel like one consistent design system.

**Never invent a new visual style. Always follow this system.**

## Core Design Philosophy

Every carousel should communicate its message within one second.

Prioritize clarity over decoration.

Large typography. Minimal layout. Strong hierarchy. Generous whitespace. Premium rendering.

Every element must have a purpose.

## Theme

- Modern Editorial
- Bold
- Minimal
- Premium
- High Retention

## Color System

| Role | Name | Hex |
|---|---|---|
| Primary | Black | `#111111` |
| Background | Warm Off White | `#F7F5F1` |
| Accent | Crimson | `#DC143C` |
| Secondary | Medium Gray | `#8B8B8B` |
| Tertiary | Light Gray | `#E9E9E9` |

**Rules — never break:**
- Never use orange.
- Never use colorful gradients.
- Only crimson draws attention.

## Typography

### Headline

Ultra Bold Condensed. Preferred fonts: Druk Condensed, Tungsten, Anton, Bebas Neue. Fallback chain: `Bebas Neue → Anton → Druk Condensed → Tungsten → Impact`.

Rules:
- ALL CAPS
- Extremely large
- Tight tracking
- Occupies roughly 35–50% of the slide

### Body

Modern Sans Serif. Preferred fonts: Inter, SF Pro Display, Helvetica Neue. Fallback chain: `Inter → SF Pro Display → Helvetica Neue → Arial`.

Weight: Regular or Medium.

Maximum three to five short paragraphs. Never create large text blocks.

## Canvas

- Size: **1080 × 1350** (4:5, IG-native portrait)
- Margins: **60–80 px** on all sides
- Invisible 12-column grid
- Generous whitespace — nothing should feel crowded

## Background Style

- Warm paper texture
- Very subtle grain
- Almost invisible grid
- Editorial feel
- No gradients, no bright colors

Implementation note for image models: include "subtle warm paper grain texture, almost invisible, no gradients" in every prompt.

## Slide 1 — HOOK (Stop Scrolling Instantly)

This slide should feel like a movie poster. Highest visual impact of the carousel.

### Layout

- Huge controversial headline
- One keyword highlighted inside a crimson rectangle
- Large cinematic 3D hero illustration (objects exploding outward, motion, depth, debris, premium shadows)
- Small supporting sentence near the bottom
- Swipe indicator

### Headline Rules

- Keep under 8 words
- Challenge assumptions
- Create curiosity

Templates:
- STOP PAYING FOR AI.
- YOUR WEBSITE IS LOSING SALES.
- MOST FOUNDERS BUILD WRONG.
- YOU DON'T NEED CHATGPT.

### Hero Image Rules

- Large centered object, occupies ~45% of slide
- Premium 3D render, strong shadows
- Flying objects, fragments, particles, motion blur
- Perspective and depth
- **No flat illustrations**

### Footer

- One short teaser line
- One swipe indicator (small, subtle)

## Educational Slide Structure

Every content slide follows this exact structure:

### Top Left — Crimson Label

Small all-caps crimson label. Pick from: `SKILL 01`, `RULE 02`, `STEP 03`, `FRAMEWORK`, `SYSTEM`. One label per slide.

### Main Heading — One Word

Starts with `/`. Examples: `/DUMBIFY`, `/SYSTEM`, `/AUTOMATE`, `/HOOKS`, `/MINDSET`. Large. Bold. Dominates upper half.

### Body Copy

Three short paragraphs. Each paragraph is one to two lines. Grade 8 reading level. No fluff. Direct language. Concrete examples.

### Supporting Visual — Lower Half

Occupies lower half of slide. Allowed visuals:

- Before vs After
- Flowchart
- Diagram
- Chart
- Graph
- Screenshot
- Browser window
- Code snippet
- Comparison cards
- Simple UI
- Document stack
- Mockup
- Wireframe
- Illustration

### Arrows

Thin crimson arrows. Only point toward learning — never decorative.

### Comparison Cards

Frequently use the patterns: Before/After, Wrong/Right, Old/New. Black card versus White card.

## Visual Language — Required Elements

Every slide should include at least four of these:

- Thin crimson divider
- Small crimson section tag
- Tiny corner crop marks
- Tiny plus symbols
- Editorial guide lines
- Accent underline
- Paper texture
- Large whitespace
- Editorial alignment
- Supporting visual
- Thin crimson arrow

## Graphics Style

- Minimal
- Editorial
- Flat mixed with realistic renders
- Premium
- **Never cartoon**

Use: cards, documents, windows, dashboards, screenshots, simple icons, wireframes, mockups, flow diagrams, charts.

## Image Rendering

- Soft studio lighting
- Matte materials
- Premium textures
- Clean reflections
- High detail
- Centered compositions
- Subtle shadows

## Motion Language

Although static, every slide should imply movement. Methods:

- Flying objects
- Exploding fragments
- Perspective
- Tilted cards
- Broken grids
- Directional arrows
- Depth
- Particles

## Writing Rules

- Short sentences
- No buzzwords, no filler
- No long paragraphs
- Active voice
- Every sentence moves the story forward

## Visual Hierarchy

Readers should naturally scan:

1. Headline
2. Body
3. Supporting visual
4. Swipe

## CTA Slide

Minimal. Huge headline. Single action.

Template:
- Headline: `WANT THE TEMPLATE?`
- Body line 1: `Comment`
- Body line 2 (in crimson): `"TEMPLATE"`
- Body line 3: `I'll send it.`
- Large comment box mockup underneath
- No additional information

## Design Consistency Checklist

Every slide must satisfy all of the following before delivery:

- [ ] Warm paper background `#F7F5F1`
- [ ] Crimson accents only — `#DC143C`, no other bright color
- [ ] Giant condensed headline (Bebas Neue / Anton / Druk)
- [ ] Minimal body copy (≤ 30 words body, no big blocks)
- [ ] Premium whitespace (60–80 px margins)
- [ ] Editorial alignment (invisible 12-col grid)
- [ ] Thin crimson divider present
- [ ] Corner crop marks present
- [ ] Tiny plus symbols present
- [ ] Supporting visual present on educational slides
- [ ] Premium shadows, matte 3D rendering where used
- [ ] One core idea per slide
- [ ] Easy to understand within one second

## Output Requirements

For every carousel request, generate:

- Slide-by-slide content
- Image prompt for every slide
- Layout instructions
- Typography hierarchy
- Visual placement instructions
- Illustration and graphic directions
- CTA slide

**Do not change the design language unless explicitly instructed.** Treat this style guide as the permanent design system for all future carousel generations.

## Integration with carousel-copy

This skill is the **visual half** of the carousel pipeline. `carousel-copy` owns structure, hook, body copy, and word counts. This skill owns typography, palette, layout, hero illustrations, and image-gen prompts. When generating a full carousel:

1. Run `carousel-copy` first → produces the slide plan (titles, body, visuals in plain language).
2. Apply this skill → translate each slide's `Visual:` line into a full Premium Editorial image prompt, fix typography, enforce the consistency checklist.
3. Output one combined deliverable: copy + visual system in the same document.

Never produce image prompts without running the consistency checklist per slide. Never produce copy without enforcing this skill's word budgets.

## Image Prompt Template

Use this skeleton for every educational slide image prompt:

```
Premium editorial Instagram/LinkedIn carousel slide, 1080x1350 portrait.
Warm off-white paper background #F7F5F1 with very subtle grain texture, no gradients.
60–80 px margins, invisible 12-column grid.

Top-left: small all-caps crimson #DC143C label reading "[LABEL]".
Headline: ultra-bold condensed sans-serif (Bebas Neue / Anton / Druk),
ALL CAPS, occupying upper 35–45% of the slide, reading "[HEADLINE]".

Body: modern sans-serif (Inter / SF Pro Display), regular/medium weight,
max three short paragraphs, obsidian #111111 type, total ≤ 30 words.

Visual: [DESCRIBE THE SUPPORTING VISUAL HERE — diagram / before-after / flow / screenshot mockup / cards / etc.]. Use obsidian, warm off-white, light gray #E9E9E9, and crimson #DC143C only. Thin crimson arrows, corner crop marks, tiny plus symbols. Premium shadows, matte materials, centered composition, soft studio lighting.

Editorial, magazine-meets-product-launch feel. No cartoon, no flat illustrations, no orange, no colorful gradients.
```

For the **hook slide**, replace the headline block with:

```
Center-frame: cinematic 3D hero illustration occupying ~45% of slide,
obsidian #111111 base material, premium matte 3D render, soft studio lighting,
strong shadows, flying fragments and particles exploding outward, motion blur,
perspective depth.
Headline overlay (top): ultra-bold condensed ALL CAPS obsidian #111111,
~40% slide height.
Keyword highlighted inside a crimson #DC143C rectangle inside the headline.
Bottom: one short teaser line + small swipe indicator.
```

## Common Pitfalls

1. **Using yellow/orange accents** — banned. The accent is crimson `#DC143C` only.
2. **Cream `#FDFBF7` from the old brand** — wrong. New background is warm off-white `#F7F5F1`.
3. **Flat illustrations on the hook slide** — the hook needs cinematic 3D rendering.
4. **Two or more ideas per slide** — split the slide, never combine.
5. **Body copy > 30 words** — migrate detail into the visual.
6. **No crimson label on educational slides** — every content slide gets one in the top-left.
7. **Heading not starting with `/`** — the one-word heading convention is structural; keep it.
8. **CTA with two actions** — one headline, one comment keyword, no second option.
9. **Missing consistency checklist items** — every slide must hit 4+ visual language elements.

## Verification Checklist

Before delivery:

- [ ] Every slide has a crimson label in the top-left (except hook and CTA)
- [ ] Every headline is ALL CAPS condensed bold
- [ ] Body copy ≤ 30 words per educational slide
- [ ] Color audit: only `#111111`, `#F7F5F1`, `#DC143C`, `#8B8B8B`, `#E9E9E9` present
- [ ] Hook slide uses cinematic 3D rendering, not flat illustration
- [ ] CTA slide has exactly one action
- [ ] At least one slide carries a screenshot/saveable quote line
- [ ] All 13 items on the Design Consistency Checklist pass
