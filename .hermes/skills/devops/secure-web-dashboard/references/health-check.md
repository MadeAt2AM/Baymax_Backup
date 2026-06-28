# Dashboard Health-Check Diagnostic

## Problem Pattern

Nginx is `active (running)` and returning a response, but it's a 502 or a connection-refused error — meaning the **backend dashboard is down** but nginx itself is fine.

This can happen silently: the `hermes-dashboard.service` goes `inactive (dead)` and stays dead until someone notices.

---

## Quick Diagnostic (run this first)

```bash
# 1. Is nginx healthy?
sudo systemctl status nginx --no-pager

# 2. Is the dashboard backend alive?
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119
# Expected: 200. Anything else = backend down.

# 3. Is the systemd service running?
sudo systemctl status hermes-dashboard.service --no-pager
# Look for: Active: active (running)
# If: Active: inactive (dead) → service crashed/stopped
```

---

## Common Cause: `hermes update` Kills the Dashboard

`hermes update` intentionally stops the dashboard after refreshing code and **does NOT restart it automatically**. After every update, the service stays dead.

**Evidence:** Check the update log:
```bash
tail -50 /root/.hermes/logs/hermes-update.log
```
Look for: `"Stopping N dashboard process(es)..."` followed by no restart entry.

---

## Fix: Restart the Dashboard

```bash
sudo systemctl restart hermes-dashboard.service
sleep 2

# Verify it's up
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119
# Should return 200

# Verify full chain through nginx
curl -k -u chrisspeaks:Cris0037 -s -o /dev/null -w "%{http_code}" https://dashboard.terrybot.top
# Should return 200
```

---

## Preventive: Watchdog Cron (Primary Defense)

`systemd Restart=always` handles crashes but does NOT recover from clean admin
stops or `hermes update`-triggered kills. A cron watchdog fills that gap.

The script is at `/root/.hermes/scripts/check-dashboard.sh` and the cron job
`hermes-dashboard-health` (job_id: `a0a18fe34a59`) runs it every 5 minutes,
alerting via Telegram only when a restart fires.

To verify it's working:
```bash
# Check last run output
cat /root/.hermes/cron/output/dashboard_health.log

# Check cron job status
cron list | grep dashboard
```

To manually trigger a health check:
```bash
/root/.hermes/scripts/check-dashboard.sh
```

The script silently logs "HEALTH: OK" when healthy, and writes a restart event
to the log + delivers to Telegram when it has to restart the service.

---

## Full Restart Sequence (when in doubt)

```bash
# 1. Stop dashboard (if somehow alive but broken)
sudo systemctl stop hermes-dashboard.service

# 2. Restart nginx (clears stale workers)
sudo systemctl restart nginx

# 3. Start dashboard fresh
sudo systemctl start hermes-dashboard.service
sleep 2

# 4. Verify
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119
sudo systemctl status hermes-dashboard.service --no-pager
```
