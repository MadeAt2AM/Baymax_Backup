# Service Watchdog Pattern

## The Problem

A critical service (API, web dashboard, background daemon) can go completely silent — **all resource metrics stay green** — while the service is dead. Classic pattern: a web server (nginx) keeps running and serving, but the backend it proxies to is dead. The proxy "looks alive" from outside but serves nothing.

Real example: `hermes-dashboard.service` went down for ~14h. Nginx was `active (running)`, returning HTTP 200 (from its error page), and all CPU/RAM/disk metrics were normal. Only a direct probe of the backend port revealed it was dead.

## The Pattern

For every critical long-running service, deploy two layers:

| Layer | Tool | What it catches |
|-------|------|----------------|
| Resource monitoring | `system-health-monitoring` skill | OOM, CPU saturation, disk full |
| Service health check | Watchdog cron (this pattern) | Service dead but resources OK |

## Watchdog Cron Recipe

### 1. Create the health-check script

```bash
cat > ~/.hermes/scripts/check-<service-name>.sh << 'SCRIPT'
#!/bin/bash
# <ServiceName> health check — restarts if backend unreachable
SERVICE="<service-name>.service"   # systemd service name
LOG="/root/.hermes/cron/output/<service-name>_health.log"
PORT=<port>                         # TCP port to probe

mkdir -p "$(dirname "$LOG")"

if ! curl -s -o /dev/null http://127.0.0.1:${PORT}; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: unreachable on :${PORT}, restarting ${SERVICE}..." >> "$LOG"
    systemctl restart "$SERVICE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: ${SERVICE} restarted" >> "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: OK — :${PORT} responding" >> "$LOG"
fi
SCRIPT
chmod +x ~/.hermes/scripts/check-<service-name>.sh
```

### 2. Schedule every 5 minutes

```
cron create \
  name="<service-name>-health" \
  --script "check-<service-name>.sh" \
  --schedule "*/5 * * * *" \
  --deliver telegram \
  --no-agent \
  --prompt "Run /root/.hermes/scripts/check-<service-name>.sh. Deliver stdout only if it contains 'restarting'. Silent when healthy."
```

**Key design:** `--no-agent` script-only job + Telegram delivery conditional on restart event. Stays silent when healthy — no spam, only alerts on actual restarts.

## Systemd Restart Policy

Even with a watchdog, systemd's own restart policy is the first line of defence. Configure it correctly:

```ini
[Service]
ExecStart=/path/to/service --flags
Restart=always          # always, not on-failure — on-failure does NOT restart after clean stops
RestartSec=10           # cooldown between restarts
MemoryMax=1.5G          # restart if RSS exceeds 1.5 GB
MemoryHigh=1.2G         # trigger restart if RSS sustained above 1.2 GB
TimeoutStartSec=60      # give service time to start before declaring dead
```

**Critical `Restart` values:**
- `no` — never restart (not recommended for any long-running service)
- `on-failure` — only on abnormal exit (crash, non-zero exit, signal kill). Does **NOT** restart after a clean `systemctl stop` or a service that exits cleanly on its own
- `always` — restart after any exit, including clean stops. Recommended for services that need to stay up

**The `--tui` trap:** If a service's `ExecStart` includes `--tui` or any global CLI flag that tries to attach an interactive terminal, it will crash in systemd daemon context. `--tui` is a **global flag** for the CLI tool, not a subcommand flag — it belongs in user-facing invocations, not service files.

## Checklist for New Services

Before declaring a service "monitored":

- [ ] `systemctl enable --now <service>.service`
- [ ] Service is `active (running)` and backend port responds `200`
- [ ] `systemctl status` shows no recent restarts or failures
- [ ] `journalctl -u <service> --no-pager -n 20` is clean
- [ ] Watchdog script created at `~/.hermes/scripts/check-<name>.sh` and verified executable
- [ ] Watchdog cron job created with `*/5 * * * *` schedule
- [ ] Confirmed Telegram alert fires when service is stopped manually

## Current Active Watchdogs (cyberslide)

| Service | Script | Cron Job ID | Schedule |
|---------|--------|-------------|----------|
| hermes-wiki-sync | `check-wiki-sync.sh` | `59cc5538d6a5` | `*/15 * * * *` |
| hermes-dashboard | `check-dashboard.sh` | `a0a18fe34a59` | `*/5 * * * *` |

## Pitfalls

- **Watchdog script probe port wrong** — always verify the actual listening port with `ss -tlnp | grep <service>` before writing the health check
- **Watchdog triggers restart loop** — if a service crashes immediately after every restart, the watchdog will spam restarts. Add `RestartSec=10` in systemd AND a back-off in the watchdog (skip restart if last restart was < 60s ago)
- **Delivery channel wrong** — `hermes send --to "telegram:CHAT_ID"` format, not a bare chat ID
