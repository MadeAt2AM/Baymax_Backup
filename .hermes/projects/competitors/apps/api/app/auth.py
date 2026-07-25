"""Single-operator authentication.

The auth flow is intentionally minimal:

- One user, seeded from environment variables.
- bcrypt password verification.
- Signed session cookie via itsdangerous.
- Rate-limited login attempts (5 per minute per IP).
- HTTPOnly, Secure, SameSite=Lax cookie, scoped to the app origin.
"""

from __future__ import annotations

import time
from typing import Annotated

import bcrypt
from fastapi import Cookie, Depends, HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeSerializer

from .config import Config, load_config


_login_attempts: dict[str, list[float]] = {}


def _rate_limit_key(request: Request) -> str:
    client = request.client
    if client is None:
        return "unknown"
    return client.host


def check_rate_limit(request: Request) -> None:
    """In-memory rate limiter. 5 attempts per minute per IP."""

    cfg = load_config()
    key = _rate_limit_key(request)
    now = time.monotonic()
    window = [t for t in _login_attempts.get(key, []) if now - t < 60.0]
    if len(window) >= cfg.login_rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate limited",
        )
    window.append(now)
    _login_attempts[key] = window


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def make_serializer(cfg: Config) -> URLSafeSerializer:
    return URLSafeSerializer(cfg.session_secret, salt="competitors-session")


def issue_session(cfg: Config, username: str) -> str:
    return make_serializer(cfg).dumps({"u": username, "t": int(time.time())})


def read_session(cfg: Config, value: str) -> dict | None:
    try:
        data = make_serializer(cfg).loads(value)
    except BadSignature:
        return None
    if not isinstance(data, dict) or "u" not in data:
        return None
    issued = int(data.get("t", 0))
    if time.time() - issued > cfg.session_ttl_seconds:
        return None
    return data


def require_user(
    request: Request,
    cfg: Annotated[Config, Depends(load_config)],
    cookie: Annotated[str | None, Cookie(alias="competitors_session")] = None,
) -> dict:
    if not cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    data = read_session(cfg, cookie)
    if not data or data.get("u") != cfg.dashboard_username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return data


def login_attempt(cfg: Config, password: str) -> bool:
    return cfg.dashboard_username and verify_password(password, cfg.dashboard_password_hash)
