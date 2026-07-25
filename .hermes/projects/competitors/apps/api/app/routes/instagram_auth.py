"""HTTP routes for the in-dashboard Instagram auth flow."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth as auth_module
from .. import auth_instagram


router = APIRouter()


class StartReauthResponse(BaseModel):
    token: str
    expires_at: float
    approved_account: str


class CompleteReauthRequest(BaseModel):
    state: str
    sessionid: str
    ds_user_id: str


class StatusResponse(BaseModel):
    state: str
    authenticated_account: str | None
    approved_account: str | None
    last_checked_at: str
    message: str


class LogoutResponse(BaseModel):
    state: str


@router.get("/api/auth/instagram/status", response_model=StatusResponse)
def instagram_status(
    _user: Annotated[dict, Depends(auth_module.require_user)],
) -> StatusResponse:
    s = auth_instagram.status()
    return StatusResponse(
        state=s.state,
        authenticated_account=s.authenticated_account,
        approved_account=s.approved_account,
        last_checked_at=s.last_checked_at,
        message=s.message,
    )


@router.post("/api/auth/instagram/start", response_model=StartReauthResponse)
def instagram_start(
    _user: Annotated[dict, Depends(auth_module.require_user)],
) -> StartReauthResponse:
    try:
        handle = auth_instagram.start_reauth()
    except auth_instagram.ValidationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return StartReauthResponse(
        token=handle.token,
        expires_at=handle.expires_at,
        approved_account=handle.approved_account,
    )


@router.post("/api/auth/instagram/complete")
def instagram_complete(
    body: CompleteReauthRequest,
    _user: Annotated[dict, Depends(auth_module.require_user)],
) -> dict:
    try:
        result = auth_instagram.complete_reauth(
            state=body.state,
            sessionid=body.sessionid,
            ds_user_id=body.ds_user_id,
        )
    except auth_instagram.StateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except auth_instagram.ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except auth_instagram.BootstrapError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "state": result.state,
        "authenticated_account": result.authenticated_account,
        "approved_account": result.approved_account,
    }


@router.post("/api/auth/instagram/logout", response_model=LogoutResponse)
def instagram_logout(
    _user: Annotated[dict, Depends(auth_module.require_user)],
) -> LogoutResponse:
    auth_instagram.logout()
    return LogoutResponse(state="ok")
