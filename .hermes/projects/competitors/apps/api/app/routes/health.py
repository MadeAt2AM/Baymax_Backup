"""Routes for the public health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text

from .. import __version__
from ..db import session_scope

router = APIRouter()


@router.get("/api/healthz")
def healthz() -> dict:
    """Return liveness + readiness without exposing secrets."""

    try:
        with session_scope() as s:
            s.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unavailable"
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status, "version": __version__}
