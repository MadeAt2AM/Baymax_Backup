"""SQLAlchemy 2 ORM models for the competitor-intelligence dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    niche_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now, onupdate=_now)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="collecting")
    requested_accounts: Mapped[list[str]] = mapped_column(JSON, default=list)
    scraped_count: Mapped[int] = mapped_column(Integer, default=0)
    analyzed_count: Mapped[int] = mapped_column(Integer, default=0)
    kept_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    source_runtime_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class Reel(Base):
    __tablename__ = "reels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    shortcode: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    competitor_id: Mapped[str] = mapped_column(String(36), ForeignKey("competitors.id"))
    source_url: Mapped[str] = mapped_column(String(512))
    caption: Mapped[str] = mapped_column(Text, default="")
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)
    transcript: Mapped[str] = mapped_column(Text, default="")
    transcript_status: Mapped[str] = mapped_column(String(16), default="complete")
    transcript_language: Mapped[str] = mapped_column(String(16), default="unknown")
    transcript_language_probability: Mapped[float] = mapped_column(default=0.0)
    transcript_segments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    transcription_model: Mapped[str] = mapped_column(String(64), default="unknown")
    transcription_model_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transcription_device: Mapped[str] = mapped_column(String(16), default="cpu")
    transcription_compute_type: Mapped[str] = mapped_column(String(16), default="int8")
    transcription_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    pipeline_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_runs.id"))

    competitor: Mapped[Competitor] = relationship(Competitor)
    analysis: Mapped["ReelAnalysis | None"] = relationship("ReelAnalysis", uselist=False, back_populates="reel")


class ReelAnalysis(Base):
    __tablename__ = "reel_analyses"

    reel_id: Mapped[str] = mapped_column(String(36), ForeignKey("reels.id"), primary_key=True)
    relevance_score: Mapped[int] = mapped_column(Integer)
    verdict: Mapped[bool] = mapped_column(Boolean)
    topic: Mapped[str] = mapped_column(String(120))
    hook_style: Mapped[str] = mapped_column(String(32))
    reasoning: Mapped[str] = mapped_column(Text)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    angle_suggestion: Mapped[str] = mapped_column(Text)
    research: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)
    analysis_model: Mapped[str] = mapped_column(String(64))
    analysis_provider: Mapped[str] = mapped_column(String(64))

    reel: Mapped[Reel] = relationship(Reel, back_populates="analysis")


Index("ix_reel_analyses_score", ReelAnalysis.relevance_score)
Index("ix_reels_views", Reel.views.desc())
