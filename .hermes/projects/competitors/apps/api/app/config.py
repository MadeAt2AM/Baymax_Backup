"""Application configuration loaded from environment variables.

The configuration is intentionally narrow: every value is required to be
explicit, and the loader refuses to start if a critical value is missing.

The first-user credentials are stored as a bcrypt hash. The plaintext
password is never written to disk by the application.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Config:
    database_url: str
    session_secret: str
    dashboard_username: str
    dashboard_password_hash: str
    app_origin: str
    login_rate_limit_per_minute: int = 5
    session_cookie_name: str = "competitors_session"
    session_ttl_seconds: int = 60 * 60 * 8  # 8 hours


def load_config() -> Config:
    """Load the configuration from environment variables.

    A 32-byte random session secret is generated if missing. This is
    acceptable for `localhost` development but **not** for production.
    """

    secret = os.environ.get("SESSION_SECRET", "").strip()
    if not secret:
        secret = secrets.token_hex(32)
    password_hash = os.environ.get("DASHBOARD_PASSWORD_HASH", "").strip()
    username = os.environ.get("DASHBOARD_USERNAME", "").strip()
    if not username:
        raise RuntimeError("DASHBOARD_USERNAME must be set")
    if not password_hash:
        raise RuntimeError("DASHBOARD_PASSWORD_HASH must be set")
    return Config(
        database_url=_require("DATABASE_URL"),
        session_secret=secret,
        dashboard_username=username,
        dashboard_password_hash=password_hash,
        app_origin=os.environ.get("APP_ORIGIN", "https://competitors.terrybot.top").strip(),
    )
