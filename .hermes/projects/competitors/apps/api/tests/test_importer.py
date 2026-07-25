"""Tests for the publish-bundle importer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "bundle_one.json"


def _bundle(**overrides) -> dict:
    data = json.loads(FIXTURE.read_text())
    data.update(overrides)
    return data


def test_import_bundle_first_run_inserts_reel_and_analysis(client) -> None:
    from app.importer import import_bundle

    result = import_bundle(_bundle())
    assert result.status == "imported"
    assert result.reel_count == 1
    assert result.analysis_count == 1


def test_import_bundle_duplicate_is_idempotent(client) -> None:
    from app.importer import import_bundle

    first = import_bundle(_bundle())
    second = import_bundle(_bundle())
    assert first.status == "imported"
    assert second.status == "already_imported"
    assert second.reel_count == 0


def test_import_bundle_invalid_score_rolls_back(client) -> None:
    from app.importer import import_bundle

    bad = _bundle()
    bad["items"][0]["analysis"]["relevance_score"] = 99
    with pytest.raises(ValueError):
        import_bundle(bad)
    # Verify nothing was committed.
    from app.db import session_scope
    from app.models import Reel
    with session_scope() as s:
        assert s.query(Reel).count() == 0


def test_import_bundle_unknown_run_id_is_rejected(client) -> None:
    from app.importer import import_bundle

    bad = _bundle()
    bad["run_id"] = ""
    with pytest.raises(ValueError):
        import_bundle(bad)
