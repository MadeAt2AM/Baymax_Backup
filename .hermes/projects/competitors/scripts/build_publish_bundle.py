#!/usr/bin/env python3
"""Build a publish bundle from a directory of validated analysis bundles.

Usage:
    python scripts/build_publish_bundle.py <analysis-dir> [--out <bundle.json>]

The bundle is a single JSON object:

{
  "run_id": "...",
  "built_at": "ISO-8601 with timezone",
  "items": [<bundles>]
}

Each item is the validated analysis bundle. The bundle is written
deterministically (sorted keys, indent=2) so two runs with the same
input produce the same output.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.models import AnalysisBundle  # noqa: E402


def _validate_one(path: Path) -> AnalysisBundle:
    return AnalysisBundle.model_validate(json.loads(path.read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="build_publish_bundle")
    p.add_argument("analysis_dir", type=Path)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--run-id", default=None)
    args = p.parse_args(argv)

    if not args.analysis_dir.exists():
        print(f"analysis directory not found: {args.analysis_dir}", file=sys.stderr)
        return 2

    paths = sorted(args.analysis_dir.glob("*.json"))
    if not paths:
        print(f"no analysis bundles in {args.analysis_dir}", file=sys.stderr)
        return 2

    bundles = []
    for path in paths:
        try:
            bundles.append(_validate_one(path).model_dump(mode="json"))
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {path}: {exc}", file=sys.stderr)
            return 3

    run_id = args.run_id or args.analysis_dir.parent.name
    sgt = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    payload = {
        "run_id": run_id,
        "built_at": sgt.isoformat(),
        "items": bundles,
    }

    out = args.out or (args.analysis_dir / "bundle.json")
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {len(bundles)} bundle(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
