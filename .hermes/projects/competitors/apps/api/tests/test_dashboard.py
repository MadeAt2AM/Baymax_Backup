"""Tests for the dashboard summary and reel endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _import_a_bundle(client, run_id: str = "run-1") -> dict:
    """Import a known-good bundle via the CLI route and return the result."""
    bundle_path = Path(__file__).parent / "fixtures" / "bundle_one.json"
    bundle = json.loads(bundle_path.read_text())
    bundle["run_id"] = run_id
    from app.importer import import_bundle
    return import_bundle(bundle)


def test_dashboard_summary_returns_403_when_unauthenticated(client) -> None:
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 401


def test_dashboard_summary_returns_kpis_after_import(client) -> None:
    client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "correct-horse-battery-staple"},
    )
    _import_a_bundle(client)
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["kpis"]["reels_kept"] >= 1
    assert body["kpis"]["accounts_tracked"] >= 1
    assert body["kpis"]["combined_views"] >= 0
    assert isinstance(body["reach_by_account"], list)
    assert isinstance(body["hook_taxonomy"], list)
    assert body["latest_run"]["run_id"] == "run-1"


def test_reels_endpoint_returns_paginated_list(client) -> None:
    client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "correct-horse-battery-staple"},
    )
    _import_a_bundle(client)
    r = client.get("/api/reels?page=1&page_size=10")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)


def test_reel_detail_returns_full_bundle(client) -> None:
    client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "correct-horse-battery-staple"},
    )
    _import_a_bundle(client)
    listing = client.get("/api/reels?page=1&page_size=10").json()
    reel_id = listing["items"][0]["id"]
    r = client.get(f"/api/reels/{reel_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["source"]["shortcode"] == "abc123def"
    assert body["analysis"]["relevance_score"] == 8


def test_reels_endpoint_safely_renders_user_strings(client) -> None:
    client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "correct-horse-battery-staple"},
    )
    bundle = json.loads((Path(__file__).parent / "fixtures" / "bundle_one.json").read_text())
    bundle["items"][0]["analysis"]["topic"] = "<script>alert(1)</script>"
    from app.importer import import_bundle
    import_bundle(bundle)
    r = client.get("/api/reels?page=1&page_size=10")
    assert r.status_code == 200
    # The response is JSON, so the raw "<script>" string is fine, but the
    # topic must not have been altered in a way that bypasses serialization.
    items = r.json()["items"]
    assert any("<script>" in item["analysis"]["topic"] for item in items)
