---
name: agent-reach
description: "Multi-platform social media research infrastructure via Agent Reach — installs and manages twitter-cli, reddit (rdt-cli), bilibili (bili-cli), xiaohongshu (xiaohongshu-mcp), xueqiu, linkedin-scraper-mcp, and Groq-powered podcast transcription. Installs into ~/.agent-reach/, managed via the agent-reach CLI, wired into mcporter for MCP tools."
version: 1.0.0
author: Panniantong / CYBERSLIDE Hermes
license: MIT
platforms: [linux, macos, server, desktop]
prerequisites:
  commands: [python3, pip]
  environment: [~/.agent-reach-venv]
metadata:
  hermes:
    tags: [social-media, research, twitter, reddit, xiaohongshu, bilibili, xueqiu, linkedin, groq, podcast, multi-platform]
    homepage: https://github.com/Panniantong/agent-reach
    install_url: https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
    skill_dir: ~/.agent-reach/
---

# Agent Reach — Multi-Platform Social Media Research

Agent Reach is an installer, health-checker, and router for upstream social media CLI tools. It does NOT wrap tools — it installs them and lets you call them directly. Think of it as the plumbing layer for social media research.

**Install location:** `~/.agent-reach/` (tools), `~/.agent-reach-venv/` (Python venv with agent-reach package)

**Activation:** `source ~/.agent-reach-venv/bin/activate` then `agent-reach <command>`

---

## Installation

### Core (always run this first)

```bash
python3 -m venv ~/.agent-reach-venv
source ~/.agent-reach-venv/bin/activate
pip install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto
```

This installs: `gh` (GitHub), `yt-dlp` (YouTube), `mcporter` (MCP + Exa search), feedparser (RSS), Jina Reader (any webpage).

### Optional channels

```bash
agent-reach install --env=auto --channels=all        # everything
agent-reach install --env=auto --channels=twitter,reddit,xiaohongshu  # pick specific
```

Channel names: `opencli`, `twitter`, `xiaohuzhou` (podcast), `xueqiu`, `xiaohongshu`, `reddit`, `facebook`, `instagram`, `bilibili`, `linkedin`, `all`

> **Note:** If the user says "ignore xueqiu", skip it without setup — it is low-priority.

### Safe mode (no system changes)

```bash
agent-reach install --env=auto --safe   # check only
agent-reach install --env=auto --dry-run  # preview
```

---

## Core Commands

| Command | What it does |
|---|---|
| `agent-reach install --env=auto` | Install core infrastructure |
| `agent-reach install --env=auto --channels=X` | Install specific optional channels |
| `agent-reach doctor` | Show channel status (✅ / ⚠️ / ❌) |
| `agent-reach doctor --json` | Machine-readable status dump |
| `agent-reach configure groq-key gsk_xxx` | Set Groq API key for podcast transcription |
| `agent-reach configure proxy URL` | Set HTTP/HTTPS proxy |
| `agent-reach configure --from-browser chrome` | Auto-extract cookies from Chrome (xiaohongshu, xueqiu, reddit) |
| `agent-reach watch` | Quick health + update check |
| `agent-reach check-update` | Check for new versions |

---

## Channel Status (14/15 — as of June 2026)

**✅ Fully working (no credentials needed):**
- GitHub — `gh search repos "..."`
- YouTube — `yt-dlp --dump-json URL`
- V2EX — Direct public API
- RSS — feedparser
- Exa Search — `mcporter call 'exa.web_search_exa(query: "...", numResults: N)'`
- Any webpage — `curl -s "https://r.jina.ai/URL"`
- Bilibili — `bili search "..."`
- 小红书 (xiaohongshu-mcp) — `mcporter call 'xiaohongshu.search_feeds(keyword: "...")'`
- 小宇宙播客 — Groq Whisper transcription active

**✅ Fully working (cookie-authenticated via OpenCLI):**
- **Twitter/X** — `opencli twitter search "..."` or `twitter search "..."` — auth_token + ct0 extracted via `agent-reach configure --from-browser chrome`
- **Reddit** — `opencli reddit search "..."` — reddit_session via same Chrome extraction
- **Facebook** — `opencli facebook whoami`, `profile`, `search`, `feed` — cookies via OpenCLI bridge (c_user, xs, fr, datr, sb)
- **Instagram** — `opencli instagram whoami`, `search`, `user`, `download` — sessionid + csrftoken via OpenCLI bridge (account: `alligator.6949242`). See "OpenCLI Instagram command surface" below for the persistent-site-session invocation pattern.

**⚠️ GitHub — use `gh` CLI, NOT OpenCLI `opencli github`:**
- `gh auth status` → ✅ shows `chrisvincodes` logged in via HTTPS
- `gh search repos "query"` → ✅ works directly
- `opencli github whoami` → ❌ AUTH_REQUIRED — OpenCLI github channel does NOT work even with `gh auth` active
- **Always use `gh` directly for GitHub operations.** OpenCLI github is a separate integration with different auth and is not the fallback.

**⚠️ Installed but needs credentials:**
- Xueqiu — needs VNC Chrome cookie extraction, then `opencli xueqiu login`

**❌ Desktop Chrome + OpenCLI extension required:**
- (none — all desktop-browser channels now resolved)

---

## Upstream Tool Reference

After installation, use upstream tools directly. Agent Reach is the installer/router, not a wrapper.

| Platform | Tool | Example |
|---|---|---|
| Twitter/X | `twitter` (venv only) | `twitter search "query" -n 5` |
| YouTube | `yt-dlp` | `yt-dlp --dump-json URL` |
| Bilibili | `bili` | `bili search "query" --type video` |
| Reddit | OpenCLI (`opencli reddit ...`) | `opencli reddit search "..."` — via CDP browser bridge |
| Instagram | OpenCLI (`opencli instagram ...`) | See "OpenCLI Instagram command surface" below — session via CDP browser bridge, NOT browser_cookie3. See `references/opencli-cookies.md` for the extraction technique. |
| Facebook | OpenCLI | `opencli facebook whoami`, `search`, `profile`, `feed` — cookies via CDP browser bridge |
| GitHub | `gh` | `gh search repos "query"` |
| Web | Jina Reader | `curl -s "https://r.jina.ai/URL"` |
| Exa Search | `mcporter` | `mcporter call 'exa.web_search_exa(query: "...")'` |
| 小红书 | `mcporter` | `mcporter call 'xiaohongshu.search_feeds(keyword: "...")'` |
| Xueqiu/雪球 | OpenCLI (`opencli xueqiu ...`) | `opencli xueqiu whoami` — xq_a_token cookie via OpenCLI browser bridge or VNC Chrome login |
| 小宇宙播客 | Groq Whisper | `bash ~/.agent-reach/tools/xiaoyuzhou/transcribe.sh <URL>` |
| LinkedIn | `mcporter` | `mcporter call 'linkedin.get_person_profile(...)'` |
| RSS | feedparser | `python3 -c "import feedparser; ..."` |

---

### OpenCLI Instagram command surface

Top-level help: `opencli instagram --help`. Read-only commands relevant for scraping:

| Command | Purpose | Notes |
|---|---|---|
| `whoami` | Confirm which Instagram account the CDP session is logged in as | First call on any host — if `logged_in: false` or the wrong account, stop. |
| `user <username>` | Fetch recent posts for an account (mixed media + reels) | Use `--limit N` for cap, `-f json` for parsing, `--window background` to avoid blocking, `--site-session persistent` to reuse the cookie session across calls. |
| `download <url>` | Download images/videos for a post or reel | Use `--path <dir>` to scope into a staging directory, `-f json` for the saved-path response, `--window background --site-session persistent`. |
| `search <query>` | Find accounts | Useful for discovering handles before tracking. |

**Preferred invocation shape (mirror this exactly when replicating on another host):**

```bash
# Auth check — no cookies, no session IDs in output
opencli instagram whoami -f json --window background --site-session persistent

# Pull recent reels for an account
opencli instagram user <username> --limit <N> -f json \
  --window background --site-session persistent

# Download one reel's media
opencli instagram download <reel-url> --path <staging-dir> -f json \
  --window background --site-session persistent
```

**Why `--window background --site-session persistent` matters:**

- `--window background` keeps the call non-blocking and doesn't depend on an interactive desktop session.
- `--site-session persistent` keeps the authenticated browser session alive between invocations, so a periodic scraper doesn't re-authenticate on every run.

Both flags are required to reproduce the Hermes-VPS scraping pattern on a fresh host. Do not change them silently when porting.

### Replicating the Instagram method to another host

When a different host (e.g. dev VPS) needs the same scraping capability — **characterize before replicating**, never invent a parallel method:

1. Record on the proven host: `opencli instagram --help`, `which opencli`, the package install method (`pip show opencli` / `npm ls -g @jackwener/opencli`), browser daemon state, persistent site-session location, Chrome/Chromium version, and the exact `user`/`download` argv shape you rely on.
2. On the target host, install the same package version and reproduce the same daemon + persistent-session layout. Don't modify command args, JSON output, or flags.
3. Test with `whoami` first. If the wrong account or a checkpoint appears, halt for operator re-authentication rather than bypassing.
4. Always pair OpenCLI scraping with a **local** speech-to-text path (Faster-Whisper + FFmpeg). Never wire a paid transcription API into the same pipeline just because it's easier.

**Cookie hygiene:** the OpenCLI profile/session directory IS a credential. Mount it only into the scraper component — never into a web/API/database container. Never commit it, copy it into Docker images, or print it. Use a secondary Instagram account, not the operator's primary.

### Pitfalls

### VNC browser session — htpasswd permission (CRITICAL)

nginx runs as `www-data` and **cannot read `/root/.vnc/.htpasswd`** — this causes `500 internal server error` on every request, logged as:
```
open() "/root/.vnc/.htpasswd" failed (13: Permission denied)
```

**Fix:** Copy htpasswd to `/etc/nginx/.htpasswd` BEFORE reloading nginx:
```bash
cp /root/.vnc/.htpasswd /etc/nginx/.htpasswd && chmod 644 /etc/nginx/.htpasswd
# Update nginx config to point to /etc/nginx/.htpasswd
sed -i 's|auth_basic_user_file /root/.vnc/.htpasswd|auth_basic_user_file /etc/nginx/.htpasswd|' /etc/nginx/sites-available/vnc
nginx -s reload
```

Always put htpasswd in `/etc/nginx/` — never reference a root-owned file from nginx config.

### Snap Chromium forces headless — use Google Chrome .deb (CRITICAL)

`/snap/bin/chromium` and `/usr/bin/chromium-browser` (which wraps snap) **silently force `--ozone-platform=headless`** internally. Even with `DISPLAY=:1`, the browser renders nowhere visible. Symptoms: no window appears in VNC, `--remote-debugging-port` doesn't bind.

**Fix — install Google Chrome from .deb:**
```bash
curl -fsSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o /tmp/chrome.deb
apt-get install -y /tmp/chrome.deb
which google-chrome  # confirms installation
```

**Launch Chrome on VNC display:**
```bash
export DISPLAY=:1
google-chrome --no-sandbox --start-maximized --window-size=1920,1080 https://twitter.com
```

The `which chromium-browser` check will say it exists but it redirects to snap — always use `/opt/google/chrome/chrome` or `google-chrome` (the .deb binary), never `chromium-browser` or `snap chromium`.

### Cookie extraction — `agent-reach configure --from-browser chrome` via rookiepy

`rookiepy` is the primary extraction tool. It reads Chrome's `Local State` encryption key, decrypts AES-GCM-encrypted cookies from the SQLite `Cookies` database — no browser needs to be running.

```bash
source ~/.agent-reach-venv/bin/activate
pip install rookiepy browser-cookie3
agent-reach configure --from-browser chrome
# Output: ✅ Twitter/X: auth_token + ct0  ✅ Reddit: reddit_session configured
```

**What gets extracted:**
- Twitter/X: `auth_token`, `ct0`, `twid`, `guest_id`
- Reddit: `reddit_session`, `token_v2`, `loid`, `edgebucket`
- Instagram: `sessionid`, `csrftoken`, `ds_user_id`, `mid`, `ig_did` (partial — not all key types via this method)
- Facebook: `c_user`, `xs`, `fr`, `datr`, `sb` (encrypted, not decoded by rookiepy alone)

**When rookiepy alone isn't enough (Facebook):** Use `browser_cookie3` directly:
```python
import browser_cookie3, urllib.parse
cj = browser_cookie3.chrome(
    cookie_file='/root/.config/google-chrome/Default/Cookies',
    key_file='/root/.config/google-chrome/Local State'
)
fb = {c.name: c.value for c in cj if 'facebook' in c.domain}
# Values are already decoded (including URL-encoded xs token)
```

### twitter-cli — correct command is `twitter`, not `twitter-cli`

After `pip install twitter-cli`, the binary is named `twitter` (not `twitter-cli`). It lives in the agent-reach venv at `~/.agent-reach-venv/bin/twitter`.

```bash
source ~/.agent-reach-venv/bin/activate
twitter search "query" -n 5           # search tweets
twitter user @username                # user info
twitter timeline -n 10                 # home timeline
```

Options: `-n / --max N` for count, `--json` for JSON output, `--full-text` for table output.

### mcporter config goes to wrong file (known bug)

When running `mcporter config add exa https://mcp.exa.ai/mcp` AFTER `mcporter config add xiaohongshu ...`, the `system` config (`~/.mcporter/mcporter.json`) is missing and exa config gets written to `~/.agent-reach/tools/xiaohongshu/config/mcporter.json` instead of the system config.

**Fix:** Manually create `~/.mcporter/mcporter.json`:

```json
{
  "mcpServers": {
    "exa": { "url": "https://mcp.exa.ai/mcp" },
    "xiaohongshu": { "url": "http://localhost:18060/mcp" }
  }
}
```

The `~/.mcporter/mcporter.json` must exist before running any `mcporter config add` command to prevent this.

### VNC browser session for cookie extraction (server-only)

For Twitter, Reddit, Xueqiu, and other cookie-auth platforms on a server with no desktop Chrome, set up a **password-protected VNC web session** so the user can log in directly in a real browser, then extract cookies from the Chrome profile.

**Stack:** TigerVNC → websockify → nginx (HTTPS + HTTP Basic Auth)

**Setup (one-time):**
```bash
# 1. Install packages
apt-get install -y tigervnc-standalone-server websockify novnc nginx apache2-utils

# 2. Set VNC password (user provides this)
mkdir -p ~/.vnc
echo "PASSWORD" | tigervncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

# 3. Generate SSL cert
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /root/.vnc/ssl.key -out /root/.vnc/ssl.crt \
  -subj "/CN=YOUR_HOSTNAME"

# 4. HTTP Basic Auth (user provides username + password)
htpasswd -bc /root/.vnc/.htpasswd USERNAME PASSWORD

# 5. Start TigerVNC (background, long-lived)
terminal(background=true, command="tigervncserver :1 -fg -xstartup /usr/bin/startxfce4")

# 6. Start websockify (background, long-lived)
terminal(background=true, command="websockify --web /usr/share/novnc --cert /root/.vnc/ssl.crt 6080 localhost:5901")

# 7. Configure nginx reverse proxy — see nginx config below
# 8. CRITICAL: copy htpasswd so www-data can read it
cp /root/.vnc/.htpasswd /etc/nginx/.htpasswd && chmod 644 /etc/nginx/.htpasswd
sed -i 's|auth_basic_user_file /root/.vnc/.htpasswd|auth_basic_user_file /etc/nginx/.htpasswd|' /etc/nginx/sites-available/vnc
nginx -s reload
```

**User URL:** `https://YOUR_HOSTNAME/vnc.html` — basic auth username/password is the htpasswd credentials. User accepts self-signed SSL cert warning in browser.

### xiaohongshu-mcp — check for pre-auth session first

xiaohongshu-mcp may already have a valid session baked into the binary (check the `ai-report` account in the health response). Before going through QR-scan setup, start the daemon and check:

```bash
cd ~/.agent-reach/tools/xiaohongshu && ./xiaohongshu-mcp-linux-amd64 &
sleep 5
curl -s http://localhost:18060/health
### Groq API — free key, no credit card

Get a free Groq API key at https://console.groq.com — no credit card needed. Configure with:

```bash
agent-reach configure groq-key gsk_xxxxx
```

### Local Faster-Whisper — no API, no key, already installed

The Hermes host already has Faster-Whisper + CTranslate2 + FFmpeg in its default Python environment, so ad-hoc transcription is always available with zero setup:

```bash
python3 -c "import faster_whisper, ctranslate2; print(faster_whisper.__version__, ctranslate2.__version__)"
ffmpeg -version | head -1
# Expected (as of 2026-07): faster_whisper 1.2.1, ctranslate2 4.8.0, ffmpeg 6.1.1+
```

Use this path whenever a downstream pipeline needs to transcribe audio/video locally — reel scrapers, podcast imports, downloaded media. Pair with FFmpeg normalization to mono 16 kHz PCM for the fastest, most accurate results.

**When to prefer Faster-Whisper over Groq:**

- Default to Faster-Whisper. It removes per-minute cost, keeps audio on-host, and works offline.
- Reach for Groq only when Faster-Whisper fails to load its model (corrupt cache, GPU/CPU mismatch) and a quick remote fallback is needed — never as the first choice for any new pipeline.

**Pin the model + revision before any production pipeline runs:** Faster-Whisper downloads `~75MB–~3GB` per model on first use and there is no cost gate. Pre-download the approved model into a dedicated cache, record its identifier/revision, and verify the service loads it with outbound network disabled so you can prove there is no remote fallback.

If no pre-auth session exists, the daemon will return `warn` status and you need to call `get_login_qrcode` via the MCP interface to get a QR code for the user to scan.

**Start daemon:** always use `background=true` in the terminal tool. Daemon is long-lived and silent — do not use `notify_on_complete=true`.

### OpenCLI — Chrome extension for Facebook, Instagram

OpenCLI needs a Chrome desktop session with the extension loaded. The extension bridges Chrome's debugger API to the OpenCLI daemon (port 19825) via WebSocket.

**⚠️ KNOWN ISSUE — Chrome won't bind `--remote-debugging-port` with `--user-data-dir=/root/.config/google-chrome` (your real profile):**
- With a clean temp profile: port 9222 binds fine ✅
- With your real Chrome profile (Default): Chrome silently fails to start the DevTools listener — port 9222 never binds ❌
- Adding `--load-extension` compounds this — Chrome may crash silently or not bind at all with the real profile

**Workaround: Two Chrome instances**
1. Chrome instance A — your real profile, NO debug port, user logs in normally
2. Chrome instance B — a fresh clean profile, `--remote-debugging-port=9222`, `--load-extension=/tmp/opencli-ext`

The extension connects to the OpenCLI daemon (which is always running on port 19825). Instance B's clean profile means it binds the debug port successfully. The extension then bridges the daemon to the user's logged-in session from instance A.

```bash
# Install OpenCLI + extension
npm install -g @jackwener/opencli
curl -fsSL https://github.com/jackwener/OpenCLI/releases/download/v1.8.5/opencli-extension-v1.0.20.zip \
  -o /tmp/opencli-ext.zip && unzip -q /tmp/opencli-ext.zip -d /tmp/opencli-ext

# Start daemon (already running on port 19825 — verify with opencli daemon status)
# OpenCLI daemon must be running before the extension can connect

# Instance A — user's real Chrome (no debug port, no extension)
# Start this first so user can log in
export DISPLAY=:1
/opt/google/chrome/chrome --no-sandbox \
  --user-data-dir=/root/.config/google-chrome --start-maximized \
  https://facebook.com

# Instance B — clean profile with extension + debug port (separate session window)
# Start this AFTER user has logged into instance A
export DISPLAY=:1
/opt/google/chrome/chrome --no-sandbox \
  --user-data-dir=/tmp/opencli-chrome \
  --remote-debugging-port=9222 \
  --load-extension=/tmp/opencli-ext \
  --start-maximized \
  about:blank

# Then in Baymax shell (not VNC):
opencli profile list  # should show connected profile
opencli browser facebook --window background open https://facebook.com
```

**If Chrome fails to bind 9222:** Check `ss -tlnp | grep 9222` — if nothing shows, Chrome silently crashed. Try with `--user-data-dir=/tmp/test-chrome` (fresh clean profile) to confirm Chrome itself works, then migrate to the two-instance approach.

**Extension not visible in `chrome://extensions`?** The extension IS loaded (it shows in `--list-extensions` output) but may not appear in the UI if it has no browserAction popup configured. The OpenCLI extension uses `action: { default_popup: "popup.html" }` — it shows as an icon in the toolbar, not a full extension page. Click the OpenCLI icon in Chrome's toolbar to activate the bridge.

### Instagram — OpenCLI required; sessionid cookie via browser bridge

Instagram's `sessionid` is HttpOnly and set via a subrequest during login — `browser_cookie3` cannot capture it from the SQLite blob. **OpenCLI is required.**

The working flow:
1. User logs into Instagram in the VNC Chrome (real profile)
2. OpenCLI bridge picks up the live session — `sessionid` appears in the CDP cookie jar
3. `opencli instagram whoami` → `logged_in: true` confirms auth

**If Instagram shows a profile checkpoint ("Continue as X / Use another profile"):**
- This is a known Instagram web behavior when multiple accounts are remembered
- The correct account (e.g. `alligator.6949242`) may already be logged in but requires a click to confirm
- In the VNC browser, click **"Use another profile"** or **"Continue"** as appropriate
- After clicking through, the `sessionid` cookie becomes available in the CDP bridge
- The `opencli instagram login` command handles this automatically if run in foreground mode — it polls until `sessionid` appears

**Preferred account for scraping:** `alligator.6949242` — confirmed working with full OpenCLI access.

```bash
# Verify Instagram auth
opencli instagram whoami -f yaml
# Expected: logged_in: true, username: alligator.6949242

# Test a search
opencli instagram search "madeat2am" -f yaml
```

**For the persistent-session scraping pattern (reels analysis pipelines, periodic trackers):**

```bash
# Pull N recent posts (mix of media + reels) for an account — JSON for parsing
opencli instagram user <username> --limit <N> -f json \
  --window background --site-session persistent

# Download the media for a reel URL into a staging directory
opencli instagram download <reel-url> --path <staging-dir> -f json \
  --window background --site-session persistent
```

Filter the JSON to `type == "reel"` (or whichever key OpenCLI uses), extract `shortcode` from the post URL, and pass to `download`. See "OpenCLI Instagram command surface" above for the full pattern and the "Replicating the Instagram method to another host" steps.

### Cookie-based auth — use a secondary account

For platforms requiring cookies (Twitter, Reddit, Xueqiu, Xiaohongshu), recommend using a **secondary account** rather than your main. Cookie auth carries two risks: (1) account ban from non-browser API calls, (2) credential exposure if cookies are compromised.

### LinkedIn — import session from Chrome (no VNC login needed)

`mcp-server-linkedin` (the current package; `linkedin-scraper-mcp` is a transitional shim forwarding to it) has an `--import-from-browser` flag that auto-detects a logged-in LinkedIn session in Chrome's Default profile, extracts and validates cookies, and stores a persistent session — all without needing a headed browser or manual login.

```bash
# 1. Import session from Chrome's Default profile (auto-detects li_at, JSESSIONID, etc.)
mcp-server-linkedin --import-from-browser --log-level INFO

# 2. Verify session is valid
mcp-server-linkedin --status
# ✅ Session is valid (profile: /root/.linkedin-mcp/profile)

# 3. Start MCP server (http transport) — USE FULL VENV PATH in background/systemd
/root/.agent-reach-venv/bin/mcp-server-linkedin \
  --transport streamable-http --host 127.0.0.1 --port 3001 --path /mcp

# 4. Register with mcporter (ensure ~/.mcporter/mcporter.json exists first)
/root/.agent-reach-venv/bin/mcporter config add linkedin http://127.0.0.1:3001/mcp

# 5. Keep alive via systemd
cat > /etc/systemd/system/linkedin-mcp.service << 'EOF'
[Unit]
Description=LinkedIn MCP Server
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/root/.agent-reach-venv/bin/mcp-server-linkedin \
  --transport streamable-http --host 127.0.0.1 --port 3001 --path /mcp
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now linkedin-mcp
```

**CRITICAL — venv PATH not inherited in background processes:** When starting the MCP server in the background (terminal background=true or systemd), you MUST use the full absolute path `/root/.agent-reach-venv/bin/mcp-server-linkedin`. Background processes do not inherit the shell's PATH, so `mcp-server-linkedin` alone will fail with "command not found".

**Session is persistent** — stored at `~/.linkedin-mcp/profile`. Survives restarts; only re-import if Chrome cookies are cleared.

**Package name change:** `linkedin-scraper-mcp` (old) → `mcp-server-linkedin` (new). The shim forwards the old entry point. Use `mcp-server-linkedin` directly for all CLI flags.

**Port selection:** use 3001+ to avoid conflicts (Remotion Studio uses 3000). mcporter config add hint says 3000 but any free port works.

**Test:**
```bash
mcporter call linkedin.get_person_profile linkedin_username=satyanadella
```

### Groq API — free key, no credit card

Get a free Groq API key at https://console.groq.com — no credit card needed. Configure with:
```bash
agent-reach configure groq-key gsk_xxxxx
```

---

## OSINT Investigation Patterns (phone numbers + personal names)

Use this playbook when an operator asks to investigate a phone number, identify who is behind a contact, or find all public profiles matching a real name. Most of the workhorse tools are already in this skill — this section sequences them.

### Search-engine fallback chain

SearXNG routinely rate-limits individual engines (Brave "too many requests", DuckDuckGo "CAPTCHA", Google/Startpage "timeout"). **Don't waste cycles retrying SearXNG** when all engines are unresponsive — escalate immediately:

1. **Exa via mcporter** — most reliable broad-recall fallback. Quoted phrases and OR-chains work well for personal-name breadth searches:
   ```bash
   /usr/local/bin/mcporter call 'exa.web_search_exa(query: "\"Full Name\" India", numResults: 10)'
   /usr/local/bin/mcporter call 'exa.web_search_exa(query: "\"Full Name\" linkedin OR github OR facebook", numResults: 10)'
   /usr/local/bin/mcporter call 'exa.web_search_exa(query: "\"Phone Number\" OR \"+91 73xxx xxxxx\"", numResults: 10)'
   ```
   **Path pitfall:** the `mcporter` binary lives at `/usr/local/bin/mcporter` (globally installed via npm), NOT in `~/.agent-reach-venv/bin/`. Calling the venv path silently hangs and times out. Always use the absolute path.

2. **Jina Reader** — `curl -sL "https://r.jina.ai/TARGET_URL"`. Working targets vs. blocked:
   - ✅ LinkedIn profile URLs (`linkedin.com/in/username`, regional subdomains `ae.linkedin.com/...`, `in.linkedin.com/...`)
   - ✅ GitHub user pages and REST API endpoints (`api.github.com/users/X`, `api.github.com/search/users?q=...`)
   - ✅ WhatsApp `wa.me/NUMBER` endpoints — confirms number is registered
   - ✅ Truecaller public profile/locator pages (returns login-wall HTML — useless for data without Indian-SIM auth)
   - ❌ Google / Bing / DuckDuckGo SERP URLs — `403 Forbidden`
   - ❌ Facebook / Instagram profile URLs — login-wall HTML, no bio/posts without auth

3. **Direct platform APIs (no auth needed)**:
   - GitHub: `https://api.github.com/search/users?q=NAME+KEYWORD` — up to 30 candidates with login + profile URL
   - GitHub: `https://api.github.com/users/USERNAME/repos?per_page=100` — repo list with languages and timestamps (excellent for dedup-by-coding-style)
   - GitHub Code Search (`/search/code?q=...`) — **requires auth (401)** unauthenticated
   - GitHub commit-email search — also auth-gated unauthenticated

### Phone-number probes

| Endpoint | What it returns |
|----------|-----------------|
| `https://wa.me/91XXXXXXXXXX` | "Chat on WhatsApp with +91 XXX" page if registered — confirms reachability, **zero PII** beyond the fact |
| `https://www.truecaller.com/search/in/91NUMBER` | Login-walled HTML — useless without Indian-SIM authenticated session |
| Format analysis (`+91 7XXXX XXXXX`) | Indian mobile; leading `7` after country code = Jio / Airtel / Vi post-2010 allocation; carrier + circle need paid lookup or Truecaller app |

**Hard limit:** No public OSINT source ties a phone number to a named individual without either (a) Truecaller app authenticated with Indian SIM, (b) the target publishing their own contact card, or (c) public registries — MCA for company directors, NITI Aayog NGO Darpan for NGOs, IndiaMART/JustDial for business listings (only if the person is a registered director / NGO / business owner).

### Personal-name breadth search

1. **LinkedIn via mcporter** — vanity handles (`subinkbabu`) and slug handles (`subin-k-babu-642b721a3`) both work. Workflow:
   ```bash
   # Step 1: Exa search to harvest candidate slugs
   /usr/local/bin/mcporter call 'exa.web_search_exa(query: "\"Full Name\"", numResults: 10)'
   # Step 2: drill into each candidate
   /usr/local/bin/mcporter call 'linkedin.get_person_profile(linkedin_username: "HANDLE-FROM-EXA")'
   ```
   Common Indian-name searches typically return 5–15 distinct profiles — **same name ≠ same person**. Note location, employer, and education to disambiguate. Profile-URN (`ACoAA...`) is unique per person and is the authoritative dedup key.

2. **GitHub username candidates** — try patterns: `firstname+lastname`, `firstnamelastname89`, `firstnamelastname-dev`, `firstnamelastname-ai`, `SUBINCBABU` (all-caps). The public profile `email` field is usually `null` — don't expect a direct contact email from the API.

3. **Instagram / Facebook / X** — handle guesses (`firstname_lastname`, `firstnamelastname89`, `firstname_lastname_official`) usually resolve to login-wall HTML, not public bios. **Don't burn more than 2–3 attempts per platform** without authentication — the return rate is near zero.

### Reporting back to the operator

When OSINT fails to link a phone number to a name (the common case):
- Report the **working-state facts**: number is reachable on WhatsApp / name has N LinkedIn matches / GitHub candidate is X with Y repos.
- Explicitly state what you couldn't determine: carrier, circle, registered name.
- Name the specific next step that WOULD resolve it (Truecaller-with-Indian-SIM, target's own contact card, MCA registry check).
- Don't fabricate or speculate beyond the evidence.
- Distinguish: "9 LinkedIn profiles match the name" vs. "this phone number belongs to a specific person." The first is a research result; the second is a claim that needs authentication.

## Key Paths

| What | Path |
|---|---|
| Agent Reach venv | `~/.agent-reach-venv/` |
| Agent Reach config | `~/.agent-reach/` |
| Upstream tool repos | `~/.agent-reach/tools/` |
| mcporter system config | `~/.mcporter/mcporter.json` |
| mcporter project config | `~/.agent-reach/tools/xiaohongshu/config/mcporter.json` |
| xiaohongshu binary | `~/.agent-reach/tools/xiaohongshu/xiaohongshu-mcp-linux-amd64` |
| Xiaoyuzhou transcribe script | `~/.agent-reach/tools/xiaoyuzhou/transcribe.sh` |
| mcporter binary (use this absolute path) | `/usr/local/bin/mcporter` |

---

## Attribution

- Upstream: https://github.com/Panniantong/agent-reach
- Install guide: https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
