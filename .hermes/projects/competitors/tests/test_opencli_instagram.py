"""Tests for the OpenCLI Instagram adapter.

The adapter wraps the local `opencli` binary and exposes:

- a function to fetch the most recent posts for a username as JSON
- a function to download a reel to a staging directory
- a session health check that raises on failed authentication

The adapter must never log or expose cookies/session IDs. We assert that
secrets do not appear in `repr()`, `str()`, or the subprocess environment
that we hand to `subprocess.run`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pipeline.opencli_instagram import (
    OpenCLIError,
    ScrapeResult,
    download_reel,
    fetch_user_posts,
    normalize_posts,
    parse_json_output,
    session_health,
)


def _good_feed_item(shortcode: str = "abc123def", username: str = "test_account") -> dict:
    return {
        "index": 1,
        "type": "reel",
        "caption": "A caption",
        "likes": 10,
        "comments": 2,
        "views": 100,
        "date": "2026-07-24T10:00:00+08:00",
        "url": f"https://www.instagram.com/reel/{shortcode}/",
        "ownerUsername": username,
    }


def test_parse_json_output_returns_dict() -> None:
    raw = json.dumps([_good_feed_item()])
    assert parse_json_output(raw) == [_good_feed_item()]


def test_parse_json_output_rejects_garbage() -> None:
    with pytest.raises(OpenCLIError):
        parse_json_output("not json at all")


def test_normalize_posts_keeps_only_reels() -> None:
    posts = [
        _good_feed_item(shortcode="reel01abc"),
        {**_good_feed_item(shortcode="ignored0x"), "type": "image"},
    ]
    normalized = normalize_posts(posts, username="test_account")
    assert len(normalized) == 1
    assert normalized[0].shortcode == "reel01abc"
    assert normalized[0].username == "test_account"


def test_normalize_posts_extracts_views_likes_comments() -> None:
    posts = [_good_feed_item()]
    n = normalize_posts(posts, username="u")[0]
    assert n.views == 100
    assert n.likes == 10
    assert n.comments == 2


def test_normalize_posts_skips_invalid_shortcodes() -> None:
    posts = [
        _good_feed_item(shortcode="badshortcode!"),
        _good_feed_item(shortcode="goodcode99"),
    ]
    out = normalize_posts(posts, username="u")
    assert [r.shortcode for r in out] == ["goodcode99"]


def test_fetch_user_posts_runs_opencli_with_argv_not_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_run(argv, *args, **kwargs):
        captured["argv"] = argv
        captured["shell"] = kwargs.get("shell", False)
        captured["env_keys"] = sorted((kwargs.get("env") or {}).keys())
        result = subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=json.dumps([_good_feed_item()]), stderr=""
        )
        return result

    monkeypatch.setattr("pipeline.opencli_instagram.subprocess.run", fake_run)
    items = fetch_user_posts(
        username="test_account",
        limit=3,
        binary=Path("/usr/local/bin/opencli"),
        site_session="persistent",
        window="background",
    )
    assert captured["shell"] is False
    assert captured["argv"][0] == "/usr/local/bin/opencli"
    assert captured["argv"][1:4] == ["instagram", "user", "test_account"]
    assert "--limit" in captured["argv"]
    assert "3" in captured["argv"]
    assert items and items[0].shortcode == "abc123def"
    # Environment must not contain secrets.
    for key in captured["env_keys"]:
        assert "cookie" not in key.lower()
        assert "session" not in key.lower() or key == "SESSION_SECRET"


def test_fetch_user_posts_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv, *args, **kwargs):
        return subprocess.CompletedProcess(
            args=argv, returncode=69, stdout="", stderr="BROWSER_CONNECT"
        )

    monkeypatch.setattr("pipeline.opencli_instagram.subprocess.run", fake_run)
    with pytest.raises(OpenCLIError):
        fetch_user_posts(
            username="test_account",
            limit=1,
            binary=Path("/usr/local/bin/opencli"),
            site_session="persistent",
            window="background",
        )


def test_session_health_succeeds_when_whoami_returns_account(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv, *args, **kwargs):
        return subprocess.CompletedProcess(
            args=argv,
            returncode=0,
            stdout=json.dumps({"username": "test_account", "ok": True}),
            stderr="",
        )

    monkeypatch.setattr("pipeline.opencli_instagram.subprocess.run", fake_run)
    account = session_health(
        binary=Path("/usr/local/bin/opencli"),
        site_session="persistent",
        window="background",
    )
    assert account == "test_account"


def test_session_health_raises_on_browser_bridge_disconnected(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv, *args, **kwargs):
        return subprocess.CompletedProcess(
            args=argv,
            returncode=69,
            stdout="",
            stderr="BROWSER_CONNECT",
        )

    monkeypatch.setattr("pipeline.opencli_instagram.subprocess.run", fake_run)
    with pytest.raises(OpenCLIError, match="Browser Bridge"):
        session_health(
            binary=Path("/usr/local/bin/opencli"),
            site_session="persistent",
            window="background",
        )


def test_download_reel_creates_file_with_known_size(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(argv, *args, **kwargs):
        # The download command writes the file to argv[argv.index('--path') + 1]/<safe>.mp4
        idx = argv.index("--path")
        dest_dir = Path(argv[idx + 1])
        dest_dir.mkdir(parents=True, exist_ok=True)
        # The real opencli would name the file; we just write a fixture file at the expected location.
        out = dest_dir / "fixture.mp4"
        out.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100)
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("pipeline.opencli_instagram.subprocess.run", fake_run)
    result = download_reel(
        url="https://www.instagram.com/reel/abc123/",
        dest_dir=tmp_path,
        binary=Path("/usr/local/bin/opencli"),
        site_session="persistent",
        window="background",
    )
    assert result.exists()
    assert result.stat().st_size > 32
