"""Faster-Whisper transcription with an injectable backend.

The transcriber accepts a backend object that exposes `transcribe(audio_path,
beam_size)` returning `(segments, info)` in the same shape as
`faster_whisper.WhisperModel.transcribe`. This lets unit tests run without
loading a real model.

The backend is constructed via `FasterWhisperBackend` when no backend is
explicitly supplied. The default device is `cpu`; the default compute type
is `int8` for CPU efficiency on the dev VPS.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol


DEFAULT_BEAM_SIZE = 5


class TranscriptionError(RuntimeError):
    """Raised when the transcriber fails to produce a usable result."""


@dataclass
class TranscriptionInfo:
    language: str
    language_probability: float


@dataclass
class TranscriptionSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    text: str
    language: str
    language_probability: float
    segments: list[TranscriptionSegment]
    model: str
    device: str
    compute_type: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "language_probability": self.language_probability,
            "segments": [
                {"start": s.start, "end": s.end, "text": s.text} for s in self.segments
            ],
            "model": self.model,
            "device": self.device,
            "compute_type": self.compute_type,
            "duration_ms": self.duration_ms,
        }


class _Backend(Protocol):
    def transcribe(self, audio_path: str, beam_size: int) -> tuple[Iterable[Any], Any]: ...


class FasterWhisperBackend:
    """Concrete backend wrapping `faster_whisper.WhisperModel`."""

    def __init__(self, *, model_name: str, device: str, compute_type: str, model_revision: str | None = None) -> None:
        from faster_whisper import WhisperModel  # local import: heavy dep

        kwargs: dict[str, Any] = {"device": device, "compute_type": compute_type}
        if model_revision:
            kwargs["model_revision"] = model_revision
        self._model = WhisperModel(model_name, **kwargs)

    def transcribe(self, audio_path: str, beam_size: int):
        return self._model.transcribe(audio_path, beam_size=beam_size)


def transcribe(
    audio_path: Path,
    *,
    backend: _Backend | None = None,
    model_name: str = "tiny",
    device: str = "cpu",
    compute_type: str = "int8",
    beam_size: int = DEFAULT_BEAM_SIZE,
    model_revision: str | None = None,
) -> TranscriptionResult:
    """Transcribe `audio_path` and return a structured result."""

    if not audio_path.exists() or audio_path.is_symlink():
        raise TranscriptionError(f"missing audio file: {audio_path}")

    if backend is None:
        backend = FasterWhisperBackend(
            model_name=model_name,
            device=device,
            compute_type=compute_type,
            model_revision=model_revision,
        )

    started = _now_ms()
    try:
        segments_iter, info = backend.transcribe(str(audio_path), beam_size=beam_size)
        segments = [
            TranscriptionSegment(
                start=float(getattr(s, "start", 0.0)),
                end=float(getattr(s, "end", 0.0)),
                text=str(getattr(s, "text", "")).strip(),
            )
            for s in segments_iter
        ]
    except Exception as exc:  # noqa: BLE001 — surface any backend failure with a clear message
        raise TranscriptionError(f"transcription failed: {exc}") from exc

    text = " ".join(s.text for s in segments).strip()
    duration_ms = _now_ms() - started
    return TranscriptionResult(
        text=text,
        language=str(getattr(info, "language", "unknown")),
        language_probability=float(getattr(info, "language_probability", 0.0)),
        segments=segments,
        model=model_name,
        device=device,
        compute_type=compute_type,
        duration_ms=duration_ms,
    )


def _now_ms() -> int:
    import time

    return int(time.monotonic() * 1000)


__all__ = [
    "DEFAULT_BEAM_SIZE",
    "FasterWhisperBackend",
    "TranscriptionError",
    "TranscriptionInfo",
    "TranscriptionResult",
    "TranscriptionSegment",
    "transcribe",
]
