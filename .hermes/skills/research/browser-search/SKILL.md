---
name: browser-search
description: "Three-tier browsing: SearXNG (search) → Camofox (browser) → CloakBrowser (stealth). Handles search, page snapshots, screenshots, and protected-site scraping."
version: 1.0.0
author: Hermes Agent
---

# Browser Search — Hermes Skill

Three-tier browsing system: **SearXNG** (search) → **Camofox** (browser automation) → **CloakBrowser** (stealth escalation).

## Status (as of June 2026)

| Service | Status | Endpoint | Notes |
|---------|--------|----------|-------|
| SearXNG | Working | `http://localhost:8080` | HTTP 200, Docker container `searxng` up, 27 results on test query |
| Camofox | Working | `http://localhost:9377` | Browser tab creation + snapshot + DOM extraction verified |
| CloakBrowser | Working | `~/.cloakbrowser/chromium-146.0.7680.177.5/chrome` | Binary installed; cloak-fetch tested — 5.3s cold start, no anti-bot challenges |

## Architecture

```
Hermes Agent
    ↓ search
SearXNG (Docker, port 8080) — meta-search engine, no API key needed
    ↓ results
Camofox (port 9377) — anti-detect Firefox browser, browse pages
    ↓ fallback
CloakBrowser — stealth Chromium, for protected sites (Instagram, etc.)
```

## Quick Start

```bash
# 1. Start SearXNG
docker compose -f /root/.hermes/projects/browser-search/searxng/docker-compose.yaml up -d

# 2. Start Camofox
cd /root/.hermes/projects/browser-search/camofox && CAMOFOX_API_KEY=<key> npm start

# 3. Wait ~15s for browser warm-up, then verify
curl http://localhost:9377/health

# 4. Test tab creation
curl -X POST http://localhost:9377/tabs \
  -H "Content-Type: application/json" \
  -d '{"userId":"test","sessionKey":"default","url":"https://example.com"}'
```

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Camofox server health |
| POST | `/tabs` | Create a new browser tab |
| GET | `/tabs/:id/snapshot?userId=X` | Get page snapshot (DOM tree) |
| GET | `/tabs/:id/screenshot?userId=X` | Full-page screenshot |
| GET | `/tabs` | List all active tabs |

## Known Issues and Fixes

### Issue: `cannot open display: [object Promise]`

Camoufox binary fails with `Error: cannot open display: [object Promise]`.

Root cause: In `server.js` ~line 954, `localVirtualDisplay.get()` is called synchronously but `VirtualDisplay.start()` is async — the Promise object leaks as the display string instead of `:99`.

Fix in `server.js` ~line 954:
```
// BEFORE:
localVirtualDisplay = pluginCtx.createVirtualDisplay();
vdDisplay = localVirtualDisplay.get();

// AFTER:
localVirtualDisplay = pluginCtx.createVirtualDisplay();
await localVirtualDisplay.start();  // ADD THIS LINE
vdDisplay = localVirtualDisplay.get();
```

### Issue: `Browser.setDefaultViewport — "<root>.viewport.isMobile" not described`

Tab creation fails with CDP protocol error. Firefox rejects the `isMobile` field in `Browser.setDefaultViewport`.

Root cause: `playwright-core@1.58+` always sends `isMobile` in CDP's `Browser.setDefaultViewport` call, but this Camoufox Firefox build's CDP implementation doesn't accept that field.

**Fix — automated via `scripts/postinstall.js`** (runs as npm lifecycle hook, no manual action needed after `npm install`):
- Patches `node_modules/playwright-core/lib/coreBundle.js`: removes `isMobile` from the viewport object in `doUpdateDefaultViewport()`
- Patches `server.js`: adds `await` to `localVirtualDisplay.start()`

**What does NOT work (do not use):**
- `noDefaultViewport: true` in `browser.newContext()` context options — this is a **browser launch** option, not a context option. Applying it at launch level does not prevent the `isMobile` field from being sent when `newContext()` itself creates a context. The CDP error occurs at the context level.
- Intercepting `b.session.send` in `server.js` — `b.session` is not the FFConnection object at the point where it can be intercepted from server.js; the CDP call happens deeper in playwright-core internals. The `coreBundle.js` patch is the only approach that works.

## CloakBrowser Binary Path

CloakBrowser's npm package (`cloakbrowser`) manages its own binary at:
```
~/.cloakbrowser/chromium-<version>/chrome
~/.cloakbrowser/chromium-<version>/chromedriver
~/.cloakbrowser/chromium-<version>/chrome_100_percent.pak
~/.cloakbrowser/chromium-<version>/locales/
...
```

The **current installed version**: `chromium-146.0.7680.177.5` (444MB chrome binary).

The `scripts/check.sh` glob `~/.cloakbrowser/chromium-*/chrome` correctly detects this. The old glob `~/.cloakbrowser/*.desktop` was wrong — CloakBrowser does not create `.desktop` files.

If the npm package's internal downloader stalls (it writes `_download_<timestamp>.tar.gz` to `~/.cloakbrowser/`), kill it and download manually with curl:
```bash
rm -f ~/.cloakbrowser/_download_*.tar.gz
curl -L -o ~/.cloakbrowser/cloakbrowser.tar.gz \
  "https://github.com/CloakHQ/cloakbrowser/releases/download/chromium-v146.0.7680.177.5/cloakbrowser-linux-x64.tar.gz"
# Extracts directly into ~/.cloakbrowser/ — no need to manually move files
tar -xzf ~/.cloakbrowser/cloakbrowser.tar.gz -C ~/.cloakbrowser/
```

The `scripts/check.sh` fix (applied June 2025): SearXNG curl check needs `-L` flag; CloakBrowser binary check glob is `~/.cloakbrowser/chromium-*/chrome` not `*.desktop`.

**⚠️ Always `cd /root/browser-search` before running CloakBrowser scripts** — `scripts/cloak/cloak-fetch.mjs` imports `cloakbrowser` from the local `node_modules/`, not a global npm package. Running from any other directory uses the wrong version or fails.

## Files and Paths

| What | Path |
|------|------|
| browser-search code | `/root/browser-search/` |
| Camofox server | `/root/.hermes/projects/browser-search/camofox/server.js` |
| Camoufox binary | `~/.cache/camoufox/camoufox-bin` (679MB) |
| SearXNG compose | `/root/.hermes/projects/browser-search/searxng/docker-compose.yaml` |
| Health check | `/root/browser-search/scripts/check.sh` |
| Camofox profiles | `~/.camofox/profiles/` | (postinstall patch logic: `references/postinstall-patch.md`) |
| CloakBrowser binary | `~/.cloakbrowser/chromium-146.0.7680.177.5/chrome` (444MB) |
| CloakBrowser npm scripts | `/root/browser-search/scripts/cloak/` |

| Lead generation | `references/lead-generation.md` |

## Health Check

```bash
# Preferred — use the script (updated June 2025 with correct curl -L and binary glob):
bash /root/browser-search/scripts/check.sh

# Manual verification:
curl -so /dev/null -w "SearXNG: %{http_code}\n" -L "http://localhost:8080/search?q=test&format=json"
curl -so /dev/null -w "Camofox: %{http_code}\n" "http://localhost:9377/health"
docker ps --format "{{.Names}}" | grep searxng
```

**Note:** SearXNG redirects `format=json` queries — always use `-L` with curl or the check returns HTTP 000. The script was fixed in June 2025 to add `-L`.

## After npm install — Patches Are Now Automated

Patches are applied automatically by `scripts/postinstall.js` which runs as the `postinstall` npm lifecycle hook. No manual re-application needed after `npm install`.

The two patches embedded in postinstall:
1. **`server.js` ~968** — adds `await` to `localVirtualDisplay.start()`
2. **`coreBundle.js`** — removes `isMobile` from CDP viewport payload in `doUpdateDefaultViewport()`

To verify patches applied after an install:
```bash
cd /root/.hermes/projects/browser-search/camofox && node scripts/postinstall.js
# Expected output (already patched = last line says "already absent"):
# [camofox-browser] postinstall: Camoufox binary already cached.
# [camofox-browser] postinstall: server.js — localVirtualDisplay.start() already awaited
# [camofox-browser] postinstall: coreBundle.js — isMobile already absent from doUpdateDefaultViewport
```

Implementation detail: the `coreBundle.js` patch locates `Browser.setDefaultViewport", { browserContextId: this._browserContextId, viewport }` via `lastIndexOf`, extracts the 600-char chunk before it, and removes any `isMobile` line sitting between `screenSize` and `deviceScaleFactor`. This avoids false positives from other `isMobile` references elsewhere in the file.

**Restart Camofox after install to pick up patched code:**
```bash
kill $(lsof -ti:9377) 2>/dev/null; sleep 1
cd /root/.hermes/projects/browser-search/camofox && node server.js &
sleep 10 && curl -s http://localhost:9377/health
```

## Related Skills

- `hyperframes-troubleshooting` — HyperFrames render issues
- `hermes-agent` — Hermes CLI and configuration
