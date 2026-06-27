# Camofox postinstall Patch Implementation

## Location
`/root/.hermes/projects/browser-search/camofox/scripts/postinstall.js`

## What It Does
After `npm install`, the npm lifecycle runs `postinstall.js` which:
1. Downloads Camoufox binaries (via `npx camoufox-js fetch`) — skips if already cached
2. Applies `server.js` patch — adds `await` to `localVirtualDisplay.start()`
3. Applies `coreBundle.js` patch — strips `isMobile` from CDP viewport payload

## coreBundle.js Patch Logic (for reference)
The patch targets `doUpdateDefaultViewport()` in the BidiBrowserContext class:

```
// Find the specific CDP call
const setDefaultViewportCall = 'Browser.setDefaultViewport", { browserContextId: this._browserContextId, viewport }';
const idx = src.lastIndexOf(setDefaultViewportCall);

// Extract 600 chars before the call to get the full viewport object
const chunk = src.slice(Math.max(0, idx - 600), idx + setDefaultViewportCall.length);

// Remove isMobile line if present between screenSize and deviceScaleFactor
const isMobileLineMatch = chunk.match(/isMobile\s*:\s*[^,]+,\s*\n\s+deviceScaleFactor\s*:/);
if (isMobileLineMatch) {
  src = src.slice(0, chunkStart) + chunk.replace(isMobileLineMatch[0], 'deviceScaleFactor:') + src.slice(idx + setDefaultViewportCall.length);
  writeFileSync(file, src);
}
```

Why this approach: `lastIndexOf` on the specific CDP call string ensures we patch the right `doUpdateDefaultViewport()` — there are multiple functions with that name in coreBundle.js. Extracting a chunk before the call avoids regex false positives from the 200+ other `isMobile` references scattered throughout the 73k-line file.

## server.js Patch Logic
Simple string replacement — adds `await` before `localVirtualDisplay.start()`:
```js
src = src.replace(
  /(localVirtualDisplay\s*=\s*pluginCtx\.createVirtualDisplay\(\))\s*;?\s*\n?\s*(localVirtualDisplay\.start\(\))/,
  '$1;\n        await $2'
);
```

## Verifying Patch Status
```bash
cd /root/.hermes/projects/browser-search/camofox && node scripts/postinstall.js
```

Expected (already patched):
```
[camofox-browser] postinstall: Camoufox binary already cached.
[camofox-browser] postinstall: server.js — localVirtualDisplay.start() already awaited
[camofox-browser] postinstall: coreBundle.js — isMobile already absent from doUpdateDefaultViewport
```
