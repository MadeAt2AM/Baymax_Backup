#!/bin/bash
# Bidirectional sync script for Obsidian-Vaults / Hermes LLM Wiki
# Listens for filesystem changes and syncs with git remote
# Handles both local changes (inotifywait) and remote changes (git pull)

REPO_DIR="/root/Obsidian-Vaults"
LOG_FILE="$REPO_DIR/.sync.log"
GIT_DIR="$REPO_DIR/.git"

# Track last sync time to avoid rapid-fire syncs
LAST_SYNC=0
DEBOUNCE_SECONDS=5

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

do_sync() {
    local reason="$1"
    local now=$(date +%s)
    
    # Debounce: skip if we synced recently
    if [ $((now - LAST_SYNC)) -lt $DEBOUNCE_SECONDS ]; then
        log "Debounced: $reason"
        return
    fi
    
    log "Syncing: $reason"
    
    cd "$REPO_DIR" || exit 1
    
    # Save any staged changes first
    git add -A
    
    # Pull remote changes first (non-destructive merge)
    git fetch origin main 2>/dev/null
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse origin/main)
    BASE=$(git merge-base @ origin/main)
    
    if [ "$LOCAL" = "$REMOTE" ]; then
        log "Up-to-date, nothing to push"
    elif [ "$LOCAL" = "$BASE" ]; then
        log "Pulling remote changes..."
        git pull --rebase origin main 2>&1 | tee -a "$LOG_FILE"
    elif [ "$REMOTE" = "$BASE" ]; then
        log "Pushing local changes..."
        git push origin main 2>&1 | tee -a "$LOG_FILE"
    else
        log "Diverged — attempting merge pull"
        git pull origin main 2>&1 | tee -a "$LOG_FILE"
    fi
    
    LAST_SYNC=$(date +%s)
    log "Sync complete"
}

# Handle git lock removal gracefully
cleanup_locks() {
    find "$GIT_DIR" -name "*.lock" -delete 2>/dev/null
}

# Initial sync on startup
log "Wiki Sync daemon started (PID $$)"
cleanup_locks
do_sync "initial"

# Listen for filesystem changes on the Hermes wiki directory
inotifywait -m -r -e modify,create,delete,move "$REPO_DIR/Hermes" 2>/dev/null | while read -r directory events filename; do
    # Skip .git directory noise
    [ "${directory#*$REPO_DIR/.git}" != "$directory" ] && continue
    
    # Skip lock files
    [ "${filename##*.lock}" != "$filename" ] && continue
    
    do_sync "fs change: $events $filename"
done