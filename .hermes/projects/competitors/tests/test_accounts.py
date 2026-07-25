"""Tests for `pipeline.accounts.parse_accounts`.

The parser reads `competitor-accounts.md`, finds the table, and returns the
distinct rows where `Active = yes`. Usernames are normalised to lowercase,
trimmed of leading `@`, and validated against the Instagram handle regex.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.accounts import AccountsError, parse_accounts


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "competitor-accounts.md"
    p.write_text(body, encoding="utf-8")
    return p


def _good_table(*rows: str) -> str:
    header = (
        "# Competitor accounts\n\n"
        "| Username | Niche / why tracked | Size (rough) | Active |\n"
        "| --- | --- | --- | --- |\n"
    )
    return header + "\n".join(rows) + "\n"


def test_parses_active_rows_lowercases_and_strips_at(tmp_path: Path) -> None:
    body = _good_table(
        "| @Example_Handle | direct competitor | 10k | yes |",
        "| SECOND.handle | one tier up | 80k | yes |",
    )
    result = parse_accounts(_write(tmp_path, body))
    assert result == ["example_handle", "second.handle"]


def test_ignores_inactive_rows(tmp_path: Path) -> None:
    body = _good_table(
        "| active_one | direct | 10k | yes |",
        "| inactive_one | was tracked | 5k | no |",
    )
    result = parse_accounts(_write(tmp_path, body))
    assert result == ["active_one"]


def test_dedupes_repeated_usernames(tmp_path: Path) -> None:
    body = _good_table(
        "| duplicate | a | 1k | yes |",
        "| DUPLICATE | b | 2k | yes |",
    )
    result = parse_accounts(_write(tmp_path, body))
    assert result == ["duplicate"]


def test_rejects_invalid_usernames(tmp_path: Path) -> None:
    body = _good_table(
        "| good_one | a | 1k | yes |",
        "| bad-name! | nope | 1k | yes |",
        "| another-good | b | 2k | yes |",
    )
    result = parse_accounts(_write(tmp_path, body))
    assert result == ["good_one", "another-good"]


def test_raises_when_no_active_accounts(tmp_path: Path) -> None:
    body = _good_table(
        "| a | a | 1k | no |",
        "| b | b | 2k | no |",
    )
    with pytest.raises(AccountsError, match="Active = yes"):
        parse_accounts(_write(tmp_path, body))


def test_raises_when_file_missing(tmp_path: Path) -> None:
    with pytest.raises(AccountsError, match="not found"):
        parse_accounts(tmp_path / "absent.md")


def test_ignores_non_table_rows(tmp_path: Path) -> None:
    body = (
        "# Header\n\n"
        "Some prose. | still prose |\n\n"
        "| Username | Niche | Size | Active |\n"
        "| --- | --- | --- | --- |\n"
        "| valid_one | a | 1k | yes |\n"
        "| --- | --- | --- | --- |\n"
    )
    result = parse_accounts(_write(tmp_path, body))
    assert result == ["valid_one"]
