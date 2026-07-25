#!/usr/bin/env bash
# Dev-VPS prerequisites installer.
#
# This script installs the self-hosted scraping and transcription
# stack on the dev VPS. It is meant to be reviewed before running.
#
# Usage on the dev VPS:
#   sudo bash scripts/setup_dev_vps.sh
#
# What it installs:
#   - System packages via apt: python3.12, python3-pip, python3-venv,
#     ffmpeg, libsm6, libxext6, libxrender1, fonts-liberation, jq
#   - Node.js 22 (via NodeSource), npm, and the `@jackwener/opencli`
#     global package (OpenCLI 1.8.5+)
#   - Google Chrome stable (the Browser Bridge target)
#   - Python packages: faster-whisper, ctranslate2, pydantic, pyyaml,
#     fastapi, uvicorn, sqlalchemy, alembic, psycopg[binary], bcrypt,
#     itsdangerous, httpx, pytest
#
# What it does NOT do:
#   - It does NOT touch the git repository at /root/.hermes/projects/competitors/
#   - It does NOT log in to Instagram. Run scripts/bootstrap_dev_session.sh
#     separately for the interactive login.
#   - It does NOT modify /etc/hosts, /etc/caddy, or the existing nginx
#     configuration.
#   - It does NOT install or start any Docker images for the API/frontend.

set -euo pipefail

log() { printf '\n[setup_dev_vps] %s\n' "$*"; }
fail() { printf '\n[setup_dev_vps][FAIL] %s\n' "$*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || fail "must run as root (use sudo)"

# -- 1. apt system packages ---------------------------------------------
log "1. apt update + base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release jq git build-essential \
  python3.12 python3.12-venv python3.12-dev python3-pip \
  ffmpeg libsm6 libxext6 libxrender1 fonts-liberation

# -- 2. Node 22 via NodeSource ------------------------------------------
if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 22 ]]; then
  log "2. installing Node 22 via NodeSource"
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
else
  log "2. node $(node -v) already present, skipping"
fi

# -- 3. OpenCLI global package ------------------------------------------
if ! command -v opencli >/dev/null 2>&1; then
  log "3. installing @jackwener/opencli globally"
  npm install -g @jackwener/opencli
else
  log "3. opencli $(opencli --version) already present, skipping"
fi

# -- 4. Google Chrome stable --------------------------------------------
if ! command -v google-chrome >/dev/null 2>&1; then
  log "4. installing Google Chrome stable"
  curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list
  apt-get update -y
  apt-get install -y google-chrome-stable
else
  log "4. google-chrome already present, skipping"
fi

# -- 5. Python packages --------------------------------------------------
log "5. creating venv and installing Python deps"
PYBIN="$(command -v python3.12)"
VENV_DIR="/srv/competitors-private/venv"
mkdir -p "$(dirname "$VENV_DIR")"
"$PYBIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools
"$VENV_DIR/bin/pip" install \
  "pydantic>=2.5" "PyYAML>=6.0" \
  "faster-whisper>=1.2" "ctranslate2>=4.6" \
  "fastapi>=0.115" "uvicorn>=0.30" \
  "sqlalchemy>=2.0" "alembic>=1.13" "psycopg[binary]>=3.2" \
  "bcrypt>=4.2" "itsdangerous>=2.2" "httpx>=0.27" "pytest>=8"

# -- 6. Self-test --------------------------------------------------------
log "6. self-test"
for c in node npm opencli google-chrome ffmpeg ffprobe python3.12; do
  command -v "$c" >/dev/null 2>&1 || fail "missing binary: $c"
done
"$VENV_DIR/bin/python" -c "import faster_whisper, ctranslate2, pydantic, yaml, fastapi, sqlalchemy, bcrypt; print('python ok')"
log "opencli version: $(opencli --version)"
log "node version:    $(node -v)"
log "chrome version:  $(google-chrome --version | head -1)"
log "ffmpeg version:  $(ffmpeg -version 2>&1 | head -1)"
log "venv path:       $VENV_DIR"
log "next step:       bash scripts/bootstrap_dev_session.sh  (requires interactive Chrome login)"
