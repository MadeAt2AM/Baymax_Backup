"""Dashboard summary endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func

from .. import auth as auth_module
from ..db import session_scope
from ..models import Competitor, PipelineRun, Reel, ReelAnalysis


router = APIRouter()


@router.get("/api/dashboard/summary")
def summary(_user: Annotated[dict, Depends(auth_module.require_user)]) -> dict:
    """Aggregate KPIs, reach, taxonomy, and the latest run."""

    with session_scope() as s:
        total_reels = (
            s.query(func.count(Reel.id))
            .join(ReelAnalysis, ReelAnalysis.reel_id == Reel.id)
            .filter(ReelAnalysis.verdict.is_(True))
            .scalar()
            or 0
        )
        total_combined_views = (
            s.query(func.coalesce(func.sum(Reel.views), 0))
            .join(ReelAnalysis, ReelAnalysis.reel_id == Reel.id)
            .filter(ReelAnalysis.verdict.is_(True))
            .scalar()
            or 0
        )
        top_reel = (
            s.query(Reel.views)
            .join(ReelAnalysis, ReelAnalysis.reel_id == Reel.id)
            .filter(ReelAnalysis.verdict.is_(True))
            .order_by(Reel.views.desc())
            .first()
        )
        top_views = top_reel[0] if top_reel else 0

        accounts = (
            s.query(Competitor)
            .join(Reel, Reel.competitor_id == Competitor.id)
            .join(ReelAnalysis, ReelAnalysis.reel_id == Reel.id)
            .filter(ReelAnalysis.verdict.is_(True))
            .distinct()
            .all()
        )
        reach_by_account = []
        for acct in accounts:
            reach = (
                s.query(
                    func.coalesce(func.sum(Reel.views), 0),
                    func.count(Reel.id),
                )
                .join(ReelAnalysis, ReelAnalysis.reel_id == Reel.id)
                .filter(Reel.competitor_id == acct.id, ReelAnalysis.verdict.is_(True))
                .one()
            )
            reach_by_account.append(
                {"account": acct.username, "views": int(reach[0] or 0), "reels": int(reach[1] or 0)}
            )
        reach_by_account.sort(key=lambda r: r["views"], reverse=True)

        taxonomy_rows = (
            s.query(
                ReelAnalysis.hook_style,
                func.count(Reel.id),
                func.coalesce(func.sum(Reel.views), 0),
            )
            .join(Reel, Reel.id == ReelAnalysis.reel_id)
            .filter(ReelAnalysis.verdict.is_(True))
            .group_by(ReelAnalysis.hook_style)
            .all()
        )
        hook_taxonomy = [
            {"hook_style": row[0], "count": int(row[1] or 0), "combined_views": int(row[2] or 0)}
            for row in taxonomy_rows
        ]
        hook_taxonomy.sort(key=lambda r: r["combined_views"], reverse=True)

        top_hook = max(hook_taxonomy, key=lambda r: r["count"]) if hook_taxonomy else None

        latest_run = (
            s.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()
        )
        latest_run_payload = None
        if latest_run is not None:
            latest_run_payload = {
                "run_id": latest_run.run_key,
                "started_at": latest_run.started_at.isoformat() if latest_run.started_at else None,
                "finished_at": latest_run.finished_at.isoformat() if latest_run.finished_at else None,
                "status": latest_run.status,
                "scraped_count": latest_run.scraped_count,
                "analyzed_count": latest_run.analyzed_count,
                "kept_count": latest_run.kept_count,
                "rejected_count": latest_run.rejected_count,
                "failed_count": latest_run.failed_count,
            }

    return {
        "kpis": {
            "reels_kept": int(total_reels or 0),
            "accounts_tracked": len(reach_by_account),
            "combined_views": int(total_combined_views or 0),
            "top_reel_views": int(top_views or 0),
            "top_hook_style": top_hook["hook_style"] if top_hook else None,
        },
        "reach_by_account": reach_by_account,
        "hook_taxonomy": hook_taxonomy,
        "latest_run": latest_run_payload,
    }
