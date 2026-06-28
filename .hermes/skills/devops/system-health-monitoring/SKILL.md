---
name: system-health-monitoring
description: Monitor CPU, RAM, disk, and load on the host every 15 minutes. Log to CSV and alert via Telegram when thresholds are breached.
triggers:
  - system monitor
  - resource alert
  - cpu ram disk bottleneck
  - server health
---

# System Health Monitoring

Monitor CPU, RAM, disk, and load on the host every 15 minutes. Log to CSV and alert via Telegram when thresholds are breached.

## Setup

### 1. Create the monitoring script

Location: `~/.hermes/scripts/system_monitor.sh`

```bash
#!/bin/bash
# System resource monitor — logs metrics and alerts on thresholds
# Thresholds: CPU >80%, RAM >85%, Disk >90%

HERMES="/usr/local/lib/hermes-agent/venv/bin/hermes"   # full path required — cron strips PATH
LOGFILE="/root/.hermes/cron/output/system_monitor.csv"
ALERT_LOG="/root/.hermes/cron/output/system_alerts.log"
TELEGRAM_TARGET="telegram:-1003300736345"   # format: telegram:chat_id (or telegram:chat_id:thread_id)
THRESH_CPU=80
THRESH_RAM=85
THRESH_DISK=90

mkdir -p "$(dirname "$LOGFILE")"

# CSV header
[ ! -f "$LOGFILE" ] && echo "timestamp,hostname,cpu_pct,ram_used_pct,ram_free_mb,disk_pct,load_1m,load_5m,alert" > "$LOGFILE"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
HOSTNAME=$(hostname)

# CPU via /proc/stat — reliable in all environments (top output format varies across distros)
read -r cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq rest < /proc/stat
total=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
idle=$((cpu_idle + cpu_iowait))
CPU_PCT=$(awk -v total="$total" -v idle="$idle" 'BEGIN {printf "%.1f", 100 * (1 - idle/total)}')

# RAM: free -m uses MiB, column 7 = available
RAM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
RAM_USED=$(free -m | awk '/^Mem:/{print $3}')
RAM_PCT=$(awk "BEGIN {printf \"%.1f\", ($RAM_USED/$RAM_TOTAL)*100}")
RAM_FREE=$(free -m | awk '/^Mem:/{print $7}')

# Disk
DISK_PCT=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')

# Load
LOAD_1M=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
LOAD_5M=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $2}' | tr -d ',')

# Thresholds
ALERT_MSG=""
ALERT_FLAG="no"
CPU_INT=${CPU_PCT%.*}; RAM_INT=${RAM_PCT%.*}; DISK_INT=${DISK_PCT%.*}

[ "$CPU_INT" -gt "$THRESH_CPU" ] && { ALERT_FLAG="cpu"; ALERT_MSG="${ALERT_MSG}🔴 CPU at ${CPU_PCT}% (threshold: ${THRESH_CPU}%)"; }
[ "$RAM_INT" -gt "$THRESH_RAM" ]  && { ALERT_FLAG="ram"; ALERT_MSG="${ALERT_MSG} | 🟡 RAM at ${RAM_PCT}% (threshold: ${THRESH_RAM}%)"; }
[ "$DISK_INT" -gt "$THRESH_DISK" ] && { ALERT_FLAG="${ALERT_FLAG:+\"${ALERT_FLAG},\"}disk"; ALERT_MSG="${ALERT_MSG} | 🟠 Disk at ${DISK_PCT}% (threshold: ${THRESH_DISK}%)"; }

# Log
echo "${TIMESTAMP},${HOSTNAME},${CPU_PCT},${RAM_PCT},${RAM_FREE},${DISK_PCT},${LOAD_1M},${LOAD_5M},${ALERT_FLAG}" >> "$LOGFILE"

# Alert
if [ "$ALERT_FLAG" != "no" ]; then
  echo "[$(date)] ${ALERT_MSG}" >> "$ALERT_LOG"
  TEXT="⚠️ *System Alert* — ${HOSTNAME}
${ALERT_MSG}
📊 CPU: ${CPU_PCT}% | RAM: ${RAM_PCT}% | Disk: ${DISK_PCT}%
🕐 ${TIMESTAMP}"

  # hermes send reuses gateway credentials — full path required in cron environment
  "$HERMES" send --to "$TELEGRAM_TARGET" "$TEXT" 2>/dev/null
fi
```

### 2. Make executable and verify

```bash
chmod +x ~/.hermes/scripts/system_monitor.sh
~/.hermes/scripts/system_monitor.sh
cat ~/.hermes/cron/output/system_monitor.csv
```

A clean row should have all numeric values. A blank `cpu_pct` means `top` parsing failed — **use `/proc/stat` instead** (see script above). This was the root cause of silent alert failures: `top -bn1` output format varies across distros and in cron environments.

### 3. Schedule via cron job

```bash
cronjob action=create \
  name="System Resource Monitor" \
  schedule="*/15 * * * *" \
  script="system_monitor.sh" \
  no_agent=true \
  deliver=local
```

**Critical:** `script` must be a bare filename relative to `~/.hermes/scripts/`. Absolute paths and `~` are rejected.

## Alerts

When a threshold is breached:
- Row in `system_monitor.csv` tagged `alert=cpu|ram|disk`
- Telegram message sent to `TELEGRAM_TARGET`
- Entry written to `system_alerts.log`

Silent when healthy — no messages, CSV grows quietly in background.

## Thresholds

| Metric | Default | Variable |
|--------|---------|----------|
| CPU | 80% | `THRESH_CPU` |
| RAM | 85% | `THRESH_RAM` |
| Disk | 90% | `THRESH_DISK` |

To change the alert channel: patch `TELEGRAM_TARGET` in the script. Format is `telegram:chat_id` (e.g. `telegram:-1003300736345` for a group, `telegram:1283992553` for a user).

## Pitfalls

- **`top -bn1` for CPU is unreliable** — use `/proc/stat` instead (see script above). The `Cpu(s)` line format differs across distros; in cron environments it can produce blank values causing silent metric gaps.
- **hermes not on PATH in cron** — always use the full path `/usr/local/lib/hermes-agent/venv/bin/hermes` in scripts run by cron.
- **hermes send syntax** — correct form is `hermes send --to "telegram:CHAT_ID"` not `hermes send telegram CHAT_ID`.
- **Integer truncation on thresholds** — `CPU_INT=${CPU_PCT%.*}` truncates 2.4% to 2. So `THRESH_CPU=2` only fires if CPU > 2%, not ≥ 2%. Use a threshold safely below your intended trigger (e.g. `THRESH_CPU=-1` to catch anything > 0%, `THRESH_CPU=79` to catch ≥ 80%).

## Log Locations

```
~/.hermes/cron/output/system_monitor.csv   # metrics log
~/.hermes/cron/output/system_alerts.log   # alert history
```

## Scope

This skill covers **resource saturation** (CPU, RAM, disk). Services can go down silently while all resource metrics stay green — a dead backend behind a running proxy is invisible to resource monitoring alone. See `references/service-watchdog-pattern.md` for the companion watchdog pattern.

## Verified

- Created: 2026-06-27
- Updated: 2026-06-28 (added service watchdog pattern reference)
- Host: cyberslide.terrybot.top (147.79.18.59)
- Job ID: `f52e7fc82801`
- Status: Running
