#!/usr/bin/env bash
# fix-large-blob-push.sh
#
# Recover from a `git push origin main` rejected with GH001 (large files).
# Use this when the baymax-backup cron job fails because a tracked blob
# exceeds GitHub's 100 MB limit.
#
# Strategy:
#   1. List all blobs reachable from HEAD but missing on origin, flag any
#      larger than 90 MB (10 MB safety margin under the 100 MB cap).
#   2. For each, derive the top-level directory and add it to .gitignore.
#   3. `git rm --cached` the files from the index.
#   4. Soft-reset to origin/main, recommit working-tree changes as a single
#      clean commit, and push (fast-forward — no force required if the
#      offending blobs were only in un-pushed local commits).
#
# Idempotent. Safe to run multiple times.
#
# Usage:
#   bash /root/baymax-backup/scripts/fix-large-blob-push.sh
#
# Exit codes:
#   0 = push succeeded (or nothing to fix)
#   1 = recovery failed; manual intervention needed
#   2 = no remote/main reachable; nothing to do

set -euo pipefail

REPO=/root
THRESHOLD_MB=90
GITIGNORE="$REPO/.gitignore"

log() { printf "[fix-large-blob] %s\n" "$*"; }
die() { printf "[fix-large-blob] ERROR: %s\n" "$*" >&2; exit 1; }

cd "$REPO"

git rev-parse --abbrev-ref HEAD | grep -qx main \
    || die "not on main branch (refusing to run)"

git ls-remote --exit-code origin main >/dev/null 2>&1 \
    || { log "no origin/main reachable — nothing to recover from"; exit 2; }

REMOTE_SHA=$(git rev-parse origin/main)

log "scanning for blobs >${THRESHOLD_MB} MB reachable from HEAD but not on origin ($REMOTE_SHA)..."

LARGE_FILES=$(mktemp)
trap 'rm -f "$LARGE_FILES"' EXIT

git rev-list --objects "${REMOTE_SHA}..HEAD" -- \
    | awk '{print $1}' \
    | git cat-file --batch-check='%(objectname) %(objecttype) %(objectsize)' \
    | awk -v thr=$((THRESHOLD_MB * 1024 * 1024)) \
        '$2 == "blob" && $3 > thr { print $1 }' \
    > "$LARGE_FILES"

if [[ ! -s "$LARGE_FILES" ]]; then
    log "no oversized blobs found — push should succeed without changes"
    exit 0
fi

log "found $(wc -l < "$LARGE_FILES") oversized blob(s):"
PATHS_TO_REMOVE=()
while read -r sha; do
    paths=$(git rev-list --objects "$sha" 2>/dev/null \
            | awk -v s="$sha" '$1 == s {print $2}')
    for p in $paths; do
        size=$(git cat-file -s "$sha")
        echo "  $p ($(numfmt --to=iec --suffix=B "$size"))"
        PATHS_TO_REMOVE+=("$p")
        topdir=$(echo "$p" | cut -d/ -f1-2)
        if ! grep -qxF "$topdir/**" "$GITIGNORE" 2>/dev/null \
           && ! grep -qxF "$topdir/" "$GITIGNORE" 2>/dev/null; then
            log "  → adding '$topdir/**' to .gitignore"
            {
                echo ""
                echo "# Auto-added by fix-large-blob-push.sh on $(date -u +%Y-%m-%d)"
                echo "$topdir/**"
                echo "$topdir/"
            } >> "$GITIGNORE"
        fi
    done
done < "$LARGE_FILES"

log "removing oversized files from git index..."
for p in "${PATHS_TO_REMOVE[@]}"; do
    git rm --cached -r --ignore-unmatch -- "$p" >/dev/null 2>&1 || true
done

log "soft-resetting to origin/main ($REMOTE_SHA) and recommitting..."
git reset --soft "$REMOTE_SHA"

git add -A

if git diff --cached --quiet; then
    log "nothing to commit after reset — clean state achieved"
    exit 0
fi

COMMIT_MSG="Backup $(date -u '+%Y-%m-%d %H:%M') — exclude oversized blobs (>${THRESHOLD_MB} MB)"
git commit -m "$COMMIT_MSG" >/dev/null

log "pushing..."
if git push origin main; then
    log "push succeeded — recovery complete"
    exit 0
else
    die "push still failed; manual intervention required (see git push output above)"
fi