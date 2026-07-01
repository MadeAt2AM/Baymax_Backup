#!/bin/bash
#
# Kokoro TTS Installer for Hermes Agent
# =======================================
# Portable installer — works on any VPS with Hermes installed.
# Run locally or via: curl -fsSL <url>/install.sh | bash
#
set -e

KOKORO_VENV="${KOKORO_VENV:-/opt/kokoro-venv}"
KOKORO_MODEL_DIR="${KOKORO_MODEL_DIR:-/root/.kokoro}"
HERMES_CONFIG="${HERMES_CONFIG:-$HOME/.hermes/config.yaml}"

echo "========================================="
echo " Kokoro TTS Installer for Hermes"
echo "========================================="
echo ""
echo "Venv:     $KOKORO_VENV"
echo "Models:   $KOKORO_MODEL_DIR"
echo "Hermes:   $HERMES_CONFIG"
echo ""

# Detect Python
PYTHON=$(command -v python3 || command -v python)
[ -z "$PYTHON" ] && echo "ERROR: No Python found" && exit 1
echo "Python: $PYTHON ($($PYTHON --version))"

# Step 1: System dependency
echo ""
echo "[1/6] Installing espeak-ng..."
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y espeak-ng
elif command -v yum &>/dev/null; then
    sudo yum install -y espeak-ng
elif command -v apk &>/dev/null; then
    sudo apk add espeak-ng
else
    echo "WARNING: Could not auto-install espeak-ng. Install manually:"
    echo "  apt-get install espeak-ng   # Debian/Ubuntu"
    echo "  yum install espeak-ng       # RHEL/CentOS"
fi

# Step 2: Create venv
echo ""
echo "[2/6] Creating Python venv at $KOKORO_VENV..."
$PYTHON -m venv --system-site-packages "$KOKORO_VENV"
source "$KOKORO_VENV/bin/activate"
pip install --upgrade pip -q

# Step 3: Install Python packages
echo ""
echo "[3/6] Installing Kokoro + dependencies..."
pip install -q \
    kokoro-onnx \
    huggingface-hub \
    scipy \
    espeakng-loader \
    phonemizer-fork \
    misaki \
    num2words \
    numpy

# Step 4: Download model + voices from correct source
echo ""
echo "[4/6] Downloading Kokoro model + voices..."
mkdir -p "$KOKORO_MODEL_DIR/models/thewh1teagle"
mkdir -p "$KOKORO_MODEL_DIR/voices/thewh1teagle"

MODEL_FILE="$KOKORO_MODEL_DIR/models/thewh1teagle/kokoro-v1.0.fp16.onnx"
VOICES_FILE="$KOKORO_MODEL_DIR/voices/thewh1teagle/voices-v1.0.bin"

if [ ! -f "$MODEL_FILE" ]; then
    echo "  Downloading model (169 MB)..."
    curl -sL "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx" \
        -o "$MODEL_FILE"
else
    echo "  Model already exists, skipping"
fi

if [ ! -f "$VOICES_FILE" ]; then
    echo "  Downloading voices (28 MB)..."
    curl -sL "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" \
        -o "$VOICES_FILE"
else
    echo "  Voices already exist, skipping"
fi

# Step 5: Patch kokoro-onnx for raw float32 voice files
echo ""
echo "[5/6] Patching kokoro-onnx for raw float32 voices..."
KOKORO_INIT=$(find "$KOKORO_VENV" -name "__init__.py" -path "*kokoro_onnx*" | head -1)
if [ -n "$KOKORO_INIT" ] && grep -q 'np.load(voices_path)' "$KOKORO_INIT"; then
    python3 << 'PATCH'
import re, sys
init_file = sys.argv[1]
with open(init_file, 'r') as f:
    content = f.read()

def fix_voices_load(match):
    prefix = match.group(1)
    return f"""{prefix}try:
{prefix}    self.voices: np.ndarray = np.load(voices_path)
{prefix}except ValueError:
{prefix}    data = np.fromfile(voices_path, dtype=np.float32)
{prefix}    self.voices = data.reshape(-1, 1, 256)"""

new_content = re.sub(
    r'(\s+)self\.voices: np\.ndarray = np\.load\(voices_path\)',
    fix_voices_load,
    content
)
with open(init_file, 'w') as f:
    f.write(new_content)
print(f"Patched: {init_file}")
PATCH
    "$KOKORO_INIT"
    echo "  Patched successfully"
else
    echo "  Already patched or kokoro_onnx not found"
fi

# Step 6: Deploy TTS script
echo ""
echo "[6/6] Deploying Kokoro TTS script..."
mkdir -p "$HOME/.kokoro"
KOKORO_TTS_SCRIPT="$HOME/.kokoro/kokoro_tts.py"

cat > "$KOKORO_TTS_SCRIPT" << 'SCRIPT_EOF'
#!/usr/bin/env python3
"""Kokoro TTS Generator — Hermes Command Provider."""
import os, sys, argparse, subprocess

os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = '/opt/kokoro-venv/lib/python3.11/site-packages/espeakng_loader/libespeak-ng.so'
os.environ['PHONEMIZER_ESPEAK_DATA'] = '/opt/kokoro-venv/lib/python3.11/site-packages/espeakng_loader/espeak-ng-data'

from kokoro_onnx import Kokoro
import scipy.io.wavfile as wavfile

MODEL = '/root/.kokoro/models/thewh1teagle/kokoro-v1.0.fp16.onnx'
VOICES = '/root/.kokoro/voices/thewh1teagle/voices-v1.0.bin'
_kokoro = None

def get():
    global _kokoro
    if _kokoro is None:
        _kokoro = Kokoro(MODEL, VOICES)
    return _kokoro

def generate(text, out_path, voice='bm_fable', speed=0.95):
    kokoro = get()
    audio, sr = kokoro.create(text, voice=voice, speed=speed)
    wavfile.write(out_path, sr, audio)
    if out_path.endswith('.mp3'):
        base = out_path.replace('.mp3', '.wav')
        wavfile.write(base, sr, audio)
        subprocess.run(['ffmpeg', '-y', '-i', base, '-codec:a', 'libmp3lame', '-qscale:a', '2', out_path],
                       capture_output=True)
        os.remove(base)
    return out_path

if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--input', help='Text input file')
    a.add_argument('--output', required=True)
    a.add_argument('--voice', default='bm_fable')
    a.add_argument('--speed', type=float, default=0.95)
    a.add_argument('--format', default='wav')
    args = a.parse_args()
    text = open(args.input).read().strip() if args.input else sys.stdin.read().strip()
    generate(text, args.output, voice=args.voice, speed=args.speed)
SCRIPT_EOF

chmod +x "$KOKORO_TTS_SCRIPT"

echo ""
echo "========================================="
echo " Installation Complete!"
echo "========================================="
echo ""
echo "Add to ~/.hermes/config.yaml under tts:"
echo ""
echo "  tts:"
echo "    provider: kokoro"
echo "    kokoro:"
echo "      voice: bm_fable"
echo "      speed: 0.95"
echo "    providers:"
echo "      kokoro:"
echo "        type: command"
echo "        command: \"/opt/kokoro-venv/bin/python /root/.kokoro/kokoro_tts.py --input {text_path} --output {output_path} --voice bm_fable --speed 0.95\""
echo "        output_format: wav"
echo "        timeout: 120"
echo ""
echo "Then restart Hermes: /restart"
echo ""
