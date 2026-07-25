#!/usr/bin/env bash
# Transfer the publish bundle to the dev VPS and trigger the importer.
#
# Usage:
#   bash scripts/publish_bundle.sh <bundle.json> [--dry-run]
#
# The script:
#   1. Verifies the bundle exists and is valid JSON.
#   2. SCPs it to /srv/projects/competitors/imports/ on the dev VPS.
#   3. Runs the container-only importer inside the API container.
#
# The script never prints cookies, session IDs, signed media URLs, or
# dashboard secrets. It only logs the run ID and counts.

set -euo pipefail

BUNDLE="${1:-}"
DRY_RUN="false"
if [[ "${2:-}" == "--dry-run" ]]; then
  DRY_RUN="true"
fi

if [[ -z "$BUNDLE" ]]; then
  echo "usage: $0 <bundle.json> [--dry-run]" >&2
  exit 1
fi

if [[ ! -f "$BUNDLE" ]]; then
  echo "bundle not found: $BUNDLE" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

# Validate the bundle is JSON and has a run_id.
RUN_ID=$(jq -r '.run_id // ""' "$BUNDLE")
ITEM_COUNT=$(jq -r '.items | length' "$BUNDLE")
if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
  echo "bundle missing run_id: $BUNDLE" >&2
  exit 1
fi

echo "publishing run_id=$RUN_ID items=$ITEM_COUNT"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "dry-run: would scp $BUNDLE to dev-vps:/srv/projects/competitors/imports/"
  echo "dry-run: would exec docker compose run --rm api python -m app.importer /imports/$(basename "$BUNDLE")"
  exit 0
fi

# TODO: enable these when the importer is wired in Phase 5.
# scp -q "$BUNDLE" "dev-vps:/srv/projects/competitors/imports/$(basename "$BUNDLE")"
# ssh -q dev-vps "cd /srv/projects/competitors && docker compose run --rm api python -m app.importer /imports/$(basename "$BUNDLE")"
echo "publish deferred: API container + importer not yet implemented (Phase 5)"
exit 0
