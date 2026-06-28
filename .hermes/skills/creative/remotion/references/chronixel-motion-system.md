# Chronixel Motion Graphics System

Creative direction framework for Remotion video creation. Loaded when building motion graphics compositions that follow a visual-communication-first approach.

## Core Philosophy

**Act like a creative director, not a caption generator.** The script provides the meaning; your motion graphics provide the visual explanation. Show the concept rather than repeating words literally.

- Protect the meaning of the script while freely improving visual execution
- Do not recreate the script word-for-word on screen
- Use text only when it makes the message stronger
- Visualize the point — don't caption it

## Typography Rules

- **Font:** `Poppins ExtraBold` (use via `@remotion/google-fonts`)
- **Letter spacing:** Very tight — letters almost touching
- **Feel:** Bold, premium, tight, high-impact

## Visual Communication First

- **Allowed:** 1–4 word labels, UI tags, button labels, short callouts, section titles
- **Avoid:** Full script sentences, paragraph overlays, excessive labeling, text that competes with voiceover

## Translation Metaphors

| Concept | Visual Translation |
|---|---|
| Speed/Efficiency | Fast-moving UI cards, compressed timelines, progress bars |
| Confusion/Disorganization | Scattered panels, overlapping windows, blurred labels |
| Clarity/Organization | Elements snapping into alignment, fog/blur fading, clean glass panels |
| Growth/Scaling | Rising graphs, content blocks stacking upward, dashboard leveling up |
| AI Tools/Automation | Clean automation flows, prompt cards, glowing nodes — NO cheesy robots |

## Chronixel Aesthetic Constraints

All creative work stays within the Chronixel signature aesthetic:

- **Background:** Dark cinematic (`#0A0A0F` or similar) with subtle SVG grid
- **UI Elements:** Premium glass morphism with `backdrop-filter: blur()`
- **Highlights:** Orange gradient (`#FF6B00 → #FF8C00`)
- **Text:** Off-white (`#F0EDE8`), very tight letter spacing
- **Motion:** Smooth, clean layouts, zero clutter

## Scene Versioning System

**Never Replace. Always Version.**

When revising a scene based on feedback, create a **new version** with the naming format:

```
Scene [N] V[version] — [Original Title]
```

Examples:
- Original: `Scene 2 - The Workflow Problem`
- First revision: `Scene 2 V2 - The Workflow Problem`
- Second revision: `Scene 2 V3 - The Workflow Problem`

Rules:
- Use the **latest version** as the base for the next revision
- Scene number stays the same — only version increases
- Never edit a scene in place
- Treat feedback phrases like "Add this to Scene 2", "Change Scene 4", "Make Scene 1 feel faster" as revision requests
