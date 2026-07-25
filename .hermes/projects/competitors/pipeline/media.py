"""FFmpeg/ffprobe wrapper for media validation and audio normalization.

The functions in this module:

- Validate a downloaded reel is a regular, in-bounds file with a video
  stream and an audio stream.
- Reject path traversal, symlink escapes, and oversized/overlong media.
- Probe the file with `ffprobe` and return the parsed JSON.
- Extract a mono 16 kHz PCM WAV via `ffmpeg` for downstream Whisper.

All subprocess calls go through argument arrays, never `shell=True`.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable


class MediaError(RuntimeError):
    """Raised for invalid media or failed validation/processing."""


_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _safe_name(name: str) -> str:
    if not _SAFE_NAME_RE.match(name):
        raise MediaError(f"unsafe staging name: {name!r}")
    return name


def safe_staging_dir(root: Path, name: str) -> Path:
    """Create a staging directory under `root`, rejecting traversal/symlinks."""

    _safe_name(name)
    target = (root / name).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise MediaError(f"staging path escapes root: {target}")
    if target.exists():
        if target.is_symlink():
            raise MediaError(f"refusing to follow symlink at {target}")
        if not target.is_dir():
            raise MediaError(f"staging path is not a directory: {target}")
    else:
        target.mkdir(parents=True, exist_ok=False)
    return target


def probe_media(path: Path) -> dict[str, Any]:
    """Return the parsed ffprobe JSON for `path`."""

    argv = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    proc = subprocess.run(  # noqa: S603 — argv is a sanitized list
        argv,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0:
        raise MediaError(f"ffprobe failed (exit {proc.returncode}): {(proc.stderr or '').strip()[:200]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise MediaError(f"ffprobe returned non-JSON output: {exc}") from exc


def validate_download(
    path: Path,
    *,
    max_bytes: int,
    max_duration_seconds: int,
    ffprobe: Callable[[Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate a downloaded file. Returns the parsed probe on success."""

    if not path.exists() or path.is_symlink():
        raise MediaError(f"missing or symlink: {path}")
    if not path.is_file():
        raise MediaError(f"not a regular file: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise MediaError(f"empty file: {path}")
    if size > max_bytes:
        raise MediaError(f"file too large: {size} > {max_bytes} bytes")

    info = ffprobe(path) if ffprobe is not None else probe_media(path)
    streams = info.get("streams") or []
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if not has_video:
        raise MediaError(f"no video stream in {path}")
    if not has_audio:
        raise MediaError(f"no audio stream in {path}")
    fmt = info.get("format") or {}
    try:
        duration = float(fmt.get("duration", 0))
    except (TypeError, ValueError):
        duration = 0.0
    if duration > max_duration_seconds:
        raise MediaError(f"video too long: {duration:.1f}s > {max_duration_seconds}s")
    return info


def extract_audio(src: Path, dst: Path) -> Path:
    """Extract mono 16 kHz PCM WAV audio from `src` to `dst`."""

    dst.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]
    proc = subprocess.run(  # noqa: S603
        argv,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
        timeout=300,
    )
    if proc.returncode != 0 or not dst.exists():
        raise MediaError(f"ffmpeg extract failed (exit {proc.returncode}): {(proc.stderr or '').strip()[:200]}")
    return dst
