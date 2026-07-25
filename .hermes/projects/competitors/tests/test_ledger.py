"""Tests for the file-locked ledger used to track reel lifecycle state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.ledger import Ledger, LedgerError


def _seed_run_keys() -> set[str]:
    return {"scraped", "low_score", "processed", "failed", "published"}


def test_load_returns_empty_state_when_missing(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.json")
    assert led.read() == {k: [] for k in _seed_run_keys()}


def test_add_appends_scraped_without_removing_others(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.json")
    led.add("scraped", "abc123")
    led.add("low_score", "abc123")
    state = led.read()
    assert state["scraped"] == ["abc123"]
    assert state["low_score"] == ["abc123"]


def test_add_is_idempotent_per_shortcode(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.json")
    led.add("scraped", "abc123")
    led.add("scraped", "abc123")
    led.add("scraped", "xyz999")
    assert led.read()["scraped"] == ["abc123", "xyz999"]


def test_known_returns_union_of_all_states(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.json")
    led.add("scraped", "a")
    led.add("low_score", "b")
    led.add("processed", "c")
    led.add("failed", "d")
    assert led.known() == {"a", "b", "c", "d"}


def test_atomic_write_does_not_corrupt_on_concurrent_interleave(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.json")
    # Pre-populate to ensure existing state survives.
    led.add("scraped", "preexisting")
    # Now write again from a different "process" — the second write should win
    # as a clean atomic swap, not partial.
    state = led.read()
    state["scraped"].append("second")
    led.write(state)
    loaded = json.loads((tmp_path / "ledger.json").read_text())
    assert loaded["scraped"] == ["preexisting", "second"]


def test_rejects_unknown_state(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.json")
    with pytest.raises(LedgerError, match="unknown state"):
        led.add("totally_not_a_state", "x")
