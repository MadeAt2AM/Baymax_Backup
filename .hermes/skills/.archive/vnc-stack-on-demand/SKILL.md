---
name: vnc-stack-on-demand
description: Spin up the VNC desktop stack only when needed, tear it down on idle. Use when VNC is requested or when RAM pressure requires reclaiming Xtigervnc + XFCE + websockify memory.
---

# VNC Stack On-Demand

Persistent VNC/XFCE + noVNC eats ~600 MB idle, ~1.5 GB with browser work. This procedure keeps it stopped and only spins it up when a session needs it.

## Architecture

Two systemd services (split because systemd `Type=simple` can't supervise websockify as `ExecStartPost` cleanly):

| Service | Role | Memory cap |
|---|---|---|
| `vnc-stack.service` | `tigervncserver :1 -fg -xstartup /usr/bin/startxfce4` | 1.5 GB |
| `vnc-websockify.service` | `websockify --web /usr/share/novnc 6080 localhost:5901` | (no cap — ~30 MB) |

`PartOf=` + `Requires=` tie them together so they start/stop as one unit. `Restart=no` on the main service is critical — the idle-killer stops it on purpose and we don't want systemd to bring it back immediately.

## Wrapper scripts

`/root/.hermes/scripts/vnc-stack/`:
- `vnc-up [--wait]` — start both services, optionally wait for port 6080
- `vnc-down [--force]` — stop both services, kill orphaned Chrome from display :1, clean X11 sockets
- `vnc-status` — per-service state, PID, ports, RSS, idle time
- `vnc-idle-killer` — check VNC log mtime vs `IDLE_MIN` env (default 10), tear down if stale

## Idle detection

Heuristic: if `/root/.vnc/cyberslide.terrybot.top:1.log` mtime > N minutes old, no client has connected — tear down. VNC writes to this log on every connection/disconnection, so it's a reliable heartbeat proxy without needing to sniff websockify sockets.

## Cron job

```
*/5 * * * * IDLE_MIN=10 /root/.hermes/scripts/vnc-stack/vnc-idle-killer >> /var/log/hermes-vnc/cron.log 2>&1
```

Cleans teardown log at `/var/log/hermes-vnc/idle-killer.log`.

## Usage from Hermes

When a task needs browser interaction through VNC:

```bash
vnc-up --wait && <do work> && # leave it running, idle-killer takes care of it later
```

The cost is 5-15 seconds of startup before the action runs. Save **1.5 GB RAM** during idle periods.

## Verification commands

```bash
vnc-status                                  # see state + RSS
ss -tnl | grep -E ":(5901|6080) "           # check listeners
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:6080/vnc.html
curl -s -i -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  http://localhost:6080/websockify --max-time 3 | head -3
# Expect: HTTP/1.1 101 Switching Protocols
```

## Pitfalls

1. **`pgrep -q` doesn't exist** — use `pgrep ... >/dev/null 2>&1` for silent checks. Symptom: `pgrep: invalid option -- 'q'`.
2. **`tigervncserver` renames itself** — the long-running child is `/usr/bin/Xtigervnc :1`, not the wrapper. Grep for `Xtigervnc :1`.
3. **`Type=simple` + `ExecStartPost` with `exec` hangs systemd** — the post-process becomes the new long-runner and systemd waits forever. Fix: split into two services, use `Requires=` + `PartOf=`.
4. **Orphan Chrome from prior sessions** — Chrome launched with `--no-sandbox --disable-gpu` and parent=init (PPID 1) re-parents away from Xtigervnc and survives its death. `vnc-down` has explicit `pkill` for these.
5. **`X11-unix/X1` socket left behind** — must be removed on teardown or new Xtigervnc fails with "Display :1 is taken". Handled in `vnc-down`.
6. **Don't enable `tigervncserver@1.service`** — that's the upstream template that auto-starts display :1 at boot. We use `vnc-stack.service` instead.
7. **Gateway restart from inside the gateway session is blocked** — runtime check at `tools/terminal_tool.py:2237` returns SIGTERM. Restart `vnc-stack` from outside via cron/systemd, not from inside an active terminal session that depends on it.

## History

- 2026-07-04: Created during RAM investigation. Original VNC was a manual `tigervncserver :1 -fg` started June 30 with last client disconnect on July 2 — 2 days idle, eating ~550 MB. New system auto-tears down after 10 min idle, saving ~1.5 GB during cookie-extraction sessions and ~200 MB during normal XFCE use.