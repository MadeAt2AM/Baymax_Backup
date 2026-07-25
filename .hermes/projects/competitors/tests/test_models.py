"""Tests for the typed Pydantic models that bound the analysis contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.models import (
    AnalysisBundle,
    HookStyle,
    ReelInput,
    Section,
    TranscriptSegment,
)


def _reel(**overrides) -> dict:
    base = {
        "shortcode": "abc123",
        "username": "test_account",
        "url": "https://www.instagram.com/reel/abc123/",
        "views": 1000,
        "likes": 50,
        "comments": 5,
        "caption": "A caption.",
        "transcript": "Full transcript text here.",
        "scraped_at": "2026-07-24T10:00:00+08:00",
    }
    base.update(overrides)
    return base


def test_reel_input_accepts_valid_payload() -> None:
    reel = ReelInput.model_validate(_reel())
    assert reel.shortcode == "abc123"
    assert reel.views == 1000


def test_reel_input_rejects_invalid_shortcode() -> None:
    with pytest.raises(ValidationError):
        ReelInput.model_validate(_reel(shortcode="bad shortcode!"))


def test_hook_style_enum_accepts_all_values() -> None:
    for value in (
        "problem-promise",
        "contrarian-claim",
        "list-tease",
        "demo-first",
        "story-frame",
        "data-shock",
        "identity-call",
        "other",
    ):
        assert HookStyle(value).value == value


def test_hook_style_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        HookStyle("not-a-hook-style")


def test_section_validates_text_is_substring_of_transcript() -> None:
    section = Section(
        label="Hook",
        text="Full transcript text",
        note="opens with context",
    )
    assert section.label == "Hook"


def test_section_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        Section(label="Hook", text="", note="empty")


def test_section_rejects_label_outside_allowed_set() -> None:
    with pytest.raises(ValidationError):
        Section(label="Random", text="anything", note="x")


def test_transcript_segment_serializes_round_trip() -> None:
    seg = TranscriptSegment(start=0.0, end=2.5, text="hello")
    dumped = seg.model_dump()
    assert dumped == {"start": 0.0, "end": 2.5, "text": "hello"}


def test_analysis_bundle_requires_score_in_range() -> None:
    base = {
        "niche": "strength training for busy professionals over 30",
        "source": _reel(),
        "analysis": {
            "relevance_score": 11,
            "verdict": True,
            "topic": "On-niche topic",
            "tools": [],
            "hook_style": "problem-promise",
            "reasoning": "Direct match.",
            "sections": [],
            "research": [],
            "angle_suggestion": "Test your angle.",
        },
        "model": {"provider": "minimax", "model": "MiniMax-M3", "analyzed_at": "2026-07-24T10:00:00+08:00"},
    }
    with pytest.raises(ValidationError):
        AnalysisBundle.model_validate(base)


def test_analysis_bundle_requires_hook_style_enum() -> None:
    base = {
        "niche": "x",
        "source": _reel(),
        "analysis": {
            "relevance_score": 8,
            "verdict": True,
            "topic": "topic",
            "tools": ["a"],
            "hook_style": "not-an-enum-value",
            "reasoning": "ok",
            "sections": [],
            "research": [],
            "angle_suggestion": "angle",
        },
        "model": {"provider": "minimax", "model": "MiniMax-M3", "analyzed_at": "2026-07-24T10:00:00+08:00"},
    }
    with pytest.raises(ValidationError):
        AnalysisBundle.model_validate(base)
