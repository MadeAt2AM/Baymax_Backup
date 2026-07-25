"""Shared fixtures for the API tests.

The tests use an in-memory SQLite database by default. The schema is
created once per test via the SQLAlchemy metadata. The goal is to prove
the application's logic; the production path uses PostgreSQL.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import bcrypt
import pytest
from fastapi.testclient import TestClient


_API_DIR = Path(__file__).resolve().parent.parent
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))


def _purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


@pytest.fixture()
def app_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a fresh app + DB per test, with a single seeded operator user."""

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SESSION_SECRET", "test-secret-32-bytes-1234567890abcdef")
    monkeypatch.setenv("DASHBOARD_USERNAME", "operator")
    seed = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt(rounds=4)).decode("utf-8")
    monkeypatch.setenv("DASHBOARD_PASSWORD_HASH", seed)
    monkeypatch.setenv("APP_ORIGIN", "http://testserver")

    _purge_app_modules()
    main_module = importlib.import_module("app.main")
    app = main_module.app

    return app


@pytest.fixture()
def client(app_db) -> TestClient:
    return TestClient(app_db)
