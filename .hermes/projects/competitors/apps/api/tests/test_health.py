"""Tests for the public /api/healthz endpoint."""

from __future__ import annotations


def test_healthz_returns_200_when_db_alive(client) -> None:
    r = client.get("/api/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "db" in body
    assert "version" in body
    # No secrets in the response.
    text = r.text.lower()
    for forbidden in ("password", "secret", "session_", "cookie"):
        assert forbidden not in text
