#!/bin/bash
# Hermes Dashboard health check — restarts the service if backend is unreachable
# Run via cron every 5 min as a secondary watchdog (systemd Restart=always is primary)

SERVICE="hermes-dashboard.service"
LOG="/root/.hermes/cron/output/dashboard_health.log"
PORT=9119

mkdir -p "$(dirname "$LOG")"

# Check if backend is responding
if ! curl -s -o /dev/null http://127.0.0.1:${PORT}; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: Dashboard backend on :${PORT} unreachable, restarting ${SERVICE}..." >> "$LOG"
    systemctl restart "$SERVICE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: ${SERVICE} restarted" >> "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: OK — dashboard on :${PORT} responding" >> "$LOG"
fi
