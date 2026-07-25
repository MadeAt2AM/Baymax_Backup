"""Tests for the single-operator auth flow."""

from __future__ import annotations


def test_login_success_sets_secure_cookie(client) -> None:
    r = client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "correct-horse-battery-staple"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "operator"
    # Cookie attributes.
    set_cookie = r.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "samesite=lax" in set_cookie.lower()
    # Path is scoped to the app.
    assert "Path=/" in set_cookie


def test_login_rejects_wrong_password(client) -> None:
    r = client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "wrong-password"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "unauthorized"


def test_me_returns_401_when_unauthenticated(client) -> None:
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_returns_user_when_authenticated(client) -> None:
    client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "correct-horse-battery-staple"},
    )
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["username"] == "operator"


def test_logout_clears_session(client) -> None:
    client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "correct-horse-battery-staple"},
    )
    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_login_rate_limit_returns_429_after_threshold(client) -> None:
    # 5 attempts are allowed; the 6th must be rejected.
    for _ in range(5):
        client.post(
            "/api/auth/login",
            json={"username": "operator", "password": "wrong"},
        )
    r = client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "wrong"},
    )
    assert r.status_code == 429
