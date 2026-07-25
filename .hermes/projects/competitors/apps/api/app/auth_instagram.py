"""In-dashboard Instagram auth flow.

This module exposes four functions:

- `status()` — query the current OpenCLI `whoami` state and return a
  structured status with no cookie values.
- `start_reauth()` — issue a one-time, time-limited state token.
- `complete_reauth(state, sessionid, ds_user_id)` — validate the
  state token, validate the cookies, write them to the OpenCLI
  site-session file, and verify the session via `whoami`.
- `logout()` — clear the OpenCLI site-session file.

The module is the single source of truth for the in-dashboard login UX.
The API routes are a thin wrapper around these functions.

The cookies are never returned to the caller and never written to logs.
The state token is single-use and short-lived (10 minutes).
"""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

try:
    from ..pipeline import bootstrap_session  # type: ignore
except ImportError:
    import sys as _sys
    from pathlib import Path as _P
    _root = str(_P(__file__).resolve().parents[2])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    from pipeline import bootstrap_session  # type: ignore


# -- Errors ----------------------------------------------------------------


class StateError(RuntimeError):
    """The state token is missing, expired, or already consumed."""


class ValidationError(RuntimeError):
    """The supplied cookies or state are malformed."""


class BootstrapError(RuntimeError):
    """The OpenCLI bootstrap step failed (e.g. whoami returned an error)."""


# Re-export the pipeline BootstrapError as well so callers can catch either.
_pipeline_bootstrap_error = getattr(bootstrap_session, "BootstrapError", None)
if _pipeline_bootstrap_error is not None:
    BootstrapError = _pipeline_bootstrap_error  # type: ignore[misc]


# -- State token store -----------------------------------------------------

_STATE_TTL_SECONDS = 600.0  # 10 minutes


@dataclass
class PendingState:
    token: str
    issued_at: float
    ttl_seconds: float
    approved_account: str


@dataclass
class StateHandle:
    token: str
    expires_at: float
    approved_account: str


_STATE_TOKENS: dict[str, PendingState] = {}


# -- Cookie validation -----------------------------------------------------

_SESSIONID_RE = re.compile(r"^[A-Za-z0-9%._\-]{32,512}$")
_DS_USER_ID_RE = re.compile(r"^[0-9]{6,20}$")


def _validate_sessionid(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("sessionid must be a string")
    # Chrome DevTools shows the cookie value URL-encoded (e.g. colons
    # as %3A). Decode before validating so the user can paste either
    # the encoded or decoded form.
    decoded = unquote(value)
    if not _SESSIONID_RE.match(decoded):
        raise ValidationError("sessionid: must be 32-512 chars, base64-ish")
    return decoded


def _validate_ds_user_id(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("ds_user_id must be a string")
    if not _DS_USER_ID_RE.match(value):
        raise ValidationError("ds_user_id: must be 6-20 digits")
    return value


# -- Public API ------------------------------------------------------------


@dataclass
class Status:
    state: str
    authenticated_account: Optional[str]
    approved_account: Optional[str]
    last_checked_at: str
    message: str = ""


def status() -> Status:
    """Return the current OpenCLI `whoami` state.

    Uses `bootstrap_session.verify_bootstrap()` for the actual subprocess
    call so the test patch path is the same as the existing test suite.
    """

    from datetime import datetime, timezone, timedelta

    approved = (os.environ.get("APPROVED_INSTAGRAM_ACCOUNT") or "").strip().lower().lstrip("@")
    sgt = timezone(timedelta(hours=8))
    last = datetime.now(sgt).isoformat(timespec="seconds")
    if not approved:
        return Status(
            state="no-check-yet",
            authenticated_account=None,
            approved_account=None,
            last_checked_at=last,
            message="APPROVED_INSTAGRAM_ACCOUNT is not set",
        )
    # Note: we don't gate on cookies file existence here. OpenCLI's
    # `whoami` is the single source of truth — the Browser Bridge or a
    # transferred Chrome profile can succeed even without a cookies file
    # that this module wrote.
    try:
        account = bootstrap_session.probe_whoami(opencli=Path("/usr/local/bin/opencli"))
    except bootstrap_session.BootstrapError as exc:
        msg = str(exc)
        if "Browser Bridge" in msg or "BROWSER_CONNECT" in msg:
            return Status(
                state="browser-bridge-disconnected",
                authenticated_account=None,
                approved_account=approved,
                last_checked_at=last,
                message=msg,
            )
        return Status(
            state="error",
            authenticated_account=None,
            approved_account=approved,
            last_checked_at=last,
            message=msg,
        )
    if account != approved:
        return Status(
            state="wrong-account",
            authenticated_account=account,
            approved_account=approved,
            last_checked_at=last,
            message=f"opencli authenticated as {account!r}, but the approved account is {approved!r}.",
        )
    return Status(
        state="ok",
        authenticated_account=account,
        approved_account=approved,
        last_checked_at=last,
        message="ok",
    )


@dataclass
class CompleteResult:
    state: str
    authenticated_account: Optional[str]
    approved_account: Optional[str]
    message: str = ""


def start_reauth() -> StateHandle:
    """Issue a one-time, time-limited state token."""

    approved = (os.environ.get("APPROVED_INSTAGRAM_ACCOUNT") or "").strip().lower().lstrip("@")
    if not approved:
        raise ValidationError("APPROVED_INSTAGRAM_ACCOUNT must be set on the dev VPS")
    token = secrets.token_urlsafe(32)
    pending = PendingState(
        token=token,
        issued_at=time.time(),
        ttl_seconds=_STATE_TTL_SECONDS,
        approved_account=approved,
    )
    _STATE_TOKENS[token] = pending
    return StateHandle(
        token=token,
        expires_at=pending.issued_at + pending.ttl_seconds,
        approved_account=approved,
    )


def _consume_state(token: object, expected_approved: str) -> PendingState:
    if not isinstance(token, str) or not token:
        raise StateError("state token missing")
    pending = _STATE_TOKENS.pop(token, None)
    if pending is None:
        raise StateError("state token invalid or already consumed")
    if (time.time() - pending.issued_at) > pending.ttl_seconds:
        raise StateError("state token expired")
    if pending.approved_account != expected_approved:
        raise StateError("state token was issued for a different approved account")
    return pending


def complete_reauth(*, state: str, sessionid: str, ds_user_id: str) -> CompleteResult:
    """Validate, write, and verify a pasted cookie set."""

    # Validate state token first (cheap, in-memory).
    approved = (os.environ.get("APPROVED_INSTAGRAM_ACCOUNT") or "").strip().lower().lstrip("@")
    if not approved:
        raise ValidationError("APPROVED_INSTAGRAM_ACCOUNT must be set on the dev VPS")
    _consume_state(state, approved)

    # Validate cookies.
    sessionid = _validate_sessionid(sessionid)
    ds_user_id = _validate_ds_user_id(ds_user_id)

    # Write the OpenCLI site-session file. Refuses symlinks (asserted by tests).
    try:
        bootstrap_session.write_cookies_to_profile(sessionid=sessionid, ds_user_id=ds_user_id)
    except bootstrap_session.BootstrapError:
        raise

    # Verify the session via whoami.
    post = status()
    if post.state != "ok":
        raise BootstrapError(
            f"cookies written but whoami did not return ok: state={post.state!r}, message={post.message!r}"
        )
    return CompleteResult(
        state="ok",
        authenticated_account=post.authenticated_account,
        approved_account=post.approved_account,
        message="ok",
    )


def logout() -> bool:
    """Clear the OpenCLI site-session file. Idempotent."""

    return bootstrap_session.clear_profile()
