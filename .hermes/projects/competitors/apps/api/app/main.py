"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import __version__
from .config import load_config
from .db import init_db, init_engine, upsert_user
from .routes import auth as auth_routes
from .routes import dashboard as dashboard_routes
from .routes import health as health_routes
from .routes import reels as reels_routes
from .routes import runs as runs_routes
from .routes import instagram_auth as instagram_auth_routes


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""

    app = FastAPI(title="Competitors Intelligence Dashboard", version=__version__)
    cfg = load_config()
    init_engine(cfg)
    init_db()
    upsert_user(cfg.dashboard_username, cfg.dashboard_password_hash)

    @app.exception_handler(Exception)
    def _unhandled(_request, exc: Exception) -> JSONResponse:
        # Never expose internal details.
        return JSONResponse(status_code=500, content={"status": "error"})

    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(dashboard_routes.router)
    app.include_router(reels_routes.router)
    app.include_router(runs_routes.router)
    app.include_router(instagram_auth_routes.router)
    return app


app = create_app()
