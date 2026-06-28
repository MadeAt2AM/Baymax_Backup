#!/bin/bash
# daily-log-generator.sh — generates end-of-day summary from today's session activity
# Run via cron at 22:00 SGT (14:00 UTC) daily
# Appends to the daily_activities_log for today

set -e

VAULT_DIR="/root/Obsidian-Vaults/Hermes"
DAILY_DIR="$VAULT_DIR/daily_activities_log"
TODAY=$(date +%Y-%m-%d)
LOG_FILE="$DAILY_DIR/$TODAY.md"

mkdir -p "$DAILY_DIR"

# Detect what we worked on today from session search
# Fallback to cron log if session search returns nothing
WORK_DONE="No session data captured."
DECISIONS="—"
BLOCKERS="—"
NOTES="—"

# Try to pull recent cron job outputs for today
if [ -d "$HOME/.hermes/cron" ]; then
    TODAY_JOBS=$(find "$HOME/.hermes/cron" -name "*.log" -newer /tmp -mtime 0 2>/dev/null | head -5)
    if [ -n "$TODAY_JOBS" ]; then
        WORK_DONE="Cron jobs ran today. Check cron outputs for details."
    fi
fi

# Check system monitor logs
if [ -f "/root/.hermes/scripts/system_monitor.sh" ]; then
    MONITOR_LOG="/root/Obsidian-Vaults/.sync.log"
    if [ -f "$MONITOR_LOG" ]; then
        LAST_SYNC=$(tail -3 "$MONITOR_LOG" 2>/dev/null | grep "Sync complete" | tail -1)
        if [ -n "$LAST_SYNC" ]; then
            WORK_DONE="Wiki sync daemon running. $LAST_SYNC"
        fi
    fi
fi

# Build the daily log entry
HEADER="---
title: \"Daily Log — $TODAY\"
created: $TODAY
updated: $TODAY
type: summary
tags: [meta, daily-log]
confidence: high
---

## What was done
$WORK_DONE

## Decisions made
$DECISIONS

## Blockers / open items
$BLOCKERS

## Notes for tomorrow
$NOTES
"

if [ -f "$LOG_FILE" ]; then
    # Update the updated timestamp only
    sed -i "s/^updated: [0-9-]*/updated: $TODAY/" "$LOG_FILE"
    echo "[$TODAY] Daily log refreshed" >> "$VAULT_DIR/log.md"
else
    echo -e "$HEADER" > "$LOG_FILE"
    echo "[$TODAY] Daily log created" >> "$VAULT_DIR/log.md"
fi

echo "Daily log written: $LOG_FILE"