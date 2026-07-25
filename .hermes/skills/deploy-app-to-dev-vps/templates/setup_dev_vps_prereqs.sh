#!/usr/bin/env bash
# Dev-VPS prerequisites installer (template).
#
# This is a TEMPLATE for installing the system-level dependencies
# (Node, npm, OpenCLI, Chrome, FFmpeg, Python venv, ML models)
# required to run a self-hosted scraping + transcription pipeline
# on a clean Ubuntu 24.04 dev VPS.
#
# It is deliberately separate from the deploy helper because:
# - It is run ONCE per host, not on every redeploy.
# - It contains no project-specific paths or secrets.
# - It needs interactive confirmation (apt may prompt) and root.
#
# Customize before running:
# - Replace /srv/<name>-private/venv with your venv path.
# - Add any project-specific apt packages below.
# - Adjust the OpenCLI global install line if your project uses a
#   different CLI binary.

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

# -- 3. CLI global package (e.g. OpenCLI) --------------------------------
if ! command -v opencli >/dev/null 2>&1; then
  log "3. installing OpenCLI globally"
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

# -- 5. Python venv with ML + API deps ----------------------------------
log "5. creating venv and installing Python deps"
PYBIN="$(command -v python3.12)"
VENV_DIR="${VENV_DIR:-/srv/<name>-private/venv}"
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
"$VENV_DIR/bin/python" -c \
  "import faster_whisper, ctranslate2, pydantic, yaml, fastapi, sqlalchemy, bcrypt; print('python ok')"
log "opencli version: $(opencli --version)"
log "node version:    $(node -v)"
log "chrome version:  $(google-chrome --version | head -1)"
log "ffmpeg version:  $(ffmpeg -version 2>&1 | head -1)"
log "venv path:       $VENV_DIR"
log "next step:       run the project-specific bootstrap script (e.g. scripts/bootstrap_dev_session.sh) for any interactive login step"
