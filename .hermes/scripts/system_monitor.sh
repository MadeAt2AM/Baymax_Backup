#!/bin/bash
# System resource monitor — logs metrics and alerts on thresholds
# Thresholds: CPU >80%, RAM >85%, Disk >90%

HERMES="/usr/local/lib/hermes-agent/venv/bin/hermes"
LOGFILE="/root/.hermes/cron/output/system_monitor.csv"
ALERT_LOG="/root/.hermes/cron/output/system_alerts.log"
STATEFILE="/root/.hermes/cron/output/.monitor_state"
TELEGRAM_TARGET="telegram:-1003300736345"

# Thresholds
THRESH_CPU=80
THRESH_RAM=85
THRESH_DISK=90

# Ensure output dir exists
mkdir -p "$(dirname "$LOGFILE")"

# Add CSV header if file doesn't exist
if [ ! -f "$LOGFILE" ]; then
    echo "timestamp,hostname,cpu_pct,ram_used_pct,ram_free_mb,disk_pct,load_1m,load_5m,alert" > "$LOGFILE"
fi

# Collect metrics
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
HOSTNAME=$(hostname)

# CPU usage via /proc/stat (reliable, no parse dependency on top output)
read -r cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq rest < /proc/stat
total=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
idle=$((cpu_idle + cpu_iowait))
CPU_PCT=$(awk -v total="$total" -v idle="$idle" "BEGIN {printf \"%.1f\", 100 * (1 - idle/total)}")

# Memory
RAM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
RAM_USED=$(free -m | awk '/^Mem:/{print $3}')
RAM_PCT=$(awk "BEGIN {printf \"%.1f\", ($RAM_USED/$RAM_TOTAL)*100}")
RAM_FREE=$(free -m | awk '/^Mem:/{print $7}')

# Disk
DISK_PCT=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')

# Load
LOAD_1M=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
LOAD_5M=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $2}' | tr -d ',')

# Check thresholds
ALERT_MSG=""
ALERT_FLAG="no"

CPU_INT=${CPU_PCT%.*}
RAM_INT=${RAM_PCT%.*}
DISK_INT=${DISK_PCT%.*}

if [ "$CPU_INT" -gt "$THRESH_CPU" ]; then
    ALERT_FLAG="cpu"
    ALERT_MSG="${ALERT_MSG}🔴 CPU at ${CPU_PCT}% (threshold: ${THRESH_CPU}%)"
fi

if [ "$RAM_INT" -gt "$THRESH_RAM" ]; then
    ALERT_FLAG="ram"
    ALERT_MSG="${ALERT_MSG} | 🟡 RAM at ${RAM_PCT}% (threshold: ${THRESH_RAM}%)"
fi

if [ "$DISK_INT" -gt "$THRESH_DISK" ]; then
    ALERT_FLAG="${ALERT_FLAG:+"${ALERT_FLAG},"}disk"
    ALERT_MSG="${ALERT_MSG} | 🟠 Disk at ${DISK_PCT}% (threshold: ${THRESH_DISK}%)"
fi

# Append to CSV log
echo "${TIMESTAMP},${HOSTNAME},${CPU_PCT},${RAM_PCT},${RAM_FREE},${DISK_PCT},${LOAD_1M},${LOAD_5M},${ALERT_FLAG}" >> "$LOGFILE"

# Send alert if threshold breached
if [ "$ALERT_FLAG" != "no" ]; then
    ALERT_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${ALERT_TIME}] ${ALERT_MSG}" >> "$ALERT_LOG"

    # Build Telegram message
    TEXT="⚠️ *System Alert* — ${HOSTNAME}
${ALERT_MSG}
📊 CPU: ${CPU_PCT}% | RAM: ${RAM_PCT}% | Disk: ${DISK_PCT}%
🕐 ${TIMESTAMP}"

    # Send via hermes send (reuses gateway credentials, no token needed)
    "$HERMES" send --to "$TELEGRAM_TARGET" "$TEXT" 2>/dev/null
fi
