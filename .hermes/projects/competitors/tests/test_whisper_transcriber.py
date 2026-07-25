"""Tests for the Faster-Whisper transcriber.

The transcriber takes an injected backend so unit tests can simulate
success, failure, and unsupported input without downloading a real model.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.whisper_transcriber import (
    TranscriptionError,
    TranscriptionResult,
    transcribe,
)


class _FakeSegment:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start = start
        self.end = end
        self.text = text


class _FakeInfo:
    def __init__(self, language: str = "en", probability: float = 0.99) -> None:
        self.language = language
        self.language_probability = probability


class _FakeBackendSuccess:
    def transcribe(self, audio_path: str, beam_size: int = 5):
        segments = [
            _FakeSegment(0.0, 1.5, "Hello"),
            _FakeSegment(1.5, 3.0, "world"),
        ]
        info = _FakeInfo("en", 0.98)
        return iter(segments), info


class _FakeBackendFailure:
    def transcribe(self, audio_path: str, beam_size: int = 5):
        raise RuntimeError("model file not found")


def _make_audio(tmp_path: Path) -> Path:
    p = tmp_path / "audio.wav"
    p.write_bytes(b"RIFF" + b"\x00" * 200)
    return p


def test_transcribe_returns_segments_and_metadata(tmp_path: Path) -> None:
    audio = _make_audio(tmp_path)
    result = transcribe(audio, backend=_FakeBackendSuccess(), model_name="tiny", device="cpu")
    assert isinstance(result, TranscriptionResult)
    assert result.language == "en"
    assert result.language_probability == pytest.approx(0.98)
    assert len(result.segments) == 2
    assert result.text == "Hello world"
    assert result.model == "tiny"
    assert result.device == "cpu"


def test_transcribe_raises_on_backend_error(tmp_path: Path) -> None:
    audio = _make_audio(tmp_path)
    with pytest.raises(TranscriptionError, match="model file not found"):
        transcribe(audio, backend=_FakeBackendFailure(), model_name="tiny", device="cpu")


def test_transcribe_raises_on_missing_audio(tmp_path: Path) -> None:
    with pytest.raises(TranscriptionError):
        transcribe(tmp_path / "absent.wav", backend=_FakeBackendSuccess(), model_name="tiny", device="cpu")


def test_transcribe_serializes_to_dict(tmp_path: Path) -> None:
    audio = _make_audio(tmp_path)
    result = transcribe(audio, backend=_FakeBackendSuccess(), model_name="tiny", device="cpu")
    d = result.to_dict()
    assert d["text"] == "Hello world"
    assert d["language"] == "en"
    assert d["model"] == "tiny"
    assert d["device"] == "cpu"
    assert d["segments"] == [
        {"start": 0.0, "end": 1.5, "text": "Hello"},
        {"start": 1.5, "end": 3.0, "text": "world"},
    ]
