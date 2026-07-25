#!/usr/bin/env python3
"""Competitors dashboard — thin CLI wrapper (Hermes adaptation).

This module is a thin wrapper that delegates the real work to the
`pipeline/` package. It is responsible for:

1. Parsing command-line arguments.
2. Selecting the run configuration (SGT timestamps, run key, safety caps).
3. Invoking the appropriate pipeline entry point.

The real collection, download, transcoding, and analysis logic lives in:

- `pipeline/accounts.py`        (parse and validate competitor-accounts.md)
- `pipeline/opencli_instagram.py` (call OpenCLI as an argument array)
- `pipeline/media.py`           (ffprobe + FFmpeg validation and normalization)
- `pipeline/whisper_transcriber.py` (local Faster-Whisper inference)
- `pipeline/collector.py`       (the synchronous end-to-end orchestrator)
- `pipeline/ledger.py`          (file-locked, atomic ledger)
- `pipeline/models.py`          (Pydantic models and the JSON schema)
- `pipeline/notes.py`           (deterministic Markdown note rendering)

Mechanical stages only. The reasoning stage (score, beats, research, angle)
runs as a Hermes playbook entry on the Hermes host.

Setup:
    pip install -e .

Run:
    python3 scrape.py --check-session
    python3 scrape.py --check-whisper
    python3 scrape.py                       # default caps
    python3 scrape.py --limit 5             # 5 per account
    python3 scrape.py --accounts handle1 handle2
    python3 scrape.py --no-transcribe
    python3 scrape.py --dry-run
    python3 scrape.py --run-id 2026-07-24T1200-foo
    python3 scrape.py --resume
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PIPELINE = ROOT / "pipeline"

if __name__ == "__main__":
    from pipeline.cli import main

    sys.exit(main())
