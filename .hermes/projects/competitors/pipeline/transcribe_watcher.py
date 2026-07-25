"""Transcription watcher.

This module runs as a background service inside the dev VPS. It:

1. Polls the audio directory for new reel audio files.
2. Runs Faster-Whisper on each new file.
3. Writes a publish bundle to the bundles directory.
4. The API importer ingests the bundle.

The watcher is intentionally tiny: no message queue, no database writes.
The API is the only writer to the database. The watcher is a pure file
transformer.

Run with: `python -m pipeline.transcribe_watcher`
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Iterator

from faster_whisper import WhisperModel  # type: ignore[import-untyped]

from .models import AnalysisBundle, AnalysisItem
from . import whisper_transcriber


logger = logging.getLogger("transcribe_watcher")

SAFE_USERNAME_RE = re.compile(r"^[a-z0-9._-]{1,30}$")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def discover_audio(audio_dir: Path) -> Iterator[Path]:
    """Yield audio files in the audio directory that haven't been
    processed yet.

    A file is processed if its sibling `.done` marker exists.
    """
    if not audio_dir.exists():
        return
    for entry in sorted(audio_dir.iterdir()):
        if entry.is_file() and entry.suffix.lower() in {".wav", ".mp3", ".m4a", ".ogg"}:
            done_marker = entry.with_suffix(entry.suffix + ".done")
            if not done_marker.exists():
                yield entry


def transcribe_file(model: WhisperModel, audio_path: Path, language: str) -> AnalysisItem:
    """Run Faster-Whisper on a single file and return an AnalysisItem.

    The shortcode is derived from the filename (e.g. `mallu.wave_ABC123.wav`).
    """
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language or None,
        vad_filter=True,
    )
    segments = list(segments_iter)
    phrases = [s.text.strip() for s in segments if s.text.strip()][:10]
    transcript = " ".join(phrases)
    parts = audio_path.stem.split("__", 1)
    if len(parts) == 2:
        competitor, shortcode = parts
    else:
        competitor, shortcode = parts[0], audio_path.stem
    if not SAFE_USERNAME_RE.match(competitor):
        raise ValueError(f"unsafe competitor username in filename: {competitor!r}")
    return AnalysisItem(
        shortcode=shortcode,
        competitor_username=competitor,
        transcript=transcript,
        hook=phrases[0] if phrases else "",
        emotion="",
        pacing="",
        summary=transcript[:280],
        notable_phrases=phrases,
        recommendation="",
        notes="",
        published_at=None,
        view_count=None,
        like_count=None,
        comment_count=None,
        duration_seconds=round(info.duration, 2) if info.duration else None,
        source_url=None,
        audio_path=str(audio_path),
    )


def write_bundle(run_id: str, items: list[AnalysisItem], bundle_dir: Path) -> Path:
    """Write a publish bundle to the bundle directory."""
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = AnalysisBundle(run_id=run_id, items=items)
    out_path = bundle_dir / f"{run_id}.json"
    out_path.write_text(bundle.model_dump_json(indent=2))
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transcription watcher")
    parser.add_argument("--audio-dir", default=_env("WHISPER_AUDIO_DIR", "/srv/competitors-private/audio"))
    parser.add_argument("--bundle-dir", default=_env("WHISPER_BUNDLE_DIR", "/srv/competitors-private/bundles"))
    parser.add_argument("--model", default=_env("WHISPER_MODEL", "tiny"))
    parser.add_argument("--language", default=_env("WHISPER_LANGUAGE", "en"))
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    audio_dir = Path(args.audio_dir)
    bundle_dir = Path(args.bundle_dir)

    logger.info("loading whisper model=%s language=%s", args.model, args.language)
    model = whisper_transcriber.load_model(args.model)

    while True:
        items: list[AnalysisItem] = []
        for audio_path in list(discover_audio(audio_dir)):
            try:
                item = transcribe_file(model, audio_path, args.language)
            except Exception as exc:  # noqa: BLE001
                logger.exception("failed to transcribe %s: %s", audio_path.name, exc)
                continue
            items.append(item)
            # Mark as done so we don't re-process.
            audio_path.with_suffix(audio_path.suffix + ".done").touch()
            logger.info("transcribed %s (%d segments)", audio_path.name, len(item.notable_phrases))

        if items:
            run_id = f"run-{int(time.time())}"
            bundle_path = write_bundle(run_id, items, bundle_dir)
            logger.info("wrote bundle %s with %d items", bundle_path, len(items))

        if args.once:
            return 0
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    sys.exit(main())
