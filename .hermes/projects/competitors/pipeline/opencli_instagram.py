"""Wrapper around the OpenCLI Instagram adapter.

The adapter is **read-only** in the first release. It supports:

- `session_health` — `whoami` to confirm the Browser Bridge is connected.
- `fetch_user_posts` — recent posts for a username, filtered to reels.
- `download_reel` — download a reel into a staging directory.

All subprocess calls are made via argument arrays (`shell=False`). Cookies
and session IDs are never read, logged, or returned.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SHORTCODE_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


class OpenCLIError(RuntimeError):
    """Raised when the OpenCLI adapter fails or returns malformed output."""


@dataclass(frozen=True)
class ScrapeResult:
    shortcode: str
    username: str
    url: str
    caption: str
    views: int
    likes: int
    comments: int
    published_at: str | None


def _argv(base: list[str]) -> list[str]:
    """Sanity-check the argument vector before execution."""

    if not base:
        raise OpenCLIError("refusing to run empty argv")
    return [str(x) for x in base]


def parse_json_output(raw: str) -> Any:
    """Parse JSON output from OpenCLI, raising OpenCLIError on garbage."""

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenCLIError(f"opencli returned non-JSON output: {exc}") from exc


def normalize_posts(raw_items: Iterable[dict], *, username: str) -> list[ScrapeResult]:
    """Filter OpenCLI feed items to reels and normalize the field names."""

    results: list[ScrapeResult] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        if item.get("type") not in ("reel", "clips", "GraphVideo", "video"):
            continue
        url = item.get("url") or item.get("postUrl") or ""
        m = re.search(r"/(?:reel|reels|p|tv)/([A-Za-z0-9_-]{6,20})(?:/|$|\?)", url)
        if not m:
            continue
        shortcode = m.group(1)
        if not SHORTCODE_RE.match(shortcode):
            continue
        results.append(
            ScrapeResult(
                shortcode=shortcode,
                username=(item.get("ownerUsername") or username).lower().lstrip("@"),
                url=url,
                caption=item.get("caption") or item.get("text") or "",
                views=int(item.get("videoViewCount") or item.get("videoPlayCount") or item.get("playCount") or item.get("views") or 0),
                likes=int(item.get("likesCount") or item.get("likeCount") or item.get("likes") or 0),
                comments=int(item.get("commentsCount") or item.get("commentCount") or item.get("comments") or 0),
                published_at=item.get("date") or item.get("takenAt") or None,
            )
        )
    return results


def fetch_user_posts(
    *,
    username: str,
    limit: int,
    binary: Path,
    site_session: str = "persistent",
    window: str = "background",
    timeout: int = 300,
) -> list[ScrapeResult]:
    """Run `opencli instagram user <u> --limit N` and return normalized reels."""

    argv = _argv(
        [
            binary,
            "instagram",
            "user",
            username,
            "--limit",
            str(limit),
            "-f",
            "json",
            "--window",
            window,
            "--site-session",
            site_session,
        ]
    )
    proc = subprocess.run(  # noqa: S603 — argv is a sanitized list, shell=False
        argv,
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        if "BROWSER_CONNECT" in stderr or "Browser Bridge" in stderr:
            raise OpenCLIError(
                "OpenCLI Browser Bridge is not connected. Open Chrome/Chromium on the dev "
                "VPS with the OpenCLI extension enabled, then re-run."
            )
        raise OpenCLIError(f"opencli user failed (exit {proc.returncode}): {stderr[:300]}")
    payload = parse_json_output(proc.stdout)
    items = payload if isinstance(payload, list) else [payload]
    return normalize_posts(items, username=username)


def session_health(
    *,
    binary: Path,
    site_session: str = "persistent",
    window: str = "background",
    timeout: int = 60,
) -> str:
    """Return the authenticated account username, or raise OpenCLIError."""

    argv = _argv(
        [
            binary,
            "instagram",
            "whoami",
            "-f",
            "json",
            "--window",
            window,
            "--site-session",
            site_session,
        ]
    )
    proc = subprocess.run(  # noqa: S603
        argv,
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        if "BROWSER_CONNECT" in stderr or "Browser Bridge" in stderr:
            raise OpenCLIError(
                "Browser Bridge extension not connected. Make sure Chrome/Chromium is open "
                "and the OpenCLI extension is enabled."
            )
        raise OpenCLIError(f"opencli whoami failed (exit {proc.returncode}): {stderr[:200]}")
    payload = parse_json_output(proc.stdout) or {}
    if not isinstance(payload, dict):
        raise OpenCLIError("opencli whoami returned a non-object payload")
    account = payload.get("username") or payload.get("user") or payload.get("account")
    if not isinstance(account, str) or not account:
        raise OpenCLIError("opencli whoami did not return a username")
    return account.lower().lstrip("@")


def download_reel(
    *,
    url: str,
    dest_dir: Path,
    binary: Path,
    site_session: str = "persistent",
    window: str = "background",
    timeout: int = 600,
) -> Path:
    """Download a reel into `dest_dir`. Returns the downloaded file path."""

    dest_dir.mkdir(parents=True, exist_ok=True)
    argv = _argv(
        [
            binary,
            "instagram",
            "download",
            url,
            "--path",
            str(dest_dir),
            "-f",
            "json",
            "--window",
            window,
            "--site-session",
            site_session,
        ]
    )
    proc = subprocess.run(  # noqa: S603
        argv,
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise OpenCLIError(f"opencli download failed (exit {proc.returncode}): {(proc.stderr or '').strip()[:300]}")
    # The actual filename is written by opencli; we just need the most recent file in dest_dir.
    candidates = sorted(dest_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise OpenCLIError("opencli download succeeded but produced no file")
    return candidates[0]
