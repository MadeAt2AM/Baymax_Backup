# VNC On-Demand — Verified Implementation

Companion to `vnc-on-demand-design.md`. Where that file is the **design sketch** (what to do, in theory), this file is the **verified implementation** (exactly what worked on cyberslide.terrybot.top, 2026-07-04).

## Why this exists separately

The design sketch was written **before** the implementation. After building it and verifying end-to-end, three things changed:

1. The two-service split is mandatory — not optional. Trying `Type=simple` + `ExecStartPost` with `exec websockify` **hangs systemd for 90s then fails with timeout**. The post-process becomes systemd's new long-runner and systemd doesn't know how to supervise it.
2. `tigervncserver :1` is a wrapper that renames itself to `/usr/bin/Xtigervnc :1` after fork. Grep patterns must match the renamed child, not the wrapper.
3. Orphan Chrome (`chrome --no-sandbox --disable-gpu`) from a prior session is functionally dead but holds ~235 MB per process (4-day-old case) and is **NOT** automatically reaped when Xtigervnc dies. The idle-killer must `pkill` it explicitly.

## Architecture as built

```
vnc-stack.service (Xtigervnc + XFCE)
       ↑
       | Requires= + PartOf=
       |
vnc-websockify.service (noVNC bridge 6080 -> 5901)
```

Both services as siblings, not parent-child via `ExecStartPost`. Websockify is a separate `Type=simple` service so systemd supervises it cleanly.

## Unit files (verbatim, working)

### `/etc/systemd/system/vnc-stack.service`

```ini
[Unit]
Description=VNC desktop stack (Xtigervnc + XFCE)
Documentation=https://github.com/TigerVNC/tigervnc
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
Environment=HOME=/root
Environment=DISPLAY=:1
Environment=XAUTHORITY=/root/.Xauthority
# -fg keeps Xtigervnc in the foreground so systemd can supervise it.
# -localhost=1 so only loopback clients can connect (we expose via noVNC).
ExecStart=/usr/bin/tigervncserver :1 -fg -xstartup /usr/bin/startxfce4 \
    -localhost=1 \
    -desktop cyberslide.terrybot.top:1 \
    -rfbport 5901 \
    -PasswordFile /root/.vnc/passwd \
    -SecurityTypes VncAuth \
    -geometry 1920x1200 \
    -depth 24

MemoryHigh=1000M
MemoryMax=1500M
Restart=no           # critical: idle-killer stops this on purpose
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

### `/etc/systemd/system/vnc-websockify.service`

```ini
[Unit]
Description=noVNC websockify bridge (6080 -> 5901)
After=vnc-stack.service
Requires=vnc-stack.service
PartOf=vnc-stack.service

[Service]
Type=simple
User=root
ExecStart=/usr/bin/websockify --web /usr/share/novnc --cert /root/.vnc/ssl.crt 6080 localhost:5901
Restart=on-failure
RestartSec=5
TimeoutStopSec=10
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

## Wrapper scripts (`/root/.hermes/scripts/vnc-stack/`)

Four scripts, all idempotent, all `bash -n` clean:

| Script | Purpose |
|---|---|
| `vnc-up [--wait]` | Start both services, optionally wait for port 6080 |
| `vnc-down [--force]` | Stop both services, kill orphan Chrome, clean X11 sockets |
| `vnc-status` | Per-service state, PIDs, ports, RSS totals, idle time |
| `vnc-idle-killer` | Check log mtime vs `IDLE_MIN`, tear down if stale |

Scripts are not inlined here — they're on disk at `/root/.hermes/scripts/vnc-stack/` and can be `cat`-ed when needed. Key behaviors:

- `vnc-up` returns 0 if already running (idempotent), 1 if start failed, blocks for port 6080 with `--wait` flag.
- `vnc-down` stops both services in reverse order (websockify first, then vnc-stack), then `pkill`s Xtigervnc, websockify, xfce4-session, xfwm4, xfdesktop, xfce4-panel, and orphan Chrome. Cleans up `/tmp/.X1-lock` and `/tmp/.X11-unix/X1`.
- `vnc-idle-killer` uses **log mtime** as the activity proxy — VNC appends to `/root/.vnc/<display>.log` on every connection event. `stat -c %Y` gives the last activity timestamp. If `NOW - mtime > IDLE_MIN * 60`, tear down. Default `IDLE_MIN=10`.

## Cron job

```
*/5 * * * * IDLE_MIN=10 /root/.hermes/scripts/vnc-stack/vnc-idle-killer >> /var/log/hermes-vnc/cron.log 2>&1
```

Logs teardown history to `/var/log/hermes-vnc/idle-killer.log`.

## Pitfalls hit during implementation (must-know)

### 1. `pgrep -q` doesn't exist

`pgrep` has no `-q` flag. Silent checks use `pgrep ... >/dev/null 2>&1`. Symptom: `pgrep: invalid option -- 'q'`. Gotcha caught on first run of `vnc-status`.

### 2. `Type=simple` + `ExecStartPost` with `exec` hangs systemd

If you put `ExecStartPost=/usr/bin/bash -c '... exec /usr/bin/websockify ...'` in the main service, **the websockify process replaces bash and becomes systemd's long-runner**. systemd's `Type=simple` doesn't know how to supervise a post-process, so it waits 90s then times out with `start-post operation timed out`. Fix: split into two services, use `Requires=` + `PartOf=`.

### 3. `tigervncserver :1` renames itself

The wrapper command is `/usr/bin/tigervncserver :1 -fg ...` but the long-running child is `/usr/bin/Xtigervnc :1 ...`. Grep patterns like `pgrep -f "tigervncserver :1"` miss it. Use `pgrep -f "Xtigervnc :1"` (the renamed process).

### 4. Orphan Chrome re-parents away from Xtigervnc

`chrome --no-sandbox --disable-gpu` launched without `--use-display=:1` (or launched after detaching) gets PPID=1 and survives Xtigervnc's death. The idle-killer needs an explicit `pkill -TERM -f "/opt/google/chrome/chrome --no-sandbox --disable-gpu"` to clean these up. Without it, you tear down VNC and Chrome stays at 235 MB each.

### 5. `/tmp/.X11-unix/X1` must be removed on teardown

After Xtigervnc dies, the X11 socket can persist if cleanup didn't run cleanly. A subsequent `tigervncserver :1` fails with "Display :1 is taken" until you `rm -f /tmp/.X1-lock /tmp/.X11-unix/X1`. Both `vnc-down` and `vnc-idle-killer` do this explicitly.

### 6. `Restart=no` is mandatory on the main service

If you set `Restart=always` or `Restart=on-failure`, then the idle-killer's `systemctl stop` triggers systemd to **immediately restart the service**. The killer becomes useless. Set `Restart=no` and rely on `vnc-up` for intentional restarts.

### 7. Don't enable the upstream `tigervncserver@1.service`

The Ubuntu package ships `/lib/systemd/system/tigervncserver@.service` — a template that auto-starts display :1 at boot. If you enable that AND `vnc-stack.service`, they fight over `/tmp/.X1-lock`. Either disable the upstream one or use `vnc-stack.service` exclusively.

### 8. Orphan Chrome — both true AND false positive in same session

The `chrome --no-sandbox --disable-gpu` running for 4 days looked identical to the false-positive tsserver pattern from earlier in the session. The discriminator was the **VNC attachment test**: check if `pgrep Xtigervnc` is alive. If yes → Chrome might be attached (false positive). If no → Chrome is truly orphaned (safe to kill).

This is the **opposite of the tsserver case** — there, the parent was alive and serving; here, the parent was dead. Same heuristic, different answer. Always trace the chain.

## Verification commands (used in the session)

```bash
# Service state
systemctl is-active vnc-stack.service
systemctl is-active vnc-websockify.service

# Listening ports
ss -tnl | grep -E ":(5901|6080) "

# noVNC web reachable
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:6080/vnc.html

# WebSocket → RFB protocol handshake (the real test)
curl -s -i \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  http://localhost:6080/websockify --max-time 3 | head -3
# Expect: HTTP/1.1 101 Switching Protocols
#         (followed by raw RFB 003.008 protocol bytes)

# External endpoint reachable
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://147.79.18.59:6080/vnc.html
```

## Measured savings

| State | Before | After |
|---|---|---|
| RAM used (idle, no VNC) | 5.2 GB | **3.2 GB** |
| RAM available | 2.6 GB | **4.6 GB** |
| VNC stack RSS (when up) | n/a (was always on) | 196 MB (clean XFCE) → 550 MB (with browser) |

## Verified

- **First deployed:** 2026-07-04 on cyberslide.terrybot.top
- **Reclaim:** 1.7 GB on idle (VNC stack torn down), 1.5 GB when VNC was previously always-on with browser
- **Verified end-to-end:** stack up via `vnc-up --wait`, WebSocket → RFB 003.008 handshake succeeded, external IP reachable, `vnc-down` tore down cleanly, `vnc-idle-killer` auto-tore down after IDLE_MIN=0 force test, `vnc-up` brought it back successfully
- **Cron:** `*/5 * * * * IDLE_MIN=10` installed, logged to `/var/log/hermes-vnc/idle-killer.log`