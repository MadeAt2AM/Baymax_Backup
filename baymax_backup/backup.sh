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
    log "gh CLI has no stored authentication — reading GITHUB_TOKEN from .env..."
    GH_TOKEN=$(python3 -c "
with open('/root/.hermes/.env') as f:
    for line in f:
        if line.startswith('GITHUB_TOKEN=') and not line.lstrip().startswith('#'):
            print(line.split('=', 1)[1].strip())
            break
" 2>/dev/null)
    if [[ -z "$GH_TOKEN" ]]; then
        logerr "No GITHUB_TOKEN found in /root/.hermes/.env — aborting."
        exit 1
    fi
    export GH_TOKEN
    if ! gh auth status &>/dev/null; then
        logerr "GitHub token validation failed."
        exit 1
    fi
    log "GitHub token validated successfully."
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
    if [[ -x /root/.hermes/.venv/bin/pip ]]; then
        /root/.hermes/.venv/bin/pip list 2>/dev/null | awk 'NR>2{print}' || true
    else
        echo "N/A (pip not installed in /root/.hermes/.venv)"
    fi
    echo ""
    echo "### NPM Global Packages"
    if command -v npm >/dev/null 2>&1; then
        npm list -g --depth=0 2>/dev/null | awk 'NR>1{print}' || true
    else
        echo "N/A (npm not installed)"
    fi
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

# Update RESTORATION_GUIDE.md with fresh analysis (append at end, then prepend header)
python3 << 'PYEOF'
import re

guide_path = '/root/baymax_backup/RESTORATION_GUIDE.md'
with open(guide_path) as f:
    guide = f.read()

with open('/tmp/analysis.tmp') as f:
    analysis = f.read()

# Remove old analysis block (if any — between markers)
guide = re.sub(
    r'\n## Environment Analysis — .*?(?=\n## Contact / Support\n)',
    '',
    guide,
    flags=re.DOTALL
)
# Remove the closing footer line if it was at the very end
guide = re.sub(r'\n\*This document is auto-generated.*', '', guide)

# Prepend new analysis at the top of the file
header = "## Environment Analysis — (auto-updated daily by backup cron)\n\n"
new_guide = guide.strip() + "\n\n" + header + analysis + "\n\n---\n\n*This document is auto-generated daily by /root/baymax_backup/backup.sh*\n"

with open(guide_path, 'w') as f:
    f.write(new_guide)
print('RESTORATION_GUIDE.md updated.')
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

# Push using Python to embed token (avoids credential helper issues)
python3 << 'PYEOF'
import subprocess, os

# Read token from .env — use a prefix search to avoid hardcoding the token value
TOKEN_PREFIX = 'GITHUB_TOKEN='
token = None
with open('/root/.hermes/.env') as f:
    for line in f:
        if line.startswith(TOKEN_PREFIX) and not line.strip().startswith('#'):
            token = line.split('=', 1)[1].strip()
            break

if not token:
    print("ERROR: No GITHUB_TOKEN found")
    exit(1)

token_remote = f'https://chrisvincodes:{token}@github.com/MadeAt2AM/Baymax_Backup.git'

# Set remote with token embedded
subprocess.run(['git', 'remote', 'set-url', 'origin', token_remote], cwd='/root', check=True)

# Push with explicit HOME so credential helpers don't interfere
result = subprocess.run(
    ['git', 'push', 'origin', 'main'],
    cwd='/root',
    capture_output=True,
    text=True,
    timeout=90,
    env={**os.environ, 'HOME': '/root', 'GIT_TERMINAL_PROMPT': '0'}
)
if result.returncode == 0:
    print("Push successful")
else:
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr[-500:])
    exit(1)
PYEOF

log "Daily backup finished successfully."
