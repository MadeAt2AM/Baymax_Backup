"""Parse the operator-edited `competitor-accounts.md` file.

The file is a Markdown table. We accept only rows where the trailing `Active`
cell is `yes`. Rows are normalised, deduplicated, and validated against the
Instagram handle regex (``^[a-z0-9._-]{1,30}$``).
"""

from __future__ import annotations

import re
from pathlib import Path

HANDLE_RE = re.compile(r"^[a-z0-9._-]{1,30}$")


class AccountsError(RuntimeError):
    """Raised for missing files, empty tables, or malformed active rows."""


def parse_accounts(path: Path) -> list[str]:
    """Return the distinct, lowercase Instagram handles in `Active = yes` rows.

    Raises `AccountsError` if the file is missing, no such rows exist, or no
    rows are valid.
    """

    if not path.exists():
        raise AccountsError(f"{path.name} not found — fill in the template first")

    handles: list[str] = []
    seen: set[str] = set()

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        username = cells[0].lstrip("@").lower()
        active = cells[-1].lower()
        if username in ("username", "") or "---" in username:
            continue
        if active != "yes":
            continue
        if not HANDLE_RE.match(username):
            continue
        if username in seen:
            continue
        seen.add(username)
        handles.append(username)

    if not handles:
        raise AccountsError("No rows with Active = yes in competitor-accounts.md")

    return handles
