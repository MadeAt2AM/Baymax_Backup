#!/usr/bin/env python3
"""One-shot Groq Whisper transcription for a local media file."""
import os, sys, json, urllib.request, urllib.error, mimetypes

KEY = os.environ.get("GROQ_API_KEY")
if not KEY:
    # fall back to agent-reach config
    import yaml  # pyyaml already in agent-reach-venv
    cfg_path = os.path.expanduser("~/.agent-reach/config.yaml")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            KEY = yaml.safe_load(f).get("groq_api_key")
if not KEY:
    sys.exit("GROQ_API_KEY not set")

audio_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 else audio_path.rsplit(".", 1)[0] + ".txt"

mimetype, _ = mimetypes.guess_type(audio_path)
print(f"Uploading {audio_path} ({os.path.getsize(audio_path)} bytes, mimetype={mimetype})")

# Build multipart/form-data manually
import uuid, io
boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
parts = []
parts.append(f"--{boundary}".encode())
parts.append(b'Content-Disposition: form-data; name="model"')
parts.append(b'')
parts.append(b"whisper-large-v3-turbo")
parts.append(f"--{boundary}".encode())
parts.append(b'Content-Disposition: form-data; name="response_format"')
parts.append(b'')
parts.append(b"verbose_json")
parts.append(f"--{boundary}".encode())
parts.append(f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(audio_path)}"'.encode())
parts.append(f"Content-Type: {mimetype or 'application/octet-stream'}".encode())
parts.append(b'')
with open(audio_path, "rb") as f:
    parts.append(f.read())
parts.append(f"--{boundary}--".encode())
parts.append(b"")
body = b"\r\n".join(parts)

req = urllib.request.Request(
    "https://api.groq.com/openai/v1/audio/transcriptions",
    data=body,
    headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "curl/8.5.0",
        "Accept": "application/json",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"Groq HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")

# Verbose JSON returns segments with timestamps
text = resp.get("text", "").strip()
segments = resp.get("segments", [])

with open(out_path, "w") as f:
    f.write(f"# Transcription of {os.path.basename(audio_path)}\n\n")
    if segments:
        f.write("## Segments\n\n")
        for s in segments:
            start = s.get("start", 0)
            end = s.get("end", 0)
            t = s.get("text", "").strip()
            if t:
                f.write(f"[{start:6.2f} - {end:6.2f}] {t}\n")
        f.write("\n## Full text\n\n")
    f.write(text + "\n")

print(f"✅ Wrote {out_path} ({len(text)} chars, {len(segments)} segments)")
