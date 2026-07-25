"""Tests for media validation and FFmpeg normalization."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pipeline.media import (
    MediaError,
    extract_audio,
    probe_media,
    safe_staging_dir,
    validate_download,
)


def _fake_ffprobe_ok(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "duration": "12.0"},
                    {"codec_type": "audio", "codec_name": "aac", "duration": "12.0"},
                ],
                "format": {"format_name": "mp4", "duration": "12.0", "size": "1024"},
            }
        ),
        encoding="utf-8",
    )


def test_safe_staging_dir_creates_under_root(tmp_path: Path) -> None:
    base = tmp_path / "staging"
    d = safe_staging_dir(base, "run-1")
    assert d.is_dir()
    assert d.parent == base
    assert d.name == "run-1"


def test_safe_staging_dir_rejects_traversal(tmp_path: Path) -> None:
    base = tmp_path / "staging"
    base.mkdir()
    with pytest.raises(MediaError):
        safe_staging_dir(base, "../../etc")


def test_safe_staging_dir_rejects_existing_symlink(tmp_path: Path) -> None:
    base = tmp_path / "staging"
    base.mkdir()
    target = base / "run-1"
    target.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(MediaError):
        safe_staging_dir(base, "run-1")


def test_probe_media_returns_streams_and_format(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = tmp_path / "probe.json"
    _fake_ffprobe_ok(fake)

    def fake_run(argv, *args, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout=fake.read_text(), stderr="")

    monkeypatch.setattr("pipeline.media.subprocess.run", fake_run)
    out = probe_media(tmp_path / "video.mp4")
    assert out["format"]["format_name"] == "mp4"
    assert any(s["codec_type"] == "video" for s in out["streams"])


def test_probe_media_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(argv, *args, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=1, stdout="", stderr="bad input")

    monkeypatch.setattr("pipeline.media.subprocess.run", fake_run)
    with pytest.raises(MediaError, match="ffprobe"):
        probe_media(tmp_path / "video.mp4")


def test_validate_download_rejects_oversize(tmp_path: Path) -> None:
    big = tmp_path / "big.mp4"
    big.write_bytes(b"\x00" * 200)
    with pytest.raises(MediaError, match="too large"):
        validate_download(
            big,
            max_bytes=100,
            max_duration_seconds=60,
            ffprobe=lambda p: {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"format_name": "mp4", "duration": "12.0"},
            },
        )


def test_validate_download_rejects_no_audio_stream(tmp_path: Path) -> None:
    f = tmp_path / "silent.mp4"
    f.write_bytes(b"\x00" * 1024)
    with pytest.raises(MediaError, match="no audio stream"):
        validate_download(
            f,
            max_bytes=10000,
            max_duration_seconds=60,
            ffprobe=lambda p: {
                "streams": [{"codec_type": "video", "codec_name": "h264"}],
                "format": {"format_name": "mp4", "duration": "12.0"},
            },
        )


def test_validate_download_rejects_oversize_duration(tmp_path: Path) -> None:
    f = tmp_path / "long.mp4"
    f.write_bytes(b"\x00" * 1024)
    with pytest.raises(MediaError, match="too long"):
        validate_download(
            f,
            max_bytes=10000,
            max_duration_seconds=10,
            ffprobe=lambda p: {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"format_name": "mp4", "duration": "60.0"},
            },
        )


def test_validate_download_accepts_good_input(tmp_path: Path) -> None:
    f = tmp_path / "good.mp4"
    f.write_bytes(b"\x00" * 1024)
    result = validate_download(
        f,
        max_bytes=10000,
        max_duration_seconds=60,
        ffprobe=lambda p: {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"format_name": "mp4", "duration": "12.0"},
        },
    )
    assert result["format"]["format_name"] == "mp4"


def test_extract_audio_creates_wav_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    src = tmp_path / "vid.mp4"
    src.write_bytes(b"\x00" * 1024)
    out = tmp_path / "audio.wav"

    def fake_run(argv, *args, **kwargs):
        out.write_bytes(b"RIFF" + b"\x00" * 100)
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("pipeline.media.subprocess.run", fake_run)
    result = extract_audio(src, out)
    assert result == out
    assert out.exists()
