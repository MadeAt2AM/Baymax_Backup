# Claude Code Reel — Composition Reference

**Project:** `/root/claude-code-reel/`
**Composition:** `MainComp` (1080×1080, 30fps, 450 frames = 15 seconds)

## Scene Timeline

| Scene | Frames | Time | Content |
|-------|--------|------|---------|
| Day 1 | 0–90 | 0:00–3:00 | 3 project cards + kinetic text (SOCIAL/DEV/ADMIN) |
| Day 2 | 90–165 | 3:00–5:30 | User + Claude beam + COMMENT CTA |
| Day 3 | 165–225 | 5:30–7:30 | Claude magnet + Drive/Gmail/Notion |
| Day 4 | 225–315 | 7:30–10:30 | Terminal + phone pop-out |
| Outro | 315–450 | 10:30–15:00 | COMMENT CLAUDE + Instagram DM |

## Post-Patch Integrity Check

After ANY patch to a Remotion TSX file, always verify with BOTH:

```bash
cd /root/claude-code-reel && npx tsc --noEmit
cd /root/claude-code-reel && CHROME_BIN=/snap/bin/chromium npx remotion still MainComp --scale=0.25 --frame=10
```

Known failure pattern: a botched patch that replaces a multi-line block can leave TWO copies of a component definition in the file. `tsc --noEmit` catches duplicate `const` declarations (`Cannot redeclare block-scoped variable 'X'`), but only after the duplicate is actually parsed as a separate statement. If the patch accidentally inserted the new component starter without removing the old one, you'll get the duplicate.

Fix: `read_file` the file from scratch (no offset/limit) to see its true state, then patch the duplicate out.

## Key Animation Patterns

### 3D Card Effect
```tsx
const scale = interpolate(frame, [0, 30], [0.5, 1], { extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });
const rotateX = interpolate(frame, [0, 30], [30, 15], { extrapolateRight: "clamp" });
const rotateY = interpolate(frame, [0, 30], [-20, -10], { extrapolateRight: "clamp" });
style={{ transform: `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${scale})` }}
```

### Kinetic Word (sweeps across screen)
```tsx
const opacity = interpolate(f, [0, 10, 40, 50], [0, 1, 1, 0], { extrapolateRight: "clamp" });
const translateX = interpolate(f, [0, 50], [-100, 1200], { extrapolateRight: "clamp", easing: Easing.linear });
style={{ transform: `translateX(${translateX}px)`, opacity, WebkitTextStroke: "1px rgba(255,255,255,0.15)" }}
```

### Pulsing Glow (Claude logo)
```tsx
const pulse = Math.sin(frame * 0.15) * 0.5 + 0.5;
const glowSize = 20 + pulse * 30;
boxShadow: `0 0 ${glowSize}px rgba(210, 168, 76, ${0.3 + pulse * 0.3})`
```

### Spring Snap (app icons to center)
```tsx
const progress = interpolate(f, [0, 40], [0, 1], { extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });
const connected = f > 35;
const scale = connected ? interpolate(f, [35, 45], [1, 1.2, 1], { extrapolateRight: "clamp" }) : progress;
const flashOpacity = connected ? interpolate(f, [35, 38], [0.8, 0], { extrapolateRight: "clamp" }) : 0;
```

### Typing Effect (terminal)
```tsx
// Slice code string length based on frame
const code = "const App = () => { ... }";
const visibleLength = interpolate(frame, [0, 40], [0, code.length], { extrapolateRight: "clamp" });
const displayCode = code.slice(0, Math.floor(visibleLength));
```
