#!/bin/bash
# ============================================================
# Baymax Backup Script — /root context
# Run manually:  bash /root/baymax_backup/backup.sh
# Run via cron:  00 00 * * * cd /root && bash baymax_backup/backup.sh
#
# Backs up /root to GitHub, analyses env, updates RESTORATION_GUIDE.md
# ============================================================

set -euo pipefail

GIT_DIR="/root"
BACKUP_SUBDIR="/root/baymax_backup"
REPO="MadeAt2AM/Baymax_Backup"
BRANCH="main"
LOG_PREFIX="[Baymax Backup]"

log()   { echo "$LOG_PREFIX $(date '+%Y-%m-%d %H:%M:%S') — $1"; }
logerr(){ echo "$LOG_PREFIX ERROR: $1" >&2; }

# ── 1. Authenticate gh ─────────────────────────────────────
log "Starting daily backup..."

if ! gh auth status &>/dev/null; then
    log "gh not authenticated — reading token from .env via Python..."
    GH_TOKEN=***
    # Extract token cleanly via Python
    GH_TOKEN=$(python3 -c "
import re
with open('/root/.hermes/.env') as f:
    for line in f:
        if 'GITHUB_TOKEN=*** in line and not line.strip().startswith('#'):
            print(line.split('=',1)[1].strip())
            break
" 2>/dev/null)
    if [[ -z "$GH_TOKEN" ]]; then
        logerr "No GITHUB_TOKEN found in /root/.hermes/.env — aborting."
        exit 1
    fi
    echo "$GH_TOKEN" | gh auth login --with-token 2>/dev/null || {
        logerr "gh auth login failed."
        exit 1
    }
    log "gh authenticated successfully."
fi

# ── 2. Git add ─────────────────────────────────────────────
log "Analysing changes since last backup..."
cd "$GIT_DIR"

# Stage everything in baymax_backup subdir and any top-level hermes config
git add \
    baymax_backup/ \
    .hermes/.env \
    .hermes/config.yaml \
    .hermes/auth.json \
    .hermes/kanban.db \
    .hermes/SOUL.md \
    .hermes/honcho.json \
    .hermes/channel_directory.json \
    .hermes/skills/ \
    .hermes/memories/ \
    .hermes/projects/ \
    .hermes/plugins/ \
    .hermes/scripts/ \
    .hermes/cron/ \
    .hermes/state/ \
    projects/ \
    hermes-video-serve/ \
    madeat2am-council/ \
    hf-bug-report/ \
    browser-search/ \
    Obsidian-Vaults/ \
    2>/dev/null || true

CHANGES=$(git diff --cached --stat 2>/dev/null || echo "")
if [[ -z "$CHANGES" ]]; then
    log "No changes since last backup — nothing to push."
    exit 0
fi

log "Changes detected:\n$CHANGES"

# ── 3. Environment Analysis ─────────────────────────────────
log "Running environment analysis..."

ANALYSIS_FILE="/tmp/analysis.tmp"
{
    echo "## Environment Analysis — $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo ""
    echo "### System Packages (user-installed)"
    dpkg -l 2>/dev/null | grep "^ii" | awk '{print $2, $3}' | sort
    echo ""
    echo "### Hermes Python Packages"
    /root/.hermes/.venv/bin/pip list 2>/dev/null | awk 'NR>2{print}'
    echo ""
    echo "### NPM Global Packages"
    npm list -g --depth=0 2>/dev/null | awk 'NR>1{print}'
    echo ""
    echo "### Node / NPM Versions"
    echo "node:  $(node --version 2>/dev/null || echo N/A)"
    echo "npm:   $(npm --version 2>/dev/null || echo N/A)"
    echo "npx:   $(npx --version 2>/dev/null || echo N/A)"
    echo "uv:    $(uv --version 2>/dev/null || echo N/A)"
    echo ""
    echo "### Docker Containers"
    docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || echo "docker not running"
    echo ""
    echo "### Listening Ports"
    ss -tlnp 2>/dev/null | grep LISTEN || ss -tln 2>/dev/null
    echo ""
    echo "### Hermes Config Summary"
    python3 -c "
import re
with open('/root/.hermes/config.yaml') as f:
    txt = f.read()
m = re.search(r'^model:\s*\n\s+default:\s*(\S+)', txt, re.M)
p = re.search(r'^model:\s*\n\s+provider:\s*(\S+)', txt, re.M)
b = re.search(r'^model:\s*\s*\n\s+base_url:\s*(\S+)', txt, re.M)
fb = len(re.findall(r'^  fallback_providers', txt))
ts = re.findall(r'^\s+-\s*(\S+)', txt)
ts = [t for t in ts if t not in ['fallback_providers','providers']]
sk = re.search(r'external_dirs:\s*\n(.*?)(?=\n\s+\w|\n\s+\w|\n\w|\n---)', txt, re.DOTALL)
print('  Default model:', m.group(1) if m else 'N/A')
print('  Provider:', p.group(1) if p else 'N/A')
print('  Base URL:', b.group(1) if b else 'N/A')
print('  Fallback providers:', fb)
print('  Toolsets count:', len(ts))
sk_dirs = [l.strip().strip('-').strip() for l in sk.group(1).split('\n') if l.strip()] if sk else []
print('  Skills external_dirs:', sk_dirs if sk_dirs else '[]')
" 2>/dev/null || echo "  (config parse error)"
    echo ""
    echo "### Cron Jobs"
    crontab -l 2>/dev/null || echo "no cron jobs"
    echo ""
    echo "### Largest Hermes Directories"
    du -sh /root/.hermes/skills 2>/dev/null || echo "N/A"
    du -sh /root/.hermes/memories 2>/dev/null || echo "N/A"
    du -sh /root/.hermes/projects 2>/dev/null || echo "N/A"
    du -sh /root/.hermes/plugins 2>/dev/null || echo "N/A"
    du -sh /root/browser-search 2>/dev/null || echo "N/A"
    echo ""
    echo "### Disk Usage (/)"
    df -h / 2>/dev/null | tail -1
    echo ""
    echo "### Systemd Services (Hermes)"
    systemctl list-units --type=service --state=running --no-pager 2>/dev/null | grep hermes || echo "hermes services not running or not found"
} > "$ANALYSIS_FILE"

# Update RESTORATION_GUIDE.md with fresh analysis
python3 << 'PYEOF'
import re

guide_path = '/root/baymax_backup/RESTORATION_GUIDE.md'
with open(guide_path) as f:
    guide = f.read()

with open('/tmp/analysis.tmp') as f:
    analysis = f.read()

# Replace the analysis section between markers
pattern = r'(## Environment Analysis\n+> [^\n]*\n)(## Step-by-step Restore)'
if re.search(pattern, guide):
    new_guide = re.sub(pattern, r'\1' + analysis + r'\n\2', guide, flags=re.DOTALL)
    with open(guide_path, 'w') as f:
        f.write(new_guide)
    print('RESTORATION_GUIDE.md updated.')
else:
    print('WARNING: Could not find analysis section marker in guide.')
PYEOF
rm -f /tmp/analysis.tmp

# Stage updated guide
git add baymax_backup/RESTORATION_GUIDE.md

# ── 4. Commit & Push ────────────────────────────────────────
COMMIT_MSG="Backup $(date '+%Y-%m-%d %H:%M')"

log "Committing..."
git commit -m "$COMMIT_MSG" 2>/dev/null || {
    log "Nothing new to commit."
    exit 0
}

log "Pushing to https://github.com/$REPO ..."
if git push "https://github.com/$REPO.git" "$BRANCH"; then
    log "✅ Backup complete — pushed to https://github.com/$REPO"
else
    logerr "Push failed — check git remote and authentication."
    exit 1
fi

log "Daily backup finished successfully."
