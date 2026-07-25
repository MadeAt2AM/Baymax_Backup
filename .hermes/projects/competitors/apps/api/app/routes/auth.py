"""Authentication routes — single-operator login/logout/me."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from .. import auth as auth_module
from ..config import Config, load_config


router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    username: str


class StatusResponse(BaseModel):
    status: str


def _cookie_secure(cfg: Config) -> bool:
    return cfg.app_origin.lower().startswith("https://")


@router.post("/api/auth/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    cfg: Annotated[Config, Depends(load_config)],
) -> LoginResponse:
    auth_module.check_rate_limit(request)
    if body.username != cfg.dashboard_username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    if not auth_module.verify_password(body.password, cfg.dashboard_password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    token = auth_module.issue_session(cfg, body.username)
    response.set_cookie(
        key=cfg.session_cookie_name,
        value=token,
        max_age=cfg.session_ttl_seconds,
        httponly=True,
        secure=_cookie_secure(cfg),
        samesite="lax",
        path="/",
    )
    return LoginResponse(username=body.username)


@router.post("/api/auth/logout", response_model=StatusResponse)
def logout(response: Response, cfg: Annotated[Config, Depends(load_config)]) -> StatusResponse:
    response.delete_cookie(cfg.session_cookie_name, path="/")
    return StatusResponse(status="ok")


@router.get("/api/auth/me", response_model=LoginResponse)
def me(user: Annotated[dict, Depends(auth_module.require_user)]) -> LoginResponse:
    return LoginResponse(username=user["u"])
