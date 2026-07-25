---
name: competitor-intelligence
version: 0.1.0
description: Process staged competitor reels — score, section, research, and publish them into the dashboard.
trigger: "When the user says 'process the staged batch' or 'process run <run-id>' or 'analyze the latest competitors batch', load this skill and run the procedure."
inputs:
  - run_id (optional; defaults to the latest run in data/staging/)
  - one optional --accounts-file override
outputs:
  - analysis bundles in data/staging/<run-id>/analysis/
  - data/staging/<run-id>/analysis/bundle.json
  - ledger updates (low_score, processed)
---

# Competitor Intelligence — Hermes playbook entry

This skill runs the **reasoning** stage of the pipeline. The mechanical
stages (scrape, download, transcribe) are handled by `scrape.py` on the
dev VPS. Reasoning happens here, on the Hermes host, via Hermes itself.

## Prerequisites

- `/root/.hermes/projects/competitors/` is the project root.
- The user has run `scrape.py --limit 1 --cap 1 --accounts <one_account>`
  to produce a staged batch under `data/staging/<run-id>/batch.json`.
- The niche is filled in `config/project.yaml` (the playbook entry will
  halt if it is missing).
- The current model provider is configured and the user has approved
  their preferred model for the reasoning stage.

## Procedure

1. **Locate the staged batch.** If `run_id` was not supplied, pick the
   most recent run under `data/staging/`. If no batch is present, halt
   and ask the user to run `scrape.py` first.

2. **Load the config.**
   - Read `config/project.yaml` and extract `niche`. If missing, halt.
   - Read `competitor-accounts.md` and confirm at least one active row.

3. **Process the batch one reel at a time.** For each item in
   `batch.json`:

   a. Read the `transcript` (verbatim) and `caption`. If the transcript is
      empty, score from the caption alone and mark `transcript_status: empty`.

   b. Score 1–10 using the rubric in `references/analysis-contract.md`.

   c. Extract `topic`, `tools`, `hookStyle`, `reasoning`,
      and `sections` (verbatim text only).

   d. Compute `verdict` = `score >= 7 AND there's a teachable insight`.

   e. If `verdict == false`, skip the research and angle steps.

   f. For each named tool, perform a **source-backed web search**. Record
      `one_liner`, `how_it_works`, `hook_fact`, and the source URL.

   g. Write the analysis bundle to
      `data/staging/<run-id>/analysis/<shortcode>.json`.

4. **Validate every bundle.** Run `python scripts/validate_analysis.py
   data/staging/<run-id>/analysis/`. If any bundle fails validation, halt
   and report the error.

5. **Build the publish bundle.** Run `python scripts/build_publish_bundle.py
   data/staging/<run-id>/analysis/`.

6. **Publish.** Run `bash scripts/publish_bundle.sh data/staging/<run-id>/analysis/bundle.json`.
   The script transfers the bundle over SSH to the dev VPS and triggers
   the container-only importer. The script does not print cookies, session
   IDs, signed media URLs, or dashboard secrets.

7. **Update the ledger.** For each rejected reel, append its shortcode to
   `data/ledger.json → low_score`. For each keeper, append its shortcode
   to `data/ledger.json → processed`.

## Failure handling

- If `bundle.json` contains fewer validated bundles than expected, halt
  and report the discrepancy.
- If the publish script fails, halt and report the SSH error. Do not
  silently retry — the operator should investigate.
- If a reel's transcript is empty, the analysis is still produced from
  the caption; the dashboard renders an empty transcript gracefully.
- Never bypass Instagram checkpoints, login challenges, or rate limits.
  If any of those appear, the pipeline must halt.

## Cleanup

- Do **not** delete `data/staging/<run-id>/videos/` from the Hermes host.
  Those files live on the dev VPS. The cleanup is owned by the dev-VPS
  retention policy.

## What this skill does NOT do

- It does not call OpenCLI or Faster-Whisper. Those run on the dev VPS.
- It does not write to PostgreSQL directly. The container-only importer
  on the dev VPS does that.
- It does not modify `competitor-accounts.md` or `config/project.yaml`.
- It does not expose cookies, session IDs, signed media URLs, or
  dashboard secrets in any output.
