"""Synchronous end-to-end collector.

The collector orchestrates the mechanical stages:

1. OpenCLI session health check.
2. Fetch recent posts for the requested accounts.
3. Filter to reels, deduplicate against the ledger.
4. Download each reel into a per-run staging directory.
5. Validate the file with `ffprobe`; reject anything outside the caps.
6. Extract mono 16 kHz PCM WAV audio with FFmpeg.
7. Transcribe locally with Faster-Whisper.
8. Stage the deterministic batch JSON for the analysis stage.
9. Update the ledger.

The collector is decoupled from the underlying adapters via small
Protocols so the unit tests can run without a real OpenCLI/Whisper stack.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


class CollectionError(RuntimeError):
    """Raised when the collection pipeline cannot continue."""


class OpenCLIPort(Protocol):
    def session_health(self, **kwargs: Any) -> str: ...
    def fetch_user_posts(self, *, username: str, limit: int, **kwargs: Any) -> list[Any]: ...
    def download_reel(self, *, url: str, dest_dir: Path, **kwargs: Any) -> Path: ...


class MediaPort(Protocol):
    def safe_staging_dir(self, root: Path, name: str) -> Path: ...
    def validate_download(self, path: Path, **kwargs: Any) -> dict[str, Any]: ...
    def extract_audio(self, src: Path, dst: Path) -> Path: ...


class WhisperPort(Protocol):
    def transcribe(self, audio_path: Path, **kwargs: Any) -> Any: ...


@dataclass
class CollectResult:
    run_id: str
    accepted_count: int = 0
    rejected_count: int = 0
    failed_count: int = 0
    failed_items: list[tuple[str, str, str]] | None = None

    def __post_init__(self) -> None:
        if self.failed_items is None:
            self.failed_items = []


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _shortcode(url: str) -> str:
    m = re.search(r"/(?:reel|reels|p|tv)/([A-Za-z0-9_-]{6,20})(?:/|$|\?)", url)
    return m.group(1) if m else ""


def collect_for_account(
    *,
    username: str,
    limit: int,
    staging_root: Path,
    run_id: str,
    opencli: OpenCLIPort,
    media: MediaPort,
    whisper: WhisperPort,
    ledger: Any,
    max_bytes: int = 100 * 1024 * 1024,
    max_duration_seconds: int = 180,
) -> CollectResult:
    """Run the full pipeline for one account. Returns a summary."""

    result = CollectResult(run_id=run_id)

    # 1. Session health.
    try:
        opencli.session_health()
    except Exception as exc:
        raise CollectionError(f"opencli session unhealthy: {exc}") from exc

    # 2. Fetch.
    items = opencli.fetch_user_posts(username=username, limit=limit)
    known = ledger.known() if hasattr(ledger, "known") else set()

    # 3+4+5+6+7. For each reel: dedup, download, validate, extract, transcribe.
    stage_dir = media.safe_staging_dir(staging_root, run_id)
    videos_dir = stage_dir / "videos"
    audio_dir = stage_dir / "audio"
    videos_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    batch_items: list[dict[str, Any]] = []
    for item in items:
        shortcode = _shortcode(_get(item, "url", "") or "")
        if not shortcode:
            continue
        if shortcode in known:
            result.rejected_count += 1
            continue
        url = _get(item, "url", "")
        try:
            video_path = opencli.download_reel(url=url, dest_dir=videos_dir)
            media.validate_download(
                video_path,
                max_bytes=max_bytes,
                max_duration_seconds=max_duration_seconds,
            )
            audio_path = media.extract_audio(video_path, audio_dir / f"{shortcode}.wav")
            transcript = whisper.transcribe(audio_path)
        except Exception as exc:
            result.failed_count += 1
            if result.failed_items is not None:
                result.failed_items.append((username, shortcode, f"{type(exc).__name__}: {exc}"))
            try:
                ledger.add("failed", shortcode)
            except Exception:
                pass
            continue

        batch_items.append(
            {
                "shortcode": shortcode,
                "username": _get(item, "username", username),
                "url": url,
                "caption": _get(item, "caption", ""),
                "views": _get(item, "views", 0),
                "likes": _get(item, "likes", 0),
                "comments": _get(item, "comments", 0),
                "published_at": _get(item, "published_at", None),
                "transcript": getattr(transcript, "text", ""),
                "transcript_segments": [s.__dict__ for s in getattr(transcript, "segments", [])],
                "transcript_language": getattr(transcript, "language", "unknown"),
                "transcript_language_probability": getattr(transcript, "language_probability", 0.0),
                "transcription_model": getattr(transcript, "model", "unknown"),
                "transcription_device": getattr(transcript, "device", "cpu"),
                "transcription_compute_type": getattr(transcript, "compute_type", "int8"),
                "transcription_duration_ms": getattr(transcript, "duration_ms", 0),
            }
        )
        result.accepted_count += 1
        try:
            ledger.add("scraped", shortcode)
        except Exception:
            pass

    # 8. Stage.
    stage_batch(staging_root, run_id, batch_items)
    return result


def stage_batch(staging_root: Path, run_id: str, items: list[dict[str, Any]]) -> Path:
    """Write a deterministic batch JSON for downstream analysis."""

    dest = staging_root / run_id / "batch.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return dest


__all__ = [
    "CollectResult",
    "CollectionError",
    "collect_for_account",
    "stage_batch",
]
