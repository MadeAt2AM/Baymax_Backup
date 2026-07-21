#!/bin/bash
# Hermes Dashboard health check — restarts the service if backend is unreachable
# Run via cron every 5 min as a secondary watchdog (systemd Restart=always is primary)

SERVICE="hermes-dashboard.service"
LOG="/root/.hermes/cron/output/dashboard_health.log"
LOCK="/root/.hermes/cron/dashboard-health.lock"
PORT=9119

mkdir -p "$(dirname "$LOG")"

# Prevent duplicate watchdog instances if the gateway is restarted or ticks overlap.
exec 9>"$LOCK"
flock -n 9 || exit 0

# Bound the probe. Without a timeout, a wedged dashboard can leave this cron
# run stuck for up to the scheduler's one-hour script limit.
if ! curl --fail --silent --show-error \
    --connect-timeout 2 --max-time 5 \
    -o /dev/null "http://127.0.0.1:${PORT}"; then
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    restart_msg="[$timestamp] HEALTH: Dashboard backend on :${PORT} unreachable, restarting ${SERVICE}..."
    printf '%s\n' "$restart_msg" | tee -a "$LOG"

    # Bound systemctl as well; a stuck stop/start must not wedge this watchdog.
    if timeout --signal=TERM --kill-after=5s 30s systemctl restart "$SERVICE"; then
        printf '[%s] HEALTH: %s restarted\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$SERVICE" | tee -a "$LOG"
    else
        rc=$?
        printf '[%s] HEALTH: %s restart failed (exit %s)\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$SERVICE" "$rc" | tee -a "$LOG" >&2
        exit "$rc"
    fi
else
    printf '[%s] HEALTH: OK — dashboard on :%s responding\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$PORT" >> "$LOG"
fi
