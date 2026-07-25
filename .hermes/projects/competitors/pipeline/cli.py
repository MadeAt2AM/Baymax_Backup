"""CLI entry point for the thin `scrape.py` wrapper.

The CLI supports:

- `--check-session` — verify OpenCLI Browser Bridge is connected.
- `--check-whisper` — verify the Faster-Whisper model loads.
- `--limit N` — reels per account (default 3).
- `--accounts h1 h2 ...` — override the competitor-accounts list.
- `--no-transcribe` — stage metadata only.
- `--dry-run` — show what would happen without touching the network.
- `--run-id ID` — use a fixed run id (default: SGT timestamp + random suffix).
- `--resume` — skip reels already in the ledger.
- `--cap N` — total reel cap per run.

The CLI exits non-zero on any failure. It does not print cookies, session
IDs, signed media URLs, or dashboard secrets.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .accounts import AccountsError, parse_accounts
from .collector import CollectionError, collect_for_account
from .ledger import Ledger
from .media import (
    MediaError,
    extract_audio,
    safe_staging_dir,
    validate_download,
)
from .opencli_instagram import (
    OpenCLIError,
    download_reel,
    fetch_user_posts,
    session_health,
)
from .whisper_transcriber import (
    FasterWhisperBackend,
    TranscriptionError,
    transcribe,
)
from . import bootstrap_session


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OPENCLI = Path("/usr/local/bin/opencli")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="competitors-collect")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--accounts", nargs="*", default=None)
    p.add_argument("--no-transcribe", action="store_true")
    p.add_argument("--cap", type=int, default=50)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--run-id", default=None)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--check-session", action="store_true")
    p.add_argument("--check-whisper", action="store_true")
    p.add_argument("--bootstrap-session", action="store_true", help="prepare the dev-VPS site-session directory and run the interactive OpenCLI login")
    p.add_argument(
        "--accounts-file",
        type=Path,
        default=ROOT / "competitor-accounts.md",
    )
    p.add_argument(
        "--staging-root",
        type=Path,
        default=ROOT / "data" / "staging",
    )
    p.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "data" / "ledger.json",
    )
    p.add_argument("--opencli", type=Path, default=DEFAULT_OPENCLI)
    p.add_argument("--whisper-model", default="tiny")
    p.add_argument("--whisper-device", default="cpu")
    p.add_argument("--whisper-compute-type", default="int8")
    p.add_argument("--whisper-model-revision", default=None)
    p.add_argument("--site-session", default="persistent")
    p.add_argument("--window", default="background")
    p.add_argument("--max-bytes", type=int, default=100 * 1024 * 1024)
    p.add_argument("--max-duration-seconds", type=int, default=180)
    return p


def _make_run_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    sgt = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    return f"{sgt.strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(4)}"


def _check_session(opencli: Path, site_session: str, window: str) -> int:
    try:
        acct = session_health(binary=opencli, site_session=site_session, window=window)
    except OpenCLIError as exc:
        print(f"session check failed: {exc}")
        return 2
    print(f"OpenCLI session OK: {acct}")
    return 0


def _check_whisper(model_name: str, device: str, compute_type: str, model_revision: str | None) -> int:
    try:
        FasterWhisperBackend(
            model_name=model_name,
            device=device,
            compute_type=compute_type,
            model_revision=model_revision,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"whisper load failed: {exc}")
        return 3
    print(f"Whisper OK: {model_name} ({device}, {compute_type})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.check_session:
        return _check_session(args.opencli, args.site_session, args.window)
    if args.check_whisper:
        return _check_whisper(
            args.whisper_model,
            args.whisper_device,
            args.whisper_compute_type,
            args.whisper_model_revision,
        )

    if args.bootstrap_session:
        try:
            d = bootstrap_session.ensure_profile_dir()
            print(f"profile dir ready: {d}")
            bootstrap_session.run_login()
            account = bootstrap_session.verify_bootstrap()
            print(f"verified account: {account}")
            return 0
        except bootstrap_session.BootstrapError as exc:
            print(f"bootstrap failed: {exc}", file=__import__("sys").stderr)
            return 5

    if args.accounts:
        usernames = [a.lower().lstrip("@") for a in args.accounts]
    else:
        try:
            usernames = parse_accounts(args.accounts_file)
        except AccountsError as exc:
            print(f"accounts: {exc}")
            return 4

    if args.dry_run:
        print(f"dry-run: would collect {args.limit} reel(s) per account for {usernames}")
        return 0

    run_id = _make_run_id(args.run_id)
    ledger = Ledger(args.ledger)
    args.staging_root.mkdir(parents=True, exist_ok=True)

    totals = {"accepted": 0, "rejected": 0, "failed": 0}
    for username in usernames:
        try:
            result = collect_for_account(
                username=username,
                limit=args.limit,
                staging_root=args.staging_root,
                run_id=run_id,
                opencli=_OpenCLIAdapter(args.opencli, args.site_session, args.window),
                media=_MediaAdapter(),
                whisper=_WhisperAdapter(
                    no_transcribe=args.no_transcribe,
                    model_name=args.whisper_model,
                    device=args.whisper_device,
                    compute_type=args.whisper_compute_type,
                    model_revision=args.whisper_model_revision,
                ),
                ledger=ledger,
                max_bytes=args.max_bytes,
                max_duration_seconds=args.max_duration_seconds,
            )
        except CollectionError as exc:
            print(f"collection failed for {username}: {exc}")
            totals["failed"] += 1
            continue
        totals["accepted"] += result.accepted_count
        totals["rejected"] += result.rejected_count
        totals["failed"] += result.failed_count
        print(
            f"{username}: accepted={result.accepted_count} "
            f"rejected={result.rejected_count} failed={result.failed_count}"
        )

    print(json.dumps({"run_id": run_id, **totals}, indent=2))
    return 0


class _OpenCLIAdapter:
    def __init__(self, binary: Path, site_session: str, window: str) -> None:
        self.binary = binary
        self.site_session = site_session
        self.window = window

    def session_health(self, **kwargs: Any) -> str:
        return session_health(
            binary=self.binary, site_session=self.site_session, window=self.window
        )

    def fetch_user_posts(self, *, username: str, limit: int):
        return [
            item.__dict__
            for item in fetch_user_posts(
                username=username,
                limit=limit,
                binary=self.binary,
                site_session=self.site_session,
                window=self.window,
            )
        ]

    def download_reel(self, *, url: str, dest_dir: Path) -> Path:
        return download_reel(
            url=url,
            dest_dir=dest_dir,
            binary=self.binary,
            site_session=self.site_session,
            window=self.window,
        )


class _MediaAdapter:
    def safe_staging_dir(self, root: Path, name: str) -> Path:
        return safe_staging_dir(root, name)

    def validate_download(self, path: Path, **kwargs) -> dict:
        return validate_download(path, **kwargs)

    def extract_audio(self, src: Path, dst: Path) -> Path:
        return extract_audio(src, dst)


class _WhisperAdapter:
    def __init__(
        self,
        *,
        no_transcribe: bool,
        model_name: str,
        device: str,
        compute_type: str,
        model_revision: str | None,
    ) -> None:
        self.no_transcribe = no_transcribe
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.model_revision = model_revision

    def transcribe(self, audio_path: Path, **kwargs: Any):
        if self.no_transcribe:
            from .whisper_transcriber import TranscriptionResult

            return TranscriptionResult(
                text="",
                language="unknown",
                language_probability=0.0,
                segments=[],
                model=self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                duration_ms=0,
            )
        return transcribe(
            audio_path,
            model_name=self.model_name,
            device=self.device,
            compute_type=self.compute_type,
            model_revision=self.model_revision,
        )


if __name__ == "__main__":
    sys.exit(main())
