# Agent Reach — Session Reference

## Installed channels (June 30, 2026 — 14/15 live)

| Channel | Backend | Status | Auth needed? |
|---|---|---|---|
| github | gh CLI | ✅ ok | No |
| youtube | yt-dlp | ✅ ok | No |
| v2ex | V2EX API (public) | ✅ ok | No |
| rss | feedparser | ✅ ok | No |
| exa_search | Exa via mcporter | ✅ ok | No |
| web | Jina Reader | ✅ ok | No |
| bilibili | bili-cli | ✅ ok | No |
| xiaohongshu | xiaohongshu-mcp (mcporter) | ✅ ok | Pre-authenticated (ai-report account) |
| xiaoyuzhou | groq-whisper | ✅ ok | Groq key configured |
| twitter | twitter-cli | ✅ ok | Cookie auth (via VNC + rookiepy) |
| reddit | rdt-cli / OpenCLI | ✅ ok | Cookie auth (via VNC + rookiepy) |
| linkedin | linkedin-scraper-mcp (MCP port 3001) | ✅ ok | Session imported from Chrome Default |
| facebook | OpenCLI | ✅ ok | CDP browser bridge (user: 61591216150542) |
| instagram | OpenCLI | ✅ ok | CDP browser bridge (user: alligator.6949242) |
| xueqiu | OpenCLI | ⚠️ warn | Cookie auth needed — user logs into VNC Chrome |

## Exact commands used during install

### 1. Core install (venv approach — no pipx on host)
```bash
python3 -m venv ~/.agent-reach-venv
source ~/.agent-reach-venv/bin/activate
pip install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto
```

### 2. Groq API key (Xiaoyuzhou podcast transcription)
```bash
source ~/.agent-reach-venv/bin/activate
agent-reach configure groq-key YOUR_GROQ_KEY_HERE
```

### 3. LinkedIn MCP install
```bash
source ~/.agent-reach-venv/bin/activate
pip install linkedin-scraper-mcp
# Note: linkedin-scraper-mcp was renamed to mcp-server-linkedin
# Binary: /root/.agent-reach-venv/bin/linkedin-scraper-mcp
```

### 3. LinkedIn MCP (fully operational — June 30, 2026)
```bash
# Import session from Chrome's Default profile (auto-detects li_at, JSESSIONID etc.)
source ~/.agent-reach-venv/bin/activate
/root/.agent-reach-venv/bin/mcp-server-linkedin --import-from-browser --log-level INFO
# Expected: ✅ Imported and validated LinkedIn session into /root/.linkedin-mcp/profile

# Verify session
/root/.agent-reach-venv/bin/mcp-server-linkedin --status
# Expected: ✅ Session is valid (profile: /root/.linkedin-mcp/profile)

# Start MCP server (background, long-lived) — USE FULL ABSOLUTE PATH
terminal(background=true,
  command="/root/.agent-reach-venv/bin/mcp-server-linkedin --transport streamable-http --host 127.0.0.1 --port 3001 --path /mcp")

# OR via systemd (recommended for production):
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

# Wire into mcporter — ensure ~/.mcporter/mcporter.json exists first
mkdir -p /root/.mcporter
python3 -c "import json; f='/root/.mcporter/mcporter.json'; open(f,'a').close() if True else None"
/root/.agent-reach-venv/bin/mcporter config add linkedin http://127.0.0.1:3001/mcp

# Verify
/root/.agent-reach-venv/bin/mcporter list linkedin --schema
/root/.agent-reach-venv/bin/mcporter call linkedin.get_person_profile linkedin_username=satyanadella
```

### 5. xiaohongshu-mcp (server-side, self-contained browser + QR)
```bash
# Detect arch
uname -m  # returns x86_64 on this host

# Download binary
mkdir -p ~/.agent-reach/tools/xiaohongshu
curl -fsSL https://github.com/xpzouying/xiaohongshu-mcp/releases/download/v2026.06.12.1403-5c43e3d/xiaohongshu-mcp-linux-amd64.tar.gz -o xhs.tar.gz
tar -xzf xhs.tar.gz -C ~/.agent-reach/tools/xiaohongshu/

# Start daemon (background, long-lived)
terminal(background=true, command="cd ~/.agent-reach/tools/xiaohongshu && ./xiaohongshu-mcp-linux-amd64")

# Health check
curl -s http://localhost:18060/health
# Expected: {"success":true,"data":{"account":"ai-report","service":"xiaohongshu-mcp","status":"healthy",...}}

# Wire into mcporter
mcporter config add xiaohongshu http://localhost:18060/mcp
```

### 6. Fix mcporter config location (known bug — mcporter writes to wrong file)
```bash
mkdir -p /root/.mcporter
cat > /root/.mcporter/mcporter.json << 'EOF'
{
  "mcpServers": {
    "exa": { "url": "https://mcp.exa.ai/mcp" },
    "xiaohongshu": { "url": "http://localhost:18060/mcp" }
  }
}
EOF
```

### 6. Verify Exa search works
```bash
mcporter call 'exa.web_search_exa(query: "MadeAt2Am social media", numResults: 5)'
```

### 7. Final doctor check
```bash
source ~/.agent-reach-venv/bin/activate && agent-reach doctor
```

## VNC Browser Session — Cookie Extraction on Server

**Problem:** Server has no desktop Chrome. Twitter, Reddit, Xueqiu need browser login. Solution: password-protected VNC web session the user opens in their browser, logs in, and Baymax extracts cookies.

**Stack:** TigerVNC → websockify → nginx (HTTPS + HTTP Basic Auth)

**Install packages:**
```bash
apt-get install -y tigervnc-standalone-server websockify novnc nginx apache2-utils
```

**SSL cert:**
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /root/.vnc/ssl.key -out /root/.vnc/ssl.crt \
  -subj "/CN=cyberslide.terrybot.top"
```

**VNC password (prompt user for their chosen password):**
```bash
mkdir -p ~/.vnc
echo "USER_VNC_PASSWORD" | tigervncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd
```

**HTTP Basic Auth (prompt user for username + password):**
```bash
htpasswd -bc /root/.vnc/.htpasswd chris USER_WEB_PASSWORD
# CRITICAL: copy to /etc/nginx/.htpasswd — nginx www-data cannot read /root/.vnc/
cp /root/.vnc/.htpasswd /etc/nginx/.htpasswd && chmod 644 /etc/nginx/.htpasswd
```

**Start TigerVNC (background, long-lived):**
```bash
terminal(background=true, command="tigervncserver :1 -fg -xstartup /usr/bin/startxfce4")
```

**Start websockify (background, long-lived):**
```bash
terminal(background=true, command="websockify --web /usr/share/novnc --cert /root/.vnc/ssl.crt 6080 localhost:5901")
```

**nginx config — write to `/etc/nginx/sites-available/vnc`:**
```nginx
server {
    listen 443 ssl;
    server_name YOUR_HOSTNAME;
    ssl_certificate /root/.vnc/ssl.crt;
    ssl_certificate_key /root/.vnc/ssl.key;
    auth_basic "VNC Desktop — Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    location / {
        proxy_pass http://localhost:6080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```
```bash
ln -sf /etc/nginx/sites-available/vnc /etc/nginx/sites-enabled/vnc
nginx -t && nginx -s reload
```

**Launch Chrome in VNC display (USE google-chrome .deb — NOT snap chromium):**
```bash
# Install Google Chrome if needed
curl -fsSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o /tmp/chrome.deb
apt-get install -y /tmp/chrome.deb

# Launch (background, long-lived)
terminal(background=true, command="export DISPLAY=:1 && google-chrome --no-sandbox --start-maximized --window-size=1920,1080 https://twitter.com")
```

**Extract cookies (from the VNC session, user logged into Twitter + Reddit):**
```bash
# Install rookiepy first — required for Linux Chrome cookie decryption
source ~/.agent-reach-venv/bin/activate
pip install rookiepy

# Auto-extract all platform cookies from Chrome profile
agent-reach configure --from-browser chrome
# Expected: ✅ Twitter/X: auth_token + ct0  ✅ Reddit: reddit_session configured
```

**User URL:** `https://cyberslide.terrybot.top/vnc.html` (or your hostname)
- Basic auth: username=`chris`, password=`USER_WEB_PASSWORD`
- User accepts self-signed SSL cert warning in browser

**Snap Chromium is unusable for VNC:** Snap Chromium forces `--ozone-platform=headless` internally. It silently runs headless instead of rendering to the VNC display. Always use the `.deb` Google Chrome from Google's repo.

**500 error after starting = htpasswd location:** nginx returns 500 because `/root/.vnc/.htpasswd` is root-owned with 600. Fix: `cp /root/.vnc/.htpasswd /etc/nginx/.htpasswd && chmod 644 /etc/nginx/.htpasswd`

## Credentials status (as of June 30, 2026)

| Credential | Status | How to configure |
|---|---|---|
| Twitter auth token | ✅ Configured | `agent-reach configure --from-browser chrome` (via VNC + rookiepy) |
| Reddit session cookie | ✅ Configured | `agent-reach configure --from-browser chrome` (via VNC + rookiepy) |
| LinkedIn session | ✅ Configured | `mcp-server-linkedin --import-from-browser` — imports from Chrome Default profile |
| Facebook cookies | ✅ Configured | OpenCLI CDP browser bridge (logged in, user_id: 61591216150542) |
| Instagram session | ✅ Configured | OpenCLI CDP browser bridge (logged in, user: alligator.6949242) |
| Xueqiu cookies | ⚠️ Needed | User logs into xueqiu.com via VNC Chrome → OpenCLI bridge picks up session |
| Groq API key | ✅ Configured | `agent-reach configure groq-key YOUR_GROQ_KEY_HERE` |
