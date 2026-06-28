#!/bin/bash
# append-to-vault.sh — append a note to the daily log or research log
# Usage:
#   ./append-to-vault.sh daily "What was done" "Decisions made" "Open items" "Notes for tomorrow"
#   ./append-to-vault.sh research "Research topic" "Question" "Sources" "Key findings" "Verdict"

VAULT_DIR="/root/Obsidian-Vaults/Hermes"
DAILY_DIR="$VAULT_DIR/daily_activities_log"
RESEARCH_DIR="$VAULT_DIR/research_log"
TODAY=$(date +%Y-%m-%d)
LOG_FILE="$VAULT_DIR/log.md"

# ── Daily activities entry ───────────────────────────────────────────────────
append_daily() {
    local done="$1"; shift
    local decisions="$1"; shift
    local blockers="$1"; shift
    local notes="$1"

    local file="$DAILY_DIR/$TODAY.md"

    if [ -f "$file" ]; then
        python3 - "$file" "$TODAY" "$done" "$decisions" "$blockers" "$notes" << 'PYEOF'
import sys, re

file, today, done, decisions, blockers, notes = sys.argv[1:]

with open(file) as f:
    raw = f.read()

sections = {
    "## What was done": done,
    "## Decisions made": decisions,
    "## Blockers / open items": blockers,
    "## Notes for tomorrow": notes,
}

# For each section: if header exists, replace content. If not, append at end.
content = raw
for header, value in sections.items():
    escaped = re.escape(header)
    pattern = rf"(\n{escaped}\n).*?(?=\n## |\Z)"
    replacement = f"\n{header}\n{value}\n"
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
    else:
        # Header not found — append after frontmatter + first blank line
        content = re.sub(r'(\n---\n)', r'\1\n' + f"{header}\n{value}\n", content)

# Update the updated date
content = re.sub(r"^updated: [0-9-]+", f"updated: {today}", content, flags=re.MULTILINE)

with open(file, "w") as f:
    f.write(content)
PYEOF
    else
        cat > "$file" << EOF
---
title: "Daily Log — $TODAY"
created: $TODAY
updated: $TODAY
type: summary
tags: [meta, daily-log]
confidence: high
---

## What was done
$done

## Decisions made
$decisions

## Blockers / open items
$blockers

## Notes for tomorrow
$notes
EOF
    fi

    echo "Daily log written: $file"
}

# ── Research log entry ───────────────────────────────────────────────────────
append_research() {
    local topic="$1"; shift
    local question="$1"; shift
    local sources="$1"; shift
    local findings="$1"; shift
    local verdict="$1"

    local slug=$(echo "$topic" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')
    local file="$RESEARCH_DIR/$TODAY-$slug.md"

    cat > "$file" << EOF
---
title: "$topic"
created: $TODAY
updated: $TODAY
type: summary
tags: [meta, research]
sources: [$sources]
confidence: medium
---

## Question
$question

## Sources consulted
$sources

## Key findings
$findings

## Verdict / next action
$verdict
EOF

    echo "Research log written: $file"
}

# ── Main ─────────────────────────────────────────────────────────────────────
MODE="$1"

if [ "$MODE" = "daily" ]; then
    append_daily "$2" "$3" "$4" "$5"
elif [ "$MODE" = "research" ]; then
    append_research "$2" "$3" "$4" "$5" "$6"
else
    echo "Usage:"
    echo "  $0 daily \"done\" \"decisions\" \"blockers\" \"notes\""
    echo "  $0 research \"topic\" \"question\" \"sources\" \"findings\" \"verdict\""
    exit 1
fi