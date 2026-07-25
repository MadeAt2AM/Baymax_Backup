"""Publish-bundle importer.

The importer is a single transactional function. It is called by:

- the container-only CLI `python -m app.importer /imports/<bundle>.json`,
- the FastAPI route `/api/imports` (container-only).

The importer validates the bundle via the `AnalysisBundle` model, then
upserts each reel + analysis pair in a single transaction. Duplicates are
detected via the unique `shortcode` index.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

try:
    from ..pipeline.models import AnalysisBundle  # type: ignore
except ImportError:
    import sys as _sys
    from pathlib import Path as _P
    _root = str(_P(__file__).resolve().parents[2])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    from pipeline.models import AnalysisBundle  # type: ignore
from .db import session_scope
from .models import Competitor, PipelineRun, Reel, ReelAnalysis


@dataclass
class ImportResult:
    status: str
    run_id: str
    reel_count: int
    analysis_count: int


def _parse_bundle(bundle: dict) -> tuple[str, list[AnalysisBundle]]:
    run_id = (bundle.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("bundle missing run_id")
    items = bundle.get("items") or []
    if not isinstance(items, list):
        raise ValueError("bundle items must be a list")
    parsed: list[AnalysisBundle] = []
    for idx, item in enumerate(items):
        try:
            parsed.append(AnalysisBundle.model_validate(item))
        except ValidationError as exc:
            raise ValueError(f"items[{idx}]: {exc}") from exc
    return run_id, parsed


def _upsert_competitor(s, username: str) -> Competitor:
    existing = s.query(Competitor).filter(Competitor.username == username).one_or_none()
    if existing is not None:
        return existing
    competitor = Competitor(username=username, display_name=None, niche_reason=None, active=True)
    s.add(competitor)
    s.flush()
    return competitor


def _upsert_run(s, run_id: str) -> PipelineRun:
    existing = s.query(PipelineRun).filter(PipelineRun.run_key == run_id).one_or_none()
    if existing is not None:
        return existing
    run = PipelineRun(run_key=run_id, status="publishing")
    s.add(run)
    s.flush()
    return run


def import_bundle(bundle: dict) -> ImportResult:
    """Import one publish bundle transactionally."""

    run_id, items = _parse_bundle(bundle)
    if not items:
        return ImportResult(status="empty", run_id=run_id, reel_count=0, analysis_count=0)

    with session_scope() as s:
        run = _upsert_run(s, run_id)
        reel_count = 0
        analysis_count = 0
        for item in items:
            src = item.source
            competitor = _upsert_competitor(s, src.username)
            existing = s.query(Reel).filter(Reel.shortcode == src.shortcode).one_or_none()
            if existing is not None:
                continue
            reel = Reel(
                shortcode=src.shortcode,
                competitor_id=competitor.id,
                source_url=src.url,
                caption=src.caption,
                views=src.views,
                likes=src.likes,
                comments=src.comments,
                published_at=src.scraped_at,
                scraped_at=src.scraped_at,
                transcript="",
                transcript_status="complete",
                pipeline_run_id=run.id,
            )
            s.add(reel)
            s.flush()
            analysis = ReelAnalysis(
                reel_id=reel.id,
                relevance_score=item.analysis.relevance_score,
                verdict=item.analysis.verdict,
                topic=item.analysis.topic,
                hook_style=item.analysis.hook_style.value,
                reasoning=item.analysis.reasoning,
                sections=[s.model_dump() for s in item.analysis.sections],
                tools=list(item.analysis.tools),
                angle_suggestion=item.analysis.angle_suggestion,
                research=[r.model_dump() for r in item.analysis.research],
                analysis_model=item.model.model,
                analysis_provider=item.model.provider,
            )
            s.add(analysis)
            reel_count += 1
            analysis_count += 1

        if reel_count == 0:
            return ImportResult(
                status="already_imported",
                run_id=run_id,
                reel_count=0,
                analysis_count=0,
            )

        run.status = "completed"
        run.kept_count = reel_count
        s.flush()
        return ImportResult(
            status="imported",
            run_id=run_id,
            reel_count=reel_count,
            analysis_count=analysis_count,
        )


def import_bundle_from_path(path: Path) -> ImportResult:
    """Read a bundle from disk and import it. Container-only entry point."""

    bundle = json.loads(path.read_text(encoding="utf-8"))
    return import_bundle(bundle)


if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) != 2:
        print("usage: python -m app.importer <bundle.json>", file=sys.stderr)
        raise SystemExit(2)
    result = import_bundle_from_path(Path(sys.argv[1]))
    print(json.dumps(result.__dict__))
