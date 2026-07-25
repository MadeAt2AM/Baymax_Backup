"""Pipeline run history endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc

from .. import auth as auth_module
from ..db import session_scope
from ..models import PipelineRun


router = APIRouter()


@router.get("/api/runs")
def list_runs(_user: Annotated[dict, Depends(auth_module.require_user)]) -> dict:
    with session_scope() as s:
        rows = (
            s.query(PipelineRun)
            .order_by(desc(PipelineRun.started_at))
            .limit(100)
            .all()
        )
        items = [
            {
                "run_id": r.run_key,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "status": r.status,
                "scraped_count": r.scraped_count,
                "analyzed_count": r.analyzed_count,
                "kept_count": r.kept_count,
                "rejected_count": r.rejected_count,
                "failed_count": r.failed_count,
            }
            for r in rows
        ]
    return {"items": items}
