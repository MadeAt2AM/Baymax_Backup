#!/usr/bin/env python3
"""Validate one or more analysis bundle JSON files.

Usage:
    python scripts/validate_analysis.py <bundle.json> [<bundle.json> ...]
    python scripts/validate_analysis.py --schema
    python scripts/validate_analysis.py --directory data/staging/run-1/analysis/

The validator fails closed:
- Either every bundle is valid, or the script exits non-zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.models import AnalysisBundle, json_schema  # noqa: E402


def _validate_one(path: Path) -> int:
    """Validate an analysis bundle or a publish bundle. Returns the count validated."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}")
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        # Publish bundle wrapper.
        for idx, item in enumerate(data["items"]):
            try:
                AnalysisBundle.model_validate(item)
            except Exception as exc:
                raise SystemExit(f"{path}: items[{idx}]: {exc}")
        return len(data["items"])
    AnalysisBundle.model_validate(data)
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="validate_analysis")
    p.add_argument("bundles", nargs="*")
    p.add_argument("--directory", type=Path, default=None)
    p.add_argument("--schema", action="store_true", help="print JSON schema and exit")
    args = p.parse_args(argv)

    if args.schema:
        print(json.dumps(json_schema(), indent=2))
        return 0

    paths: list[Path] = [Path(b) for b in args.bundles]
    if args.directory:
        if not args.directory.exists():
            print(f"directory not found: {args.directory}", file=sys.stderr)
            return 2
        paths.extend(sorted(args.directory.glob("*.json")))
    if not paths:
        print("no bundles supplied", file=sys.stderr)
        return 2

    failures = []
    total_items = 0
    for path in paths:
        try:
            count = _validate_one(path)
        except SystemExit as exc:
            failures.append((path, str(exc)))
            print(f"FAIL {path}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures.append((path, str(exc)))
            print(f"FAIL {path}: {exc}")
        else:
            total_items += count
            tag = "bundle" if count == 1 else "bundles"
            print(f"OK   {path} ({count} {tag})")
    if failures:
        print(f"\n{len(failures)} file(s) failed validation", file=sys.stderr)
        return 1
    print(f"\n{len(paths)} file(s) valid, {total_items} bundle(s) total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
