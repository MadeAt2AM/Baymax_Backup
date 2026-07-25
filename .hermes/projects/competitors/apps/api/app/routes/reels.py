"""Reel list and detail endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc

from .. import auth as auth_module
from ..db import session_scope
from ..models import Reel, ReelAnalysis


router = APIRouter()


@router.get("/api/reels")
def list_reels(
    _user: Annotated[dict, Depends(auth_module.require_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    account: str | None = None,
    hook_style: str | None = None,
    score_min: int | None = Query(None, ge=1, le=10),
    q: str | None = None,
) -> dict:
    with session_scope() as s:
        query = (
            s.query(Reel, ReelAnalysis)
            .join(ReelAnalysis, ReelAnalysis.reel_id == Reel.id)
            .filter(ReelAnalysis.verdict.is_(True))
        )
        if account:
            query = query.filter(Reel.source_url.like(f"%/{account.lower()}/%"))
        if hook_style:
            query = query.filter(ReelAnalysis.hook_style == hook_style)
        if score_min is not None:
            query = query.filter(ReelAnalysis.relevance_score >= score_min)
        if q:
            needle = f"%{q.lower()}%"
            query = query.filter(
                (Reel.caption.ilike(needle)) | (ReelAnalysis.topic.ilike(needle))
            )
        total = query.count()
        rows = (
            query.order_by(desc(Reel.views))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        items = []
        for reel, analysis in rows:
            items.append(
                {
                    "id": reel.id,
                    "shortcode": reel.shortcode,
                    "source_url": reel.source_url,
                    "views": reel.views,
                    "likes": reel.likes,
                    "comments": reel.comments,
                    "scraped_at": reel.scraped_at.isoformat() if reel.scraped_at else None,
                    "analysis": {
                        "topic": analysis.topic,
                        "hook_style": analysis.hook_style,
                        "relevance_score": analysis.relevance_score,
                        "verdict": analysis.verdict,
                    },
                }
            )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/api/reels/{reel_id}")
def reel_detail(
    reel_id: str,
    _user: Annotated[dict, Depends(auth_module.require_user)],
) -> dict:
    with session_scope() as s:
        reel = s.query(Reel).filter(Reel.id == reel_id).one_or_none()
        if reel is None:
            raise HTTPException(status_code=404, detail="not found")
        analysis = s.query(ReelAnalysis).filter(ReelAnalysis.reel_id == reel_id).one_or_none()
        if analysis is None:
            raise HTTPException(status_code=404, detail="not found")
        return {
            "id": reel.id,
            "source": {
                "shortcode": reel.shortcode,
                "url": reel.source_url,
                "views": reel.views,
                "likes": reel.likes,
                "comments": reel.comments,
                "caption": reel.caption,
                "transcript": reel.transcript,
                "scraped_at": reel.scraped_at.isoformat() if reel.scraped_at else None,
            },
            "analysis": {
                "topic": analysis.topic,
                "hook_style": analysis.hook_style,
                "relevance_score": analysis.relevance_score,
                "verdict": analysis.verdict,
                "reasoning": analysis.reasoning,
                "sections": analysis.sections,
                "tools": analysis.tools,
                "research": analysis.research,
                "angle_suggestion": analysis.angle_suggestion,
                "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
                "model": {
                    "provider": analysis.analysis_provider,
                    "model": analysis.analysis_model,
                },
            },
        }
