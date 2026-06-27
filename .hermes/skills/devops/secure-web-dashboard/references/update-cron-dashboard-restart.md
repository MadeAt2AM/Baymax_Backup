# Hermes Update Cron — Dashboard Restart Procedure

## Problem

`hermes update` runs `hermes update` which:
1. Kills any running dashboard process (via `_kill_stale_dashboard_processes()` in `hermes_cli/main.py`)
2. Prints *"Restart the dashboard when you're ready"* — but never restarts it

The result after every bi-daily update: 502 Bad Gateway on `dashboard.terrybot.top`.

## Root Cause

`hermes update` intentionally stops stale dashboard processes because the running Python backend no longer matches the newly-pulled frontend JS bundle. However it has no mechanism to restart them (no saved launch args in systemd-less environments).

## Correct Cron Sequence

The bi-daily update cron (`6e32c4bc5ea6`) runs this exact sequence:

```bash
# 1. Stop dashboard BEFORE update — avoids stale-process conflict on port 9119
systemctl stop hermes-dashboard

# 2. Run the update
hermes update

# 3. Restart dashboard AFTER update
systemctl start hermes-dashboard

# 4. Verify dashboard is up
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119/
# Expected: 200

# 5. Verify gateway still running
systemctl status hermes-gateway --no-pager | grep "Active:"
# Expected: active (running)

# 6. Verify nginx proxy
curl -s -o /dev/null -w "%{http_code}" https://dashboard.terrybot.top/
# Expected: 401 (Basic Auth challenge = nginx proxy healthy)

# 7. Send status to Telegram
```

## Address-In-Use Error (EADDRINUSE)

If the dashboard fails to start after update with this error:
```
ERROR: [Errno 98] error while attempting to bind on address ('127.0.0.1', 9119): address already in use
```

A **manual process** from a previous manual `hermes dashboard --port 9119` is holding the port. The systemd service cannot start because the port is occupied.

**Fix:**
```bash
# Find the rogue process
ps aux | grep "hermes dashboard" | grep -v grep

# Kill it (replace PID with actual)
kill <PID>

# Then start the service
systemctl start hermes-dashboard
```

The rogue process typically originates from a `hermes dashboard` run manually in a terminal session that was later detached but not killed.

## Log Locations

- Update log: `/root/.hermes/logs/hermes-update.log`
- Dashboard logs: `journalctl -u hermes-dashboard --no-pager`
- Gateway logs: `journalctl -u hermes-gateway --no-pager`

## Known Issue Flag

After any `hermes update`, always assume the dashboard needs restarting until proven otherwise. Do not wait for a user complaint.