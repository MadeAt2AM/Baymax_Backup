# VNC / GUI Service On-Demand Architecture

Reference design for moving always-on GUI services (VNC, X11, desktop browsers) to a "spin up on connection, tear down when idle" model.

## When this applies

You have a service that:
- Runs 24/7 but is only actively used for short bursts (cookie extraction, occasional remote desktop)
- Holds significant RAM (VNC server + browsers commonly = 1.5-2 GB)
- Has a clear "is anyone connected right now" signal (network port for VNC, websocket for noVNC)
- Can tolerate 5-10 seconds of startup latency on each activation

If the service is genuinely used constantly (gaming, live editing over VNC), don't bother — the complexity outweighs the savings.

## The three pieces

### Piece 1: Socket-activated systemd unit

Replace the manual `tigervncserver :1 -fg` invocation with a socket-activated unit. The VNC server only starts when something connects to port 6080 (noVNC) or 5901 (raw VNC).

`/etc/systemd/system/vnc-socket.socket`:
```ini
[Unit]
Description=noVNC socket (VNC on-demand)
Before=vnc-socket@.service

[Socket]
ListenStream=6080
Accept=no

[Install]
WantedBy=sockets.target
```

`/etc/systemd/system/vnc-socket@.service`:
```ini
[Unit]
Description=VNC desktop session (one-shot per connection)
After=network.target

[Service]
Type=simple
User=root
Environment=DISPLAY=:1
ExecStart=/usr/libexec/tigervncsession-start %i
TimeoutStopSec=30

[Install]
WantedBy=sockets.target
```

Caveats:
- Tigervnc's `startxfce4` xstartup launches a full desktop, so cold-start is 5-8 seconds. Acceptable for most workflows, painful for live editing.
- If multiple clients connect simultaneously, they all share the same X session. Add `-AlwaysShared` if multi-user is expected.

### Piece 2: Idle-killer watchdog cron

A cron job (every 5 min) that detects "no VNC client for N minutes" and tears the whole stack down.

`/root/.hermes/scripts/vnc-idle-killer.sh`:
```bash
#!/bin/bash
# Tear down VNC stack if no client connection for > 10 minutes
VNC_LOG="/root/.vnc/cyberslide.terrybot.top:1.log"
IDLE_LIMIT=600   # 10 minutes

LAST_TOUCH=$(stat -c %Y "$VNC_LOG" 2>/dev/null || echo 0)
NOW=$(date +%s)
IDLE=$((NOW - LAST_TOUCH))

if [ "$IDLE" -gt "$IDLE_LIMIT" ]; then
    echo "[$(date)] VNC idle for ${IDLE}s — tearing down"
    pkill -f Xtigervnc
    pkill -f "chrome.*--no-sandbox --disable-gpu"
    pkill -f "xfce4-session"
    pkill -f websockify
fi
```

The trick: VNC appends to its log on every client connection event. `stat -c %Y` (mtime) tells you when the last client activity was. No need to parse logs.

### Piece 3: Smart spin-up wrapper (in agent code)

When you (the agent) need the VNC browser for a task (cookie extraction, visual debug, screenshot), check if display :1 exists first:

```bash
ensure_vnc_running() {
    if ! pgrep -f "Xtigervnc :1" >/dev/null; then
        echo "VNC not running — spinning up..."
        tigervncserver :1 -fg -xstartup /usr/bin/startxfce4 &
        # Wait for X server to be ready
        for i in {1..20}; do
            if xdpyinfo -display :1 >/dev/null 2>&1; then
                echo "VNC ready after ${i}s"
                return 0
            fi
            sleep 1
        done
        echo "VNC failed to start in 20s"
        return 1
    fi
}
```

The agent calls this at the start of any VNC-dependent workflow. Cold start cost: 5-8 seconds, paid only when actually needed.

## Expected savings

| State | RAM (approx) |
|-------|--------------|
| Idle, no VNC | 1.7 GB less than always-on |
| VNC session active | Same as always-on (1.7 GB overhead while running) |
| VNC + cookie extraction peak | Same as always-on + extractor overhead |

For a VPS where VNC is used < 10% of the day, this is a 1.5+ GB reclaim on average.

## What's NOT in scope here

- Cookie/session persistence across restarts (the persistent profile dir at `~/.linkedin-mcp/profile/` already handles this — verify before tearing down)
- Browser session state — if you kill `chrome --no-sandbox --disable-gpu` while it's the only VNC-connected browser, the user loses unsaved tabs. Acceptable for cookie-extraction-only workflows, painful for browsing workflows
- Multiple concurrent users — socket activation assumes one user per session

## Validation approach

Before deploying this pattern, verify:
1. All VNC users have a way to trigger the spin-up (noVNC web UI works as the trigger)
2. The cookie/session files are stored on disk (not in-memory only)
3. The 5-10 second cold-start is acceptable for all use cases
4. There's a fallback if the socket activation unit fails (manual `tigervncserver :1` still works)

## Reference case

This design was developed for cyberslide.terrybot.top after observing:
- Xtigervnc idle for 4+ days (last client disconnect logged)
- Headless chrome from a prior cookie-extraction session running for 4 days, PPID=1, ~1.5 GB
- 1.7 GB total reclaimable by adding on-demand logic
- Design sketched 2026-07-04, not yet deployed