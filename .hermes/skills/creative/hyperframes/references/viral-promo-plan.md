# Viral Promo Video — Scene Planning Template

Use this template when the user gives you a script/promo copy and asks you to plan and produce a short-form video (YouTube Shorts, TikTok, Instagram Reels). Apply the structure below, fill in the specifics, then build the hyperframes composition.

## The Structure ( ≈50–60s total)

| Scene | Timing | Purpose | Typical Visuals |
|-------|--------|---------|-----------------|
| **1 — HOOK** | 0–5s | Stop the scroll | Glitch reveal, bold number callout, or provocative stat |
| **2 — THE REVEAL** | 5–15s | Show the value | Cards/grid of categories, icons, spec counts |
| **3 — DEEP VALUE** | 15–22s | Build the desire | One highlighted element pulsing, specific benefit line |
| **4 — THE DEMO** | 22–30s | Proof it works | Terminal/code window, self-typing command |
| **5 — THE DROP** | 30–38s | Satisfying payoff | Items cascade/fall into place — "147 agents drop in" |
| **6 — SOCIAL PROOF** | 38–46s | Normalize it | Team grid assembled, stats visible |
| **7 — CTA** | 46–52s | Act now | Glowing text, single action, FREE callout |

## Visual Identity Rules

- **Canvas:** Dark `#0a0a0f`, never white or light gray
- **Primary accent:** Electric blue `#3b82f6`
- **Secondary accent:** Hot magenta `#e11d48` (use sparingly — CTA only)
- **Text:** White `#ffffff` for headlines, `#94a3b8` (slate-400) for secondary
- **Font stack:** Space Grotesk (headlines, Sans) + JetBrains Mono (terminal, code)
- **Motion:** Fast cuts (0.4–0.6s per element), staggered entrances, glitch/scale transitions between scenes
- **Background:** Subtle dot-grid or blueprint pattern (CSS radial-gradient), fixed, never scrolls

## Scene-by-Scene Detail

### Scene 1 — Hook (0–5s)
- Dark screen → glitch distortion on text
- Large bold number in center (e.g. "147")
- Hook line fades in with blur-to-sharp
- Optional: scan-line overlay, chromatic aberration on number
- Text: the opening statement from the script

### Scene 2 — The Reveal (5–15s)
- Grid of specialist domain cards flies in (8 categories max visible)
- Each card: emoji icon + category name + agent count
- Categories: Finance, Marketing, Product, Operations, Engineering, Legal, HR, & 25 more
- Stagger entrance: 0.08s between cards, `power3.out`
- Headline above grid: "Name it — it's already in here"

### Scene 3 — Deep Value (15–22s)
- One card highlighted (golden/magenta glow ring pulsing)
- Quote line: "Ones you'd never think to write yourself"
- Sub-text: "Perfect that they're all in one database"
- Fade everything else to 30% opacity

### Scene 4 — The Demo (22–30s)
- Terminal window drops in from top (scale + fade)
- MacOS-style window chrome: three dots (red/yellow/green), "zsh — hyperframes" title
- Command types itself character by character:
  ```
  npx claude-code agents import
  ```
- Caption below: "One command. Point it at Claude Code."
- Typewriter effect: 50ms per character, `power4.out`

### Scene 5 — The Drop (30–38s)
- Agent nodes cascade from top (random stagger, 0.04s between each)
- Small colored squares/nodes representing each agent
- Directory tree appears at bottom:
  ```
  agents/
  ├── finance/
  ├── marketing/
  └── ... (147 nodes visible)
  ```
- Headline: "147 agents drop directly into your directory"

### Scene 6 — Social Proof (38–46s)
- Full grid of agent nodes (all 147 visible or representative sample)
- Grid pulses with subtle glow
- Headline: "Your massive team of AI agents"
- Stats row: "Finance · Marketing · Product · Operations · Engineering · Legal · HR"

### Scene 7 — CTA (46–52s)
- "Comment" in large white text, "FREE" in electric blue, glowing
- Sub: "and I'll send you the full repo link directly"
- Tag at bottom: `[ // FREE ]` in bordered pill
- Optional: pulsing glow animation on "FREE"
- Fade to dark at end

## Transitions

- **Scene 1 → 2:** Flash-through-white (100ms) or glitch-cut
- **Scene 2 → 3:** Smooth crossfade (400ms)
- **Scene 3 → 4:** Push-slide down (terminal drops in)
- **Scene 4 → 5:** Wipe or dissolve
- **Scene 5 → 6:** Fade
- **Scene 6 → 7:** Flash-through-blue or glitch

## Checklist Before Rendering

- [ ] Visual identity defined (canvas, colors, fonts)
- [ ] Hero frame for each scene built before animation
- [ ] `data-start` and `data-duration` on every composition div
- [ ] Root div has `data-start="0"` (linter requirement)
- [ ] GSAP stagger uses 4th positional argument, NOT `stagger` key in vars
- [ ] All font URLs verified with `curl -sI <url> | head -1`
- [ ] Terminal chrome: red/yellow/green dots, slate title bar
- [ ] No `repeat: -1` anywhere
- [ ] `hyperframes lint` passes with 0 errors
- [ ] `hyperframes validate` passes with 0 errors
- [ ] `hyperframes inspect` run and issues resolved
- [ ] Frame extracted at mid-composition for visual check
