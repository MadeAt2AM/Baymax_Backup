"""File-locked ledger for shortcode lifecycle state.

The ledger is a small JSON file guarded by an `fcntl` lock. It tracks which
shortcodes are in each state (`scraped`, `low_score`, `processed`, `failed`,
`published`). Writes are atomic: a temp file is written then renamed into
place, so a crash mid-write cannot corrupt the file.
"""

from __future__ import annotations

import fcntl
import json
from pathlib import Path
from typing import Any

VALID_STATES = ("scraped", "low_score", "processed", "failed", "published")


class LedgerError(RuntimeError):
    """Raised for invalid states or unparseable ledger files."""


class Ledger:
    """A small, file-backed ledger with locking and atomic writes."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _empty(self) -> dict[str, list[str]]:
        return {state: [] for state in VALID_STATES}

    def read(self) -> dict[str, list[str]]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LedgerError(f"{self.path} is not valid JSON: {exc}") from exc
        # Defensive: ensure every known state is present.
        result = self._empty()
        if isinstance(data, dict):
            for state, values in data.items():
                if state in VALID_STATES and isinstance(values, list):
                    result[state] = list(values)
        return result

    def write(self, state: dict[str, list[str]]) -> None:
        for s in state:
            if s not in VALID_STATES:
                raise LedgerError(f"unknown state: {s}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(state, fh, indent=2, sort_keys=True)
                fh.flush()
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        tmp.replace(self.path)

    def add(self, state: str, shortcode: str) -> None:
        if state not in VALID_STATES:
            raise LedgerError(f"unknown state: {state}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Use a sidecar lock file so we can lock before the ledger exists.
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with lock_path.open("a+") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                current = self.read()
                if shortcode not in current[state]:
                    current[state].append(shortcode)
                    self.write(current)
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

    def known(self) -> set[str]:
        result: set[str] = set()
        for state, values in self.read().items():
            result.update(values)
        return result


def empty_state() -> dict[str, list[str]]:
    """Helper for code that just needs the canonical empty shape."""
    return {state: [] for state in VALID_STATES}


__all__ = ["Ledger", "LedgerError", "VALID_STATES", "empty_state"]
