# Browser Search — Deployment Reference

## Camofox: Native Node.js (not Docker)

**Critical finding:** Camofox has NO public Docker Hub image. The `jo-inc/camofox-browser` repo on Docker Hub returns "access denied". The only way to run it is native Node.js.

**Docker build also fails** — the Dockerfile uses `apt-get update` with `RUN --mount=type=bind,source=dist` which requires the dist/ binaries to exist first. Builds fail in environments with slow/noisy apt mirrors. Workaround: always use native Node.js mode.

### Setup steps (in order)

```bash
# 1. Clone camofox repo
git clone https://github.com/jo-inc/camofox-browser.git \
  /root/.hermes/projects/browser-search/camofox

# 2. Install deps
cd /root/.hermes/projects/browser-search/camofox
npm install

# 3. Download Camoufox binary (~679MB) and yt-dlp
make fetch

# 4. Extract Camoufox to the cache location
mkdir -p ~/.cache/camoufox
unzip -q dist/camoufox-x86_64.zip -d ~/.cache/camoufox
chmod -R 755 ~/.cache/camoufox

# 5. Start (auth-required endpoints need API key)
CAMOFOX_API_KEY=your_key_here npm start
```

### Makefile targets
```
make fetch       # Download dist/camoufox-x86_64.zip + dist/yt-dlp-x86_64
make build       # Docker build (skip — use native instead)
make up          # Docker run (skip — use native instead)
```

### Version info
- Camoufox: 135.0.1 (beta.24)
- yt-dlp: latest linux x86_64 binary

## SearXNG Docker setup

```bash
cd /root/.hermes/projects/browser-search/searxng
docker compose up -d
```

Compose file: `searxng/docker-compose.yaml`
Settings: `searxng/searxng/settings.yml`

Health check:
```bash
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/search?format=json&q=health"
```

## CloakBrowser

Already installed via browser-search npm deps (package: `cloakbrowser`). No additional setup.

Test:
```bash
node /root/browser-search/scripts/cloak/cloak-fetch.mjs "https://example.com"
```

## Camofox — impit native bindings not loading

If `npm start` fails with:
```
Error: impit couldn't load native bindings.
[cause]: Error: Cannot find native binding.
npm has a bug related to optional dependencies (github.com/npm/cli/issues/4828).
```

The fix is a **clean reinstall** — `npm rebuild` alone is insufficient:
```bash
cd /root/.hermes/projects/browser-search/camofox
rm -rf node_modules package-lock.json
npm install
```

Then restart: `CAMOFOX_API_KEY=*** npm start`

## Port mapping summary

| Service | Port | URL |
|---|---|---|
| SearXNG | 8080 | http://localhost:8080 |
| Camofox | 9377 | http://localhost:9377 |
| Camofox docs | 9377 | http://localhost:9377/docs |
