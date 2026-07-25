---
name: headless-vps-scraping-toolchain
description: Install and operate a self-hosted scraping + transcription toolchain on a headless Linux VPS (Ubuntu 24.04 image with no DISPLAY). Covers apt + NodeSource + Chrome signing-key rotation, Faster-Whisper + CTranslate2 + FFmpeg venv, the OpenCLI Browser Bridge and its headless-login fallback ladder, the Instagram no-third-party-OAuth pattern, and the cookie-paste auth UX with strict security guardrails. Use when you need to provision a new VPS for scraping/automation work, install OpenCLI on a fresh image, recover from BROWSER_CONNECT errors, or build an in-dashboard reauth flow for a service that does not expose OAuth.
version: 1.0.0
author: Baymax (Baymax Agent)
license: MIT
metadata:
  hermes:
    tags: [vps, devops, scraping, opencli, instagram, headless, install]
    related_skills: [vps-container-deploy, deploy-app-to-dev-vps, docker-network-troubleshooting, secure-web-dashboard]
---

# Headless VPS scraping toolchain

Class-level skill for self-hosted scraping + transcription on a Linux VPS
that starts as a clean image (Ubuntu 24.04 LTS, no desktop, no Chrome,
no Node, no FFmpeg). The pattern is: install the toolchain with apt +
NodeSource + Python venv, drive OpenCLI from there, and fall back to
cookie-paste for any auth that requires a real Chrome.

## When to use

- Provisioning a fresh VPS for scraping / data-collection work
- Installing OpenCLI + Chrome + FFmpeg + Faster-Whisper on a new image
- Diagnosing `BROWSER_CONNECT` or `Browser Bridge not connected` errors
- Designing an in-dashboard reauth flow for Instagram / TikTok / X
  (none of which expose third-party OAuth for desktop/web apps)
- Building a "log in via the dashboard" UX without impersonating
  the upstream service

**Do not use for:** containerised deploys (use `vps-container-deploy`),
Hetzner MTU work (use `docker-network-troubleshooting`), or installing
TTS (use `kokoro-tts`).

## Iron Rule

```
PREFLIGHT MUST RUN ON THE TARGET MACHINE
```

Running `command -v opencli` on the orchestrator proves the orchestrator
has OpenCLI. It says nothing about the VPS you are about to deploy to.
A fresh VPS image typically has none of: Node, npm, Chrome, FFmpeg,
ffprobe, OpenCLI, Python 3.12. The preflight that found OpenCLI on
your local host is **not** the preflight for the deploy.

Always run a per-machine preflight on the actual target before claiming
the deploy is ready.

## The install sequence

```bash
# 0. Verify preflight on the TARGET (not the orchestrator)
ssh dev-vps 'for c in node npm opencli google-chrome ffmpeg ffprobe \
  python3.12; do
    printf "%-15s %s\n" "$c" "$(command -v $c 2>&1)"
  done'

# 1. apt basics
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release jq git \
  build-essential python3.12 python3.12-venv python3.12-dev \
  ffmpeg

# 2. Node 22 via NodeSource
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

# 3. OpenCLI (and any CLI you need)
npm install -g @jackwener/opencli

# 4. Chrome — KEY ROTATION GOTCHA
# Canonical key from dl.google.com/linux/linux_signing_key.pub has both
# old (7721F63B) and new (EBF29A6585A1C5B8) signing keys. apt needs the
# new key. If `apt-get update` complains about FD533C07C264648F or
# EBF29A6585A1C5B8, the signing key you have is stale.

curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
  | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
  https://dl.google.com/linux/chrome/deb/ stable main" \
  > /etc/apt/sources.list.d/google-chrome.list
apt-get update -y
apt-get install -y google-chrome-stable

# 5. Python venv with the transcription stack
python3.12 -m venv /srv/competitors-private/venv
/srv/competitors-private/venv/bin/pip install -U pip wheel setuptools
/srv/competitors-private/venv/bin/pip install \
  "pydantic>=2.5" "PyYAML>=6" \
  "faster-whisper>=1.2" "ctranslate2>=4.0" \
  "fastapi>=0.115" "uvicorn>=0.30" \
  "sqlalchemy>=2.0" "psycopg[binary]>=3.2" \
  "bcrypt>=4.2" "itsdangerous>=2.2"

# 6. Register the unix `whoami` binary as an OpenCLI external command.
#    `opencli whoami` is NOT a built-in subcommand on a fresh OpenCLI
#    install — the verify call needs this register step once per host.
opencli external register whoami /usr/bin/whoami
# Verify it works:
opencli whoami   # should now return {"ok": true, "result": {"username": "<unix-user>"}}
```

Verify each step on the target before moving on. If `command -v opencli`
returns nothing on the dev VPS after running on the orchestrator, the
install did not propagate — re-run on the target.

## The four headless-login paths

When the OpenCLI Browser Bridge can't connect (no DISPLAY, no X11,
no logged-in user), the operator needs an alternative auth path.
Pick one based on the threat model and operator friction:

| Path | Operator friction | Account-ban risk | Best for |
|---|---|---|---|
| 1. Transferred pre-authenticated Chrome profile | One-time setup | Low (same machine, no upload) | Production baseline |
| 2. SSH X11 forwarding (`ssh -X dev-vps`) | One-time login | Low | One-off / debugging |
| 3. VNC + manual browser click | High | Low | When SSH X doesn't work |
| 4. Cookie paste from a Chrome elsewhere | None after first login | **Moderate** (paste into web form) | Dashboard UX fallback |

**Order of preference:** 1 > 2 > 3 > 4. Path 4 is acceptable only when
the threat model is documented and the cookie set is small
(`sessionid` + `ds_user_id` for Instagram, for example).

## The Instagram pattern (no third-party OAuth)

Instagram does not expose third-party OAuth for desktop/web apps. There
is no "log in via Instagram" button you can build that doesn't
impersonate `instagram.com`. The only safe in-dashboard reauth is a
cookie paste from a Chrome where the operator logged in to Instagram
directly.

The required cookie set for Instagram:
- `sessionid` — 32-512 chars, base64-ish (`^[A-Za-z0-9%._\-]{32,512}$`)
- `ds_user_id` — 6-20 digits (`^[0-9]{6,20}$`)

Extraction recipe (DevTools → Application → Cookies → `.instagram.com`):

1. Open `https://www.instagram.com` in a Chrome where the operator is
   logged in as the **approved secondary** account (not the primary).
2. DevTools → Application → Cookies → `https://www.instagram.com`.
3. Copy `sessionid` (Value column) and `ds_user_id`.
4. Paste into the dashboard form. Click Authenticate.
5. The dashboard writes the cookies to the OpenCLI site-session file
   (`site-session.json`) under the profile directory, mode 0600,
   owned by the scraper service account.
6. The dashboard invokes `opencli instagram whoami` to verify.
7. If `whoami` returns the approved account, the auth state flips to
   `ok`. If it returns a different account, the state flips to
   `wrong-account` and the operator must log out of Instagram in the
   other Chrome first.

## The cookie-paste API contract

The API has exactly four endpoints and they are deliberately minimal:

```
GET  /api/auth/instagram/status        -> current whoami state
POST /api/auth/instagram/start         -> 10-min one-time state token
POST /api/auth/instagram/complete      -> state + sessionid + ds_user_id
POST /api/auth/instagram/logout        -> clear the cookies file
```

Pin them with tests for:
- state token single-use, TTL-bound, replay-rejected
- cookie format validation (regex) before any subprocess call
- write-to-profile refuses symlinks (chase-symlink is the textbook
  container-escape path; refuse the operation)
- file mode 0600 after write
- no cookie values in any response, in any log line
- post-write `whoami` round-trip — if it doesn't return `ok`, fail
  with a clear BootstrapError

## Pitfalls

### 1. `command -v opencli` is not enough — verify it runs

After `npm install -g @jackwener/opencli`, run `opencli --version` on
the target. If you ran the install on the orchestrator and only
verified on the orchestrator, the dev VPS may have nothing.

### 2. Chrome signing-key rotation

If apt-get update fails with `NO_PUBKEY FD533C07C264648F` or
`NO_PUBKEY EBF29A6585A1C5B8`, your keyring has the **old** key.
Re-fetch from `dl.google.com/linux/linux_signing_key.pub` (this file
contains both keys, including the current one) and `gpg --dearmor` it
into `/usr/share/keyrings/google-chrome.gpg`. Don't bother with
keys.openpgp.org — it doesn't have the Chrome signing keys.

### 3. OpenCLI Browser Bridge needs a real Chrome

The Browser Bridge is a Chrome extension. With no Chrome running and
no display, `opencli instagram login` fails with `BROWSER_CONNECT`.
The CLI has a `--window background` mode that runs Chrome headless
but **also** requires the extension to be connected to a real
running Chrome with the same profile directory.

### 4. The site-session file has a fixed name

OpenCLI's persistent site-session writes to `<profile>/site-session.json`
with a known JSON shape. If you write the file with a different name
or a different shape, OpenCLI won't pick it up. The shape is:

```json
{
  "cookies": [
    {
      "name": "sessionid",
      "value": "<base64-ish>",
      "domain": ".instagram.com",
      "path": "/",
      "expires": -1,
      "httpOnly": true,
      "secure": true,
      "sameSite": "Lax"
    },
    {
      "name": "ds_user_id",
      "value": "<digits>",
      "domain": ".instagram.com",
      ...
    }
  ],
  "origins": [
    { "origin": "https://www.instagram.com", "localStorage": {} }
  ]
}
```

### 5. The account-ban risk of paste-cookie flows is real

Instagram's anti-scraping policy treats pasted `sessionid` cookies
suspicious. The path is fine when:
- you only use the **approved secondary** account, not the operator's
  primary
- you write the cookies to the OpenCLI site-session only (not to
  logs, not to a database, not to error responses)
- you don't share the cookies across machines
- you don't run the same `sessionid` from many parallel sessions

If any of those constraints is violated, the path is no longer fine.

### 6. `--site-session persistent` is not the default

`opencli instagram whoami` runs without a persistent site-session by
default. Add `--site-session persistent` (and a `--site-session-dir`
pointing at the profile) or every `whoami` invocation creates a fresh
ephemeral session that won't have your pasted cookies.

### 7. `opencli whoami` is an external CLI, not a built-in subcommand

On a fresh OpenCLI install (verified with OpenCLI 1.8.6 on Ubuntu 24.04),
`opencli whoami` errors with:

```
error: unknown command 'whoami'
  Tip: 'whoami' exists on your PATH. Use 'opencli external register whoami'
  to add it as an external CLI.
```

The unix `whoami` binary (`/usr/bin/whoami`) IS on `$PATH` after the
Node + apt steps above, but OpenCLI doesn't auto-wire external binaries.
The verify call (`bootstrap_session.verify_bootstrap()` and friends)
expects `opencli whoami` to work — it must be registered once per host:

```bash
opencli external register whoami /usr/bin/whoami
# Now: opencli whoami  →  {"ok": true, "result": {"username": "<unix-user>"}}
```

The `external register` step is in the install sequence at step 6 (added
2026-07-25). If you skip it, `bootstrap_session.probe_whoami()` returns
a `BootstrapError` with the "unknown command" message and the dashboard
auth banner shows the `error` state forever.

## Verification

After install, on the target machine:

```bash
ssh dev-vps '
  echo "== tool inventory =="
  for c in node npm opencli google-chrome ffmpeg ffprobe python3.12; do
    printf "  %-15s %s\n" "$c" "$(command -v $c 2>&1)"
  done
  echo "== Whisper smoke =="
  /srv/competitors-private/venv/bin/python -c "
  from faster_whisper import WhisperModel
  m = WhisperModel(\"tiny\", device=\"cpu\", compute_type=\"int8\")
  segs, info = m.transcribe(\"/dev/null\", vad_filter=True)
  print(f\"language={info.language} prob={info.language_probability:.3f} segments=0\")
  "
'
```

A clean install reports all six tools present and the Whisper smoke
test returns `language=en prob=0.000.. segments=0` (empty audio is
expected — the test is about model load + inference path, not
transcription quality).

## When stuck

| Symptom | Likely cause | Fix |
|---|---|---|
| `command not found: opencli` on dev-vps | You installed on the orchestrator, not the target | Re-run the install on the dev VPS |
| `NO_PUBKEY FD533C07C264648F` or `EBF29A6585A1C5B8` | Stale Chrome signing key | Re-fetch from `dl.google.com/linux/linux_signing_key.pub` |
| `BROWSER_CONNECT` on `opencli instagram login` | No Chrome session with the extension | Use one of the four headless paths |
| `opencli whoami` errors with `unknown command 'whoami'` | External CLI never registered on this host | `opencli external register whoami /usr/bin/whoami` (one-time, per host) |
| `opencli whoami` returns nothing | Different `whoami` payload shape than expected | Read the actual JSON, handle both `{"username": "..."}` and `{"result": {"username": "..."}}` |
| Cookie paste writes file but `whoami` still says no-profile | Wrong file name — must be `site-session.json`, not `cookies.json` | Rename to `site-session.json` |
| Cookie paste writes file but `whoami` says wrong-account | Operator was logged in to the wrong Chrome profile | Log out, log in to approved account, redo the paste |
| Paste succeeds but Instagram returns `"token invalid or already consumed"` | Cookie consumed by another browser session, OR fingerprint mismatch (dev VPS is a Hetzner datacenter IP) | See `references/instagram-cookie-paste-failures.md` — close other Chrome tabs on `instagram.com`, re-extract within 5 min, or switch to Path 1 (transferred Chrome profile + persistent site-session) |
| Paste succeeds but Instagram returns `"checkpoint_required"` or `"unrecognized_device"` | Device fingerprint mismatch — the Hetzner IP and headless Chrome UA don't match the operator's desktop | Same reference — Path 1 is the only reliable fix; Path 6 (mobile-web cookies from `m.instagram.com`) sometimes works as an interim |
| Cookie paste keeps failing across multiple attempts on the same account | The secondary account is being burned by repeated paste cycles | Stop pasting. Switch to Path 1, or burn this account and create a fresh one from the dev VPS's own IP |

## References

- `references/opencli-instagram-recipe.md` — concrete install + paste
  recipe with file paths and exact commands.
- `references/in-dashboard-instagram-banner.md` — React-side companion
  for the `InstagramAuthBanner` component: 8-test TDD list, state
  machine, typed wrapper, the `getByText` collision pitfall, and
  dashboard-mounting pattern. Read alongside `opencli-instagram-recipe.md`
  when building or revising the in-dashboard login UX.
- `references/instagram-cookie-paste-failures.md` — troubleshooting
  for the four Instagram-specific root causes behind `whoami`
  failure despite a successful paste (`token invalid or already
  consumed`, `checkpoint_required`, fingerprint mismatch, expired
  cookies), the Instagram-specific error-string mapping, the
  ranking of all six auth paths for Instagram (vs the four in this
  SKILL.md's general fallback ladder), and the Path 1 transferred-
  Chrome-profile bootstrap recipe for when paste is too fragile.
