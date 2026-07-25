"""Tests for the operator CLI."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture
def sqlite_db(tmp_path):
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    return url


def _run_cli(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(os.path.dirname(api_dir))
    # The `app` package lives under apps/api/. We add both the api dir
    # (so `app.cli` resolves) and the repo root (so the `pipeline`
    # package is importable) to PYTHONPATH. The api dir must come
    # first so the local app wins over any installed package of the
    # same name.
    api_dir = os.path.join(repo_root, "apps", "api")
    env = {**env, "PYTHONPATH": api_dir + os.pathsep + repo_root}
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        cwd=api_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_create_user_persists_record(sqlite_db, tmp_path):
    env = os.environ.copy()
    env["DATABASE_URL"] = sqlite_db
    username = "operator-" + uuid.uuid4().hex[:8]
    password = "secret-password"
    result = _run_cli(["create-user", "--username", username, "--password", password], env)
    assert result.returncode == 0, result.stderr
    assert "created user" in result.stdout
    # Verify the row exists with a bcrypt hash.
    engine = create_engine(sqlite_db)
    with engine.connect() as conn:
        row = conn.execute(
            text("select username, password_hash from users where username = :u"),
            {"u": username},
        ).first()
    assert row is not None
    assert row[0] == username
    assert row[1].startswith("$2")


def test_create_user_is_idempotent_on_existing_username(sqlite_db):
    env = os.environ.copy()
    env["DATABASE_URL"] = sqlite_db
    username = "dup-user"
    password = "password"
    result = _run_cli(["create-user", "--username", username, "--password", password], env)
    assert result.returncode == 0
    result2 = _run_cli(["create-user", "--username", username, "--password", password], env)
    assert result2.returncode == 0
    assert "already exists" in result2.stdout


def test_create_user_missing_password_raises(sqlite_db):
    env = os.environ.copy()
    env["DATABASE_URL"] = sqlite_db
    result = _run_cli(["create-user", "--username", "x"], env)
    assert result.returncode != 0


def test_cli_fails_without_database_url(tmp_path):
    env = {"PATH": os.environ.get("PATH", "")}
    env.pop("DATABASE_URL", None)
    result = _run_cli(["create-user", "--username", "x", "--password", "y"], env)
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr


def test_list_users_returns_created_users(sqlite_db):
    env = os.environ.copy()
    env["DATABASE_URL"] = sqlite_db
    u1 = "u1-" + uuid.uuid4().hex[:6]
    u2 = "u2-" + uuid.uuid4().hex[:6]
    _run_cli(["create-user", "--username", u1, "--password", "pw"], env)
    _run_cli(["create-user", "--username", u2, "--password", "pw"], env)
    result = _run_cli(["list-users"], env)
    assert result.returncode == 0
    assert u1 in result.stdout
    assert u2 in result.stdout
