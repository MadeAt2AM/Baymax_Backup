# Dev-VPS install script — when the VPS has nothing

When the dev VPS is a clean Ubuntu 24.04 image (or any minimal image),
the Docker-based deploy path can't start because the runtime stack
isn't there. This file captures the install pattern from the
`competitors` project (VPS 147.79.18.32, July 2026).

## Trigger

The local-host preflight says OpenCLI / Node / Chrome / FFmpeg /
Python 3.12 are installed on the Hermes host, but `ssh dev-vps 'for c
in opencli node npm google-chrome ffmpeg ffprobe python3.12; do
command -v $c; done'` returns mostly empty. The dev VPS has Docker
and curl but none of the runtime stack the plan assumes.

## Symptom

- `opencli: command not found` on the VPS
- `node: command not found` on the VPS
- `python3.12: command not found` (only `python3` exists, version 3.10)
- No Chrome anywhere
- `ffmpeg: command not found`

## The fix — `setup_dev_vps.sh`

A single reviewable bash script, idempotent (every step checks
`command -v` first), pinned versions. The `competitors` project at
`/root/.hermes/projects/competitors/scripts/setup_dev_vps.sh` is the
worked example.

### Section 1 — apt system packages

```bash
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release jq git build-essential \
  python3.12 python3.12-venv python3.12-dev python3-pip \
  ffmpeg libsm6 libxext6 libxrender1 fonts-liberation
```

`fonts-liberation`, `libsm6`, `libxext6`, `libxrender1` are required
by Chrome and by Faster-Whisper's `av` library. Without them Chrome
won't start and Whisper will fail on audio decode.

### Section 2 — Node 22 via NodeSource

```bash
if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 22 ]]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi
```

The `command -v` + version check makes the section idempotent. If
node 22+ is already there (e.g. from a previous run), skip.

### Section 3 — OpenCLI global package

```bash
npm install -g @jackwener/opencli
```

Documented OpenCLI install path. Pulls the latest from npm; if you
need version pinning, use `npm install -g @jackwener/opencli@1.8.5`.

### Section 4 — Google Chrome stable

```bash
curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
  | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" \
  > /etc/apt/sources.list.d/google-chrome.list
apt-get update -y
apt-get install -y google-chrome-stable
```

**Pitfall:** GPG keys for third-party apt sources rotate every ~2
years. A preflight that copies a stale key from another machine
fails with `NO_PUBKEY` on `apt-get update`. Always download the key
fresh from the canonical URL at install time. Same applies to
NodeSource, Docker, etc.

### Section 5 — Python venv at `/srv/<project>-private/venv`

```bash
VENV="/srv/<project>-private/venv"
mkdir -p "$(dirname "$VENV")"
python3.12 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip wheel setuptools
"$VENV/bin/pip" install \
  "pydantic>=2.5" "PyYAML>=6.0" \
  "faster-whisper>=1.2" "ctranslate2>=4.6" \
  "fastapi>=0.115" "uvicorn>=0.30" \
  "sqlalchemy>=2.0" "alembic>=1.13" "psycopg[binary]>=3.2" \
  "bcrypt>=4.2" "itsdangerous>=2.2" "httpx>=0.27" "pytest>=8"
```

Putting the venv under `/srv/<project>-private/` instead of in a
user home means the dev VPS can later run multiple projects on the
same machine without colliding. Mode 0700 on the parent dir if
multiple users should not see each other's venvs.

### Section 6 — Self-test (mandatory)

```bash
for c in node npm opencli google-chrome ffmpeg ffprobe python3.12; do
  command -v "$c" >/dev/null 2>&1 || { echo "missing: $c"; exit 1; }
done
"$VENV/bin/python" -c "import faster_whisper, ctranslate2, pydantic, yaml; print('python ok')"
opencli --version
google-chrome --version | head -1
ffmpeg -version 2>&1 | head -1
```

The self-test is what catches the GPG key issue (apt install
silently succeeds, but `google-chrome --version` reports "command not
found" if the install actually failed). **Always run the self-test.**

## What NOT to do

- **Don't `apt-get install nodejs` from the default Ubuntu repos.**
  Ubuntu 24.04 ships nodejs 18.x, which is too old for OpenCLI 1.8.
  Use NodeSource.
- **Don't `npm i opencli`.** That's a different package. OpenCLI is
  `@jackwener/opencli` and lives at
  https://www.npmjs.com/package/@jackwener/opencli.
- **Don't copy Chrome from the Hermes host.** The dev VPS gets
  Chrome via apt; copy-pasting Chrome binaries doesn't update
  `apt-get` and creates a 2-week-old security hole.
- **Don't install `python3-pip` only.** On Ubuntu 24.04 the
  `python3.12-venv` package is separate from `python3-pip` and
  `python3.12-dev`. All three are required.

## Verification

After running `setup_dev_vps.sh`, ssh to the VPS and run:

```bash
ssh dev-vps 'bash -lc "
for c in node npm opencli google-chrome ffmpeg ffprobe python3.12; do
  printf \"%-15s %s\\n\" \"$c\" \"\$(command -v $c)\"
done
/srv/<project>-private/venv/bin/python -c \
  \"from faster_whisper import WhisperModel; \
    m = WhisperModel(\\\"tiny\\\", device=\\\"cpu\\\", compute_type=\\\"int8\\\"); \
    print(\\\"whisper ok\\\")\"
"'
```

The whisper load test is the real verification — it triggers the
model download, exercises FFmpeg via `av`, and proves the full
transcription path works end-to-end on the dev VPS. A 1-second
synthesized tone should transcribe in ~500ms with 0 segments and
`language=en prob≈0.3`.

## Worked example

`/root/.hermes/projects/competitors/scripts/setup_dev_vps.sh` —
executed on 147.79.18.32 (Hetzner Helsinki, Ubuntu 24.04) on
2026-07-24. Result: all 6 binaries present, whisper tiny loaded in
2.5s, real transcription 446ms for a 1s fixture, language detection
`en` prob 0.268, 0 segments.