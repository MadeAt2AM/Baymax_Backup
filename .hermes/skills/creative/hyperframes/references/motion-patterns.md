# HyperFrames Motion Patterns

Proven animation patterns for HyperFrames GSAP timelines. Each is deterministic and compatible with the headless capture renderer.

---

## Typewriter Effect

Typing text character-by-character using a `tl.call` loop with closures. Must be synchronous (no async).

```js
const str = "Recommend: MULTI-AGENT SYNTHESIS with override.";
const el = document.getElementById('typewriter-target');

for (let i = 0; i <= str.length; i++) {
  root.call(
    ((ci) => () => { el.textContent = str.slice(0, ci); })(i),
    [],
    18.8 + i * 0.048  // start time + per-char delay (seconds)
  );
}
```

**Key pattern:** `(ci) => () => { ... }(i)` — IIFE closure captures loop variable at creation time. Without this, all iterations see `i = str.length` (the final value when the loop ends).

**Per-character delay:** 0.045–0.055s per char at 30fps gives natural reading speed (~20-22 chars/sec). Adjust for pacing.

---

## Cascading Agent Cards (Collapse + Enter)

When a list of cards should appear one at a time with the previous card collapsing/fading:

```js
// Each card enters with elastic scale, then exits before the next enters
root.from('#agent1', {
  opacity: 0, y: -80, scale: 0.85, duration: 0.6, ease: 'back.out(1.7)'
}, 6.1);
root.from('#agent2', {
  opacity: 0, y: -80, scale: 0.85, duration: 0.6, ease: 'back.out(1.7)'
}, 6.75);
root.from('#agent3', { ... }, 7.4);

// Previous card exits when the next enters
root.to('#agent1', { opacity: 0, y: -60, scale: 0.9, duration: 0.3, ease: 'power2.in' }, 6.7);
root.to('#agent2', { opacity: 0, y: -60, scale: 0.9, duration: 0.3, ease: 'power2.in' }, 7.35);
// Last card stays until scene end
root.to('#agent5', { opacity: 0, duration: 0.5, ease: 'power2.in' }, 14.85);
```

**Stagger:** 0.65s between entries gives ~1.35s visible time per card in a 9s scene. Adjust per card count and scene length.

---

## Flash Transition Overlay

A near-instant white flash between scenes. Uses a fixed overlay div with rapid opacity up/down:

HTML:
```html
<div class="flash-overlay" id="flash"></div>
```

```css
.flash-overlay {
  position: fixed; inset: 0;
  background: #FDFBF7;  /* use scene background color */
  z-index: 100; opacity: 0; pointer-events: none;
}
```

GSAP (at the transition boundary, ~2.93s in a 3s scene):
```js
root.set('#flash', { opacity: 0 }, 2.85);                          // reset
root.to('#flash',   { opacity: 1, duration: 0.08, ease: 'power4.in' }, 2.85);  // flash up
root.set('#flash',  { opacity: 0 }, 2.93);                          // reset for hard kill
root.to('#flash',   { opacity: 0, duration: 0.06, ease: 'power2.out' }, 2.93); // fade
root.set('#flash',  { opacity: 0 }, 3.00);                          // hard kill
```

**Note:** The hard kill at 3.00s prevents stale opacity state on non-linear seeking.

---

## Gaussian Blur + Position Fade (Text Entrance)

For premium editorial feel on headline text:

```js
root.from('.scene-headline', {
  filter: 'blur(12px)', opacity: 0, y: 40,
  duration: 0.9, ease: 'power3.out'
}, 0.1);
```

Works well for first-line text hooks. Use `blur(8–14px)` depending on font size. Pair with `power3.out` or `expo.out` for snappy deceleration.

---

## Satellite Node Growth (Trim Paths / Line Growth)

Simulating line-growth from a center node to multiple satellite points:

```js
// Council card pops in
root.from('#council-card', {
  scale: 0.5, opacity: 0, duration: 0.7, ease: 'back.out(1.7)'
}, 3.6);

// Satellite nodes grow outward one by one
root.from('#council-card .satellite-node', {
  scale: 0, opacity: 0, duration: 0.4, ease: 'back.out(1.7)'
}, 3.9, 0.12);  // 0.12s stagger = 4th positional arg
```

---

## Elastic Scale Pop (Overshoot Entrance)

For cards, buttons, badges — the classic overshoot snap:

```js
root.from('.cta-btn', {
  scale: 0.6, opacity: 0, duration: 0.7, ease: 'back.out(2.0)'
}, 21.6);
```

`back.out(1.7–2.0)` gives a noticeable overshoot without being excessive. For subtle overshoot: `back.out(1.2)`.

---

## Progress Bar Fill (Width Animation)

Synthesizing progress bar via `width` on a fill element inside a track:

```js
// Progress track fills from #111111 to #D32F2F (via CSS gradient)
root.from('#prog-fill', {
  width: '0%', duration: 1.2, ease: 'power3.inOut'
}, 15.6);
```

CSS:
```css
.progress-track {
  width: 600px; height: 8px;
  background: rgba(17,17,17,0.15);
  border-radius: 4px; overflow: hidden;
}
.progress-fill {
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, #111111 0%, #D32F2F 100%);
  border-radius: 4px;
}
```

---

## Spotlight Sweep on CTA Button

A horizontal light sweep across a button using a skewed pseudo-element:

```css
.cta-btn {
  position: relative; overflow: hidden;
}
.cta-btn::before {
  content: '';
  position: absolute;
  width: 200%; height: 100%;
  background: rgba(255,255,255,0.25);
  top: 0; left: -100%;
  transform: skewX(-20deg);
  animation: spotlight 2.5s ease-in-out infinite;
}
@keyframes spotlight {
  0%   { left: -100%; }
  60%  { left: -100%; }  /* hold */
  80%  { left: 60%; }    /* sweep */
  100% { left: 120%; }
}
```

**Note:** `animation` on a pseudo-element is CSS-only (not GSAP), so it runs independently of the GSAP timeline. It's deterministic (no random), so it's safe for video rendering.

---

## Verdict Flash (Scene 5)

A brief white flash at 18.05s to punctuate the verdict reveal:

```js
root.set('#flash', { opacity: 0 }, 18.05);
root.to('#flash', { opacity: 0.7, duration: 0.06, ease: 'power4.in' }, 18.05);
root.set('#flash', { opacity: 0 }, 18.11);
```
