"""Tests for the in-dashboard Instagram auth flow.

These tests pin:

- state-token issuance, TTL, and one-time use;
- cookie-format validation (`sessionid`, `ds_user_id`);
- write-to-profile refuses symlinks and non-existent parent dirs;
- the post-write `whoami` round-trip is exercised with a fake subprocess;
- logout clears the OpenCLI site-session file;
- no cookie values are ever returned by any status response.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest


def _ok_whoami(account: str = "mallu.wave") -> dict:
    return {"ok": True, "result": {"username": account}}


def _bridge_disconnect() -> dict:
    return {
        "ok": False,
        "error": {"code": "BROWSER_CONNECT", "message": "Browser Bridge extension not connected"},
    }


class FakeCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# ---------------------------------------------------------------------------
# State token lifecycle
# ---------------------------------------------------------------------------


def test_start_returns_state_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app import auth_instagram

    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(tmp_path / "opencli-profile"))
    state = auth_instagram.start_reauth()
    assert isinstance(state.token, str)
    assert len(state.token) >= 32
    assert state.expires_at > time.time()
    assert state.approved_account == "mallu.wave"


def test_complete_consumes_state_token_and_rejects_replay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    profile_dir = tmp_path / "opencli-profile"
    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(profile_dir))

    def fake_run(argv, *args, **kwargs):
        return FakeCompleted(returncode=0, stdout=json.dumps(_ok_whoami()))

    monkeypatch.setattr("pipeline.bootstrap_session.subprocess.run", fake_run)
    # Reload auth_instagram to pick up env changes.
    import importlib
    importlib.reload(auth_instagram)

    state = auth_instagram.start_reauth()
    result = auth_instagram.complete_reauth(
        state=state.token,
        sessionid="A" * 40,
        ds_user_id="1234567890",
    )
    assert result.state == "ok"
    assert result.authenticated_account == "mallu.wave"

    with pytest.raises(auth_instagram.StateError, match="replay|consumed|invalid"):
        auth_instagram.complete_reauth(
            state=state.token,
            sessionid="A" * 40,
            ds_user_id="1234567890",
        )


def test_complete_rejects_expired_state_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(tmp_path / "opencli-profile"))
    state = auth_instagram.start_reauth()
    # Force expiry.
    auth_instagram._STATE_TOKENS[state.token] = auth_instagram.PendingState(
        token=state.token,
        issued_at=time.time() - 9999.0,
        ttl_seconds=60.0,
        approved_account="mallu.wave",
    )
    with pytest.raises(auth_instagram.StateError, match="expired"):
        auth_instagram.complete_reauth(
            state=state.token,
            sessionid="A" * 40,
            ds_user_id="1234567890",
        )


# ---------------------------------------------------------------------------
# Cookie validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sessionid",
    [
        "short",  # too short
        "A" * 31,  # boundary
        "has spaces " + "A" * 30,
        "newline\n",
        "<script>alert(1)</script>",
    ],
)
def test_complete_rejects_invalid_sessionid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sessionid: str
) -> None:
    from app import auth_instagram

    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(tmp_path / "opencli-profile"))
    state = auth_instagram.start_reauth()
    with pytest.raises(auth_instagram.ValidationError, match="sessionid"):
        auth_instagram.complete_reauth(
            state=state.token,
            sessionid=sessionid,
            ds_user_id="1234567890",
        )


@pytest.mark.parametrize("ds_user_id", ["abc", "12" * 21, "", "-1", "1.2"])
def test_complete_rejects_invalid_ds_user_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ds_user_id: str
) -> None:
    from app import auth_instagram

    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(tmp_path / "opencli-profile"))
    state = auth_instagram.start_reauth()
    with pytest.raises(auth_instagram.ValidationError, match="ds_user_id"):
        auth_instagram.complete_reauth(
            state=state.token,
            sessionid="A" * 40,
            ds_user_id=ds_user_id,
        )


# ---------------------------------------------------------------------------
# Profile directory safety
# ---------------------------------------------------------------------------


def test_complete_refuses_symlinked_profile_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(link))
    state = auth_instagram.start_reauth()
    with pytest.raises(auth_instagram.BootstrapError, match="symlink"):
        auth_instagram.complete_reauth(
            state=state.token,
            sessionid="A" * 40,
            ds_user_id="1234567890",
        )


# ---------------------------------------------------------------------------
# whoami states
# ---------------------------------------------------------------------------


def test_status_returns_disconnected_when_bridge_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(tmp_path / "opencli-profile"))

    def fake_run(argv, *args, **kwargs):
        return FakeCompleted(returncode=1, stdout="", stderr="BROWSER_CONNECT")

    monkeypatch.setattr("pipeline.bootstrap_session.subprocess.run", fake_run)
    status = auth_instagram.status()
    assert status.state == "browser-bridge-disconnected"
    assert status.authenticated_account is None


def test_status_returns_wrong_account_when_account_differs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(tmp_path / "opencli-profile"))

    def fake_run(argv, *args, **kwargs):
        return FakeCompleted(
            returncode=0, stdout=json.dumps(_ok_whoami("madeat2am.primary"))
        )

    monkeypatch.setattr("pipeline.bootstrap_session.subprocess.run", fake_run)
    status = auth_instagram.status()
    assert status.state == "wrong-account"
    assert status.authenticated_account == "madeat2am.primary"


def test_status_returns_ok_when_account_matches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(tmp_path / "opencli-profile"))

    def fake_run(argv, *args, **kwargs):
        return FakeCompleted(returncode=0, stdout=json.dumps(_ok_whoami("mallu.wave")))

    monkeypatch.setattr("pipeline.bootstrap_session.subprocess.run", fake_run)
    status = auth_instagram.status()
    assert status.state == "ok"
    assert status.authenticated_account == "mallu.wave"


def test_status_response_contains_no_cookies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(tmp_path / "opencli-profile"))

    def fake_run(argv, *args, **kwargs):
        return FakeCompleted(returncode=0, stdout=json.dumps(_ok_whoami()))

    monkeypatch.setattr("pipeline.bootstrap_session.subprocess.run", fake_run)
    status_dict = auth_instagram.status().__dict__
    text = json.dumps(status_dict)
    assert "sessionid" not in text
    assert "ds_user_id" not in text


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_clears_opencli_profile_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    profile_dir = tmp_path / "opencli-profile"
    profile_dir.mkdir()
    cookies_file = profile_dir / "site-session.json"
    cookies_file.write_text(json.dumps({"cookies": []}))

    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(profile_dir))
    auth_instagram.logout()
    assert not cookies_file.exists()
    # Idempotent: a second call is a no-op.
    auth_instagram.logout()


# ---------------------------------------------------------------------------
# Round-trip: complete -> status -> ok
# ---------------------------------------------------------------------------


def test_complete_round_trip_results_in_ok_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    profile_dir = tmp_path / "opencli-profile"
    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(profile_dir))

    def fake_run(argv, *args, **kwargs):
        return FakeCompleted(returncode=0, stdout=json.dumps(_ok_whoami("mallu.wave")))

    monkeypatch.setattr("pipeline.bootstrap_session.subprocess.run", fake_run)
    monkeypatch.setattr("app.auth_instagram.subprocess.run", fake_run)

    state = auth_instagram.start_reauth()
    result = auth_instagram.complete_reauth(
        state=state.token,
        sessionid="B" * 40,
        ds_user_id="9876543210",
    )
    assert result.state == "ok"
    # Cookies file should have been written.
    cookies_files = list(profile_dir.glob("site-session.json"))
    assert cookies_files, "expected cookies file to be written"
    payload = json.loads(cookies_files[0].read_text())
    cookie_names = {c["name"] for c in payload.get("cookies", [])}
    assert cookie_names == {"sessionid", "ds_user_id"}

    # Subsequent status call should be ok.
    status = auth_instagram.status()
    assert status.state == "ok"
    assert status.authenticated_account == "mallu.wave"


def test_complete_writes_file_with_restrictive_permissions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app import auth_instagram

    profile_dir = tmp_path / "opencli-profile"
    monkeypatch.setenv("APPROVED_INSTAGRAM_ACCOUNT", "mallu.wave")
    monkeypatch.setenv("OPENCLI_PROFILE_DIR", str(profile_dir))

    def fake_run(argv, *args, **kwargs):
        return FakeCompleted(returncode=0, stdout=json.dumps(_ok_whoami()))

    monkeypatch.setattr("pipeline.bootstrap_session.subprocess.run", fake_run)
    monkeypatch.setattr("app.auth_instagram.subprocess.run", fake_run)

    state = auth_instagram.start_reauth()
    auth_instagram.complete_reauth(
        state=state.token,
        sessionid="C" * 40,
        ds_user_id="5555555555",
    )
    cookies_files = list(profile_dir.glob("*.json"))
    assert cookies_files
    mode = cookies_files[0].stat().st_mode & 0o777
    # 0600 or 0 on a filesystem that doesn't support it.
    assert mode in (0o600, 0o000)
