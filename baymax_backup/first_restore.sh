#!/bin/bash
# ============================================================
# Baymax First Restore Script
# Run this ONCE on a fresh VPS to restore Hermes from backup
# ============================================================
set -euo pipefail

echo "============================================"
echo " Baymax Backup — First Restore Script"
echo "============================================"
echo ""

# Check running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Run as root: sudo bash first_restore.sh"
   exit 1
fi

BACKUP_DIR="/root/baymax_backup"
RESTORE_DIR="/root"

echo "[1/8] Checking backup data..."
if [[ ! -f "$BACKUP_DIR/backup_data/.env.restore" ]]; then
    echo "❌ .env.restore not found. Run this from the backed-up VPS or extract the backup first."
    exit 1
fi
echo "✅ Backup data found."

echo ""
echo "[2/8] Restoring critical configuration files..."
mkdir -p "$RESTORE_DIR/.hermes"
cp "$BACKUP_DIR/backup_data/.env.restore"        "$RESTORE_DIR/.hermes/.env"
cp "$BACKUP_DIR/backup_data/config.yaml.restore"  "$RESTORE_DIR/.hermes/config.yaml"
cp "$BACKUP_DIR/backup_data/auth.json.restore"    "$RESTORE_DIR/.hermes/auth.json" 2>/dev/null || true
cp "$BACKUP_DIR/backup_data/kanban.db.restore"    "$RESTORE_DIR/.hermes/kanban.db" 2>/dev/null || true
cp "$BACKUP_DIR/backup_data/honcho.json.restore"  "$RESTORE_DIR/.hermes/honcho.json" 2>/dev/null || true
cp "$BACKUP_DIR/backup_data/channel_directory.json.restore" "$RESTORE_DIR/.hermes/channel_directory.json" 2>/dev/null || true
cp "$BACKUP_DIR/backup_data/SOUL.md.restore"      "$RESTORE_DIR/.hermes/SOUL.md"
echo "✅ Config files restored."

echo ""
echo "[3/8] Restoring Hermes directory structure..."
mkdir -p "$RESTORE_DIR/.hermes/"{skills,memories,projects,plugins,scripts,cron,hooks,state}
mkdir -p "$RESTORE_DIR/.hermes/backup_data" 2>/dev/null || true

# Copy skills (excluding very large ones — npm packages get rebuilt)
if [[ -d "$BACKUP_DIR/.hermes/skills" ]]; then
    cp -r "$BACKUP_DIR/.hermes/skills/"* "$RESTORE_DIR/.hermes/skills/" 2>/dev/null || true
fi

# Copy memories
if [[ -d "$BACKUP_DIR/.hermes/memories" ]]; then
    cp -r "$BACKUP_DIR/.hermes/memories/"* "$RESTORE_DIR/.hermes/memories/" 2>/dev/null || true
fi

# Copy projects
if [[ -d "$BACKUP_DIR/.hermes/projects" ]]; then
    cp -r "$BACKUP_DIR/.hermes/projects/"* "$RESTORE_DIR/.hermes/projects/" 2>/dev/null || true
fi

# Copy root-level projects
if [[ -d "$BACKUP_DIR/projects" ]]; then
    mkdir -p "$RESTORE_DIR/projects"
    cp -r "$BACKUP_DIR/projects/"* "$RESTORE_DIR/projects/" 2>/dev/null || true
fi

# Copy browser-search
if [[ -d "$BACKUP_DIR/browser-search" ]]; then
    cp -r "$BACKUP_DIR/browser-search" "$RESTORE_DIR/" 2>/dev/null || true
fi

# Copy Obsidian Vaults (LLM Wiki)
if [[ -d "$BACKUP_DIR/Obsidian-Vaults" ]]; then
    cp -r "$BACKUP_DIR/Obsidian-Vaults" "$RESTORE_DIR/" 2>/dev/null || true
fi
echo "✅ Directory structure restored."

echo ""
echo "[4/8] Restoring systemd services..."
if [[ -f "$BACKUP_DIR/backup_data/hermes-gateway.service.restore" ]]; then
    cp "$BACKUP_DIR/backup_data/hermes-gateway.service.restore" /etc/systemd/system/hermes-gateway.service
fi
if [[ -f "$BACKUP_DIR/backup_data/hermes-dashboard.service.restore" ]]; then
    cp "$BACKUP_DIR/backup_data/hermes-dashboard.service.restore" /etc/systemd/system/hermes-dashboard.service
fi
systemctl daemon-reload 2>/dev/null || true
echo "✅ Systemd services restored."

echo ""
echo "[5/8] Setting Python venv..."
cd /root/.hermes
python3 -m venv .venv 2>/dev/null || python3.12 -m venv .venv 2>/dev/null || true
. .venv/bin/activate
pip install --upgrade pip 2>/dev/null | tail -1
pip install pyyaml python-dotenv 2>/dev/null | tail -1
echo "✅ Python venv ready at /root/.hermes/.venv"

echo ""
echo "[6/8] Installing Node dependencies..."
if command -v npm &>/dev/null; then
    # Rebuild hermes node modules
    if [[ -d "/root/.hermes/node" ]]; then
        echo "   Note: .hermes/node not in backup (857MB). Hermes will rebuild on first start."
    fi
fi
echo "✅ Node.js $(node --version) / npm $(npm --version) available."

echo ""
echo "[7/8] Installing gh CLI (if not present)..."
if ! command -v gh &>/dev/null; then
    apt-get update -qq && apt-get install -y gh 2>&1 | tail -3
fi
echo "✅ gh $(gh --version | head -1) ready."

echo ""
echo "[8/8] Authenticate gh CLI..."
echo "   You need a GitHub PAT with repo scope for MadeAt2AM org."
echo "   Get it from: https://github.com/settings/tokens"
echo "   Then run: gh auth login --with-token"
echo "✅ Restore complete!"

echo ""
echo "============================================"
echo " Next Steps:"
echo "  1. gh auth login --with-token  (with a repo-scoped PAT)"
echo "  2. systemctl enable hermes-gateway hermes-dashboard"
echo "  3. systemctl start hermes-gateway"
echo "  4. Follow RESTORATION_GUIDE.md for full details"
echo "============================================"
