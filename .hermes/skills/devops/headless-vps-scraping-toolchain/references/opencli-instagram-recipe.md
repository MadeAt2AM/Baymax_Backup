# OpenCLI + Instagram on a headless dev VPS — concrete recipe

This is the worked recipe from the competitors project. Every command
runs on the **target** (dev VPS), not the orchestrator.

## Preflight on the target

```bash
ssh dev-vps 'bash -lc "
  for c in node npm opencli google-chrome ffmpeg ffprobe python3.12; do
    printf \"%-15s %s\n\" \"\$c\" \"\$(command -v \$c 2>&1)\"
  done
"'
```

A fresh Ubuntu 24.04 image returns `command not found` for every one of
those. That is the signal to install. Don't trust a preflight that ran
on a different machine.

## Install

```bash
ssh dev-vps 'bash -lc "
  set -e
  apt-get update -y
  apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg lsb-release jq git \
    build-essential python3.12 python3.12-venv python3.12-dev \
    ffmpeg
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
  npm install -g @jackwener/opencli
  curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \\
    | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
  echo \"deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \\
    https://dl.google.com/linux/chrome/deb/ stable main\" \\
    > /etc/apt/sources.list.d/google-chrome.list
  apt-get update -y
  apt-get install -y google-chrome-stable
  python3.12 -m venv /srv/competitors-private/venv
  /srv/competitors-private/venv/bin/pip install -U pip wheel setuptools
  /srv/competitors-private/venv/bin/pip install \\
    \"pydantic>=2.5\" \"PyYAML>=6\" \\
    \"faster-whisper>=1.2\" \"ctranslate2>=4.0\" \\
    \"fastapi>=0.115\" \"uvicorn>=0.30\" \\
    \"sqlalchemy>=2.0\" \"psycopg[binary]>=3.2\" \\
    \"bcrypt>=4.2\" \"itsdangerous>=2.2\"
"'
```

## Profile directory

```
/srv/competitors-private/
├── opencli-profile/
│   └── site-session.json     ← cookies file (mode 0600)
└── venv/
    └── bin/python
```

The profile directory is created on first `ensure_profile_dir()` call.
The bootstrap script refuses to follow a symlink at any step.

## Site-session JSON shape

```json
{
  "cookies": [
    {
      "name": "sessionid",
      "value": "<32-512 chars base64-ish>",
      "domain": ".instagram.com",
      "path": "/",
      "expires": -1,
      "httpOnly": true,
      "secure": true,
      "sameSite": "Lax"
    },
    {
      "name": "ds_user_id",
      "value": "<6-20 digits>",
      "domain": ".instagram.com",
      "path": "/",
      "expires": -1,
      "httpOnly": false,
      "secure": true,
      "sameSite": "Lax"
    }
  ],
  "origins": [
    { "origin": "https://www.instagram.com", "localStorage": {} }
  ]
}
```

Atomic write: temp file → `os.replace(target, temp)` → `os.chmod(0o600)`.

## whoami parsing

OpenCLI's `whoami` payload has at least two observed shapes:

```json
{"ok": true, "result": {"username": "mallu.wave"}}
```

and

```json
{"username": "mallu.wave"}
```

The `probe_whoami` function handles both. `verify_bootstrap` (the
strict version used in the pre-deploy gate) raises if the account
doesn't match the approved one.

## The four fallback paths

### Path 1 — transferred Chrome profile

```bash
# On the source machine where the operator is logged in to mallu.wave:
scp -r /path/to/Chrome\ Profile/ dev-vps:/srv/competitors-private/chrome-profile/

# On the dev VPS:
opencli instagram whoami --site-session-dir /srv/competitors-private/opencli-profile/
```

### Path 2 — SSH X-forward

```bash
ssh -X dev-vps
google-chrome &     # opens on the local display
# Click the OpenCLI Browser Bridge extension icon, link to the CLI
opencli instagram login --window foreground
```

### Path 3 — VNC

Heavy. Skip unless X-forward is broken.

### Path 4 — cookie paste via the dashboard

The dashboard exposes four endpoints:

```
GET  /api/auth/instagram/status
POST /api/auth/instagram/start
POST /api/auth/instagram/complete
POST /api/auth/instagram/logout
```

The frontend banner shows the current `whoami` state. When state is
not `ok`, it surfaces DevTools extraction instructions for `sessionid`
and `ds_user_id`. The paste form posts to `/complete`, which writes
`site-session.json` and re-runs `whoami` to verify.

## Verification

```bash
ssh dev-vps 'bash -lc "
  opencli --version
  opencli instagram --help
  opencli instagram whoami --site-session persistent
"'
```

A clean install returns:
- `1.8.6`
- a list of subcommands including `login`, `whoami`, `user`, `reel`
- `BROWSER_CONNECT` (this is expected — the Browser Bridge isn't
  connected yet; the dashboard will surface this state and offer the
  paste fallback)

## Reset

```bash
ssh dev-vps 'rm -f /srv/competitors-private/opencli-profile/site-session.json'
```

This clears the cookies file. The next `whoami` call will report
`no-profile` and the dashboard banner will offer the paste flow.
