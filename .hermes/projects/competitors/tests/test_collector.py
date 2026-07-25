"""Tests for the synchronous end-to-end collector pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipeline.collector import (
    CollectionError,
    collect_for_account,
    stage_batch,
)
from pipeline.ledger import Ledger


class _FakeOpenCLI:
    def __init__(self, items: list[dict[str, Any]] | None = None, raise_health: bool = False) -> None:
        self._items = items or []
        self._raise_health = raise_health
        self.calls: list[tuple[str, tuple, dict]] = []

    def fetch_user_posts(self, *, username: str, limit: int, **kwargs):
        self.calls.append(("fetch_user_posts", (username, limit), kwargs))
        return self._items

    def session_health(self, **kwargs):
        if self._raise_health:
            raise RuntimeError("BROWSER_NOT_CONNECTED")
        return "test_account"

    def download_reel(self, *, url: str, dest_dir: Path, **kwargs):
        self.calls.append(("download_reel", (url, str(dest_dir)), kwargs))
        out = dest_dir / f"{url.rsplit('/', 2)[-2]}.mp4"
        out.write_bytes(b"\x00" * 128)
        return out


class _FakeMedia:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def safe_staging_dir(self, root: Path, name: str) -> Path:
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def validate_download(self, path: Path, **kwargs) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("no audio stream")
        return {"format": {"duration": "12.0"}, "streams": [{"codec_type": "audio"}]}

    def extract_audio(self, src: Path, dst: Path) -> Path:
        dst.write_bytes(b"RIFF" + b"\x00" * 100)
        return dst


class _FakeWhisper:
    def transcribe(self, audio_path: Path, **kwargs):
        from pipeline.whisper_transcriber import TranscriptionResult

        return TranscriptionResult(
            text="hello world",
            language="en",
            language_probability=0.99,
            segments=[],
            model="tiny",
            device="cpu",
            compute_type="int8",
            duration_ms=120,
        )


def _good_item(shortcode: str = "abc123def") -> dict:
    return {
        "type": "reel",
        "url": f"https://www.instagram.com/reel/{shortcode}/",
        "ownerUsername": "test_account",
        "caption": "caption",
        "videoViewCount": 100,
        "likesCount": 10,
        "commentsCount": 2,
        "date": "2026-07-24T10:00:00+08:00",
    }


def test_collect_for_account_writes_staged_batch(tmp_path: Path) -> None:
    base = tmp_path / "data"
    base.mkdir()
    opencli = _FakeOpenCLI(items=[_good_item()])
    media = _FakeMedia()
    whisper = _FakeWhisper()
    ledger = Ledger(base / "ledger.json")

    result = collect_for_account(
        username="test_account",
        limit=3,
        staging_root=base / "staging",
        run_id="run-1",
        opencli=opencli,
        media=media,
        whisper=whisper,
        ledger=ledger,
    )

    assert result.run_id == "run-1"
    assert result.accepted_count == 1
    assert result.rejected_count == 0
    batch_file = base / "staging" / "run-1" / "batch.json"
    assert batch_file.exists()
    body = json.loads(batch_file.read_text())
    assert body["run_id"] == "run-1"
    assert body["items"][0]["shortcode"] == "abc123def"
    assert body["items"][0]["transcript"] == "hello world"
    assert ledger.read()["scraped"] == ["abc123def"]


def test_collect_for_account_dedupes_known_shortcodes(tmp_path: Path) -> None:
    base = tmp_path / "data"
    base.mkdir()
    opencli = _FakeOpenCLI(items=[_good_item()])
    media = _FakeMedia()
    whisper = _FakeWhisper()
    ledger = Ledger(base / "ledger.json")
    ledger.add("scraped", "abc123def")

    result = collect_for_account(
        username="test_account",
        limit=3,
        staging_root=base / "staging",
        run_id="run-2",
        opencli=opencli,
        media=media,
        whisper=whisper,
        ledger=ledger,
    )
    assert result.accepted_count == 0
    assert result.rejected_count == 1


def test_collect_for_account_logs_failed_items(tmp_path: Path) -> None:
    base = tmp_path / "data"
    base.mkdir()
    opencli = _FakeOpenCLI(items=[_good_item()])
    media = _FakeMedia(fail=True)
    whisper = _FakeWhisper()
    ledger = Ledger(base / "ledger.json")

    result = collect_for_account(
        username="test_account",
        limit=3,
        staging_root=base / "staging",
        run_id="run-3",
        opencli=opencli,
        media=media,
        whisper=whisper,
        ledger=ledger,
    )
    assert result.accepted_count == 0
    assert result.failed_count == 1
    assert ledger.read()["failed"] == ["abc123def"]


def test_collect_for_account_skips_when_session_unhealthy(tmp_path: Path) -> None:
    base = tmp_path / "data"
    base.mkdir()
    opencli = _FakeOpenCLI(raise_health=True)
    media = _FakeMedia()
    whisper = _FakeWhisper()
    ledger = Ledger(base / "ledger.json")

    with pytest.raises(CollectionError, match="session"):
        collect_for_account(
            username="test_account",
            limit=3,
            staging_root=base / "staging",
            run_id="run-bad",
            opencli=opencli,
            media=media,
            whisper=whisper,
            ledger=ledger,
        )


def test_stage_batch_writes_file(tmp_path: Path) -> None:
    out = stage_batch(tmp_path, "run-x", [{"shortcode": "abc123def"}])
    assert out.exists()
    assert json.loads(out.read_text())["items"][0]["shortcode"] == "abc123def"
