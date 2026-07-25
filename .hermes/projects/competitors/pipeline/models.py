"""Pydantic models that bound the analysis contract.

These types are the source of truth for what a validated analysis bundle
looks like. They are enforced at import time and before publishing. The
JSON schema is exported for use by `scripts/validate_analysis.py`.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


SHORTCODE_RE = r"^[A-Za-z0-9_-]{6,20}$"


class HookStyle(str, Enum):
    problem_promise = "problem-promise"
    contrarian_claim = "contrarian-claim"
    list_tease = "list-tease"
    demo_first = "demo-first"
    story_frame = "story-frame"
    data_shock = "data-shock"
    identity_call = "identity-call"
    other = "other"


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str = Field(min_length=1, max_length=2000)


class ReelInput(BaseModel):
    shortcode: str = Field(pattern=SHORTCODE_RE)
    username: str = Field(min_length=1, max_length=64)
    url: str = Field(pattern=r"^https://www\.instagram\.com/.+")
    views: int = Field(ge=0)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    caption: str = Field(default="", max_length=4000)
    transcript: str = Field(default="", max_length=20000)
    scraped_at: datetime

    @field_validator("username")
    @classmethod
    def _validate_username(cls, v: str) -> str:
        return v.lower().lstrip("@")


SectionLabel = Literal["Hook", "Beat 1", "Beat 2", "Beat 3", "Beat 4", "Beat 5", "Beat 6", "Beat 7", "Beat 8", "CTA"]


class Section(BaseModel):
    label: SectionLabel
    text: str = Field(min_length=1, max_length=4000)
    note: str = Field(min_length=1, max_length=240)


class ToolResearch(BaseModel):
    tool: str = Field(min_length=1, max_length=120)
    one_liner: str = Field(min_length=1, max_length=240)
    how_it_works: str = Field(min_length=1, max_length=1000)
    hook_fact: str = Field(min_length=1, max_length=240)
    source_url: str = Field(pattern=r"^https?://")


class AnalysisSection(BaseModel):
    relevance_score: int = Field(ge=1, le=10)
    verdict: bool
    topic: str = Field(min_length=1, max_length=120)
    tools: list[str] = Field(default_factory=list)
    hook_style: HookStyle
    reasoning: str = Field(min_length=1, max_length=1000)
    sections: list[Section] = Field(default_factory=list)
    research: list[ToolResearch] = Field(default_factory=list)
    angle_suggestion: str = Field(min_length=1, max_length=600)


class ModelMetadata(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=128)
    analyzed_at: datetime


class AnalysisBundle(BaseModel):
    niche: str = Field(min_length=3, max_length=240)
    source: ReelInput
    analysis: AnalysisSection
    model: ModelMetadata


def json_schema() -> dict:
    """Export the JSON schema for use by the validator script."""
    return AnalysisBundle.model_json_schema()


__all__ = [
    "AnalysisBundle",
    "AnalysisSection",
    "HookStyle",
    "ModelMetadata",
    "ReelInput",
    "Section",
    "SectionLabel",
    "ToolResearch",
    "TranscriptSegment",
    "json_schema",
]
