---
name: vps-ram-pressure
description: Diagnose and resolve high RAM utilization on a Linux VPS. Find which processes and services are eating memory, distinguish genuinely-needed workload from orphaned/over-provisioned processes, and apply safe mitigations that don't break active functionality. Covers systemd memory capping (MemoryHigh/MemoryMax drop-ins), swap file creation, journal vacuuming, broken-container cleanup, LSP/singleton-browser investigation pitfalls, and on-demand service architecture (VNC, GUI daemons). Use when RAM is >85%, swap is empty, OOM kills have happened, or a service "feels heavy" — anything from "what's eating my RAM" triage to a structured memory-pressure response.
triggers:
  - vps ram full
  - memory pressure
  - oom kill
  - high memory usage
  - find what's eating ram
  - reduce memory usage
  - memory cap systemd
  - service memory leak
  - swap file create
  - vnc on demand
---

# VPS RAM Pressure Response

Structured workflow for "VPS is running low on RAM — find the cause and fix without breaking things." Read once at start, then follow the diagnostic → triage → mitigation → verify loop.

## When to use this skill

Trigger on any of:
- `free -h` shows `available` < 1 GB on a < 8 GB box, or < 10% of total
- Swap = 0 (no safety net for spikes)
- OOM kills in `dmesg` or `journalctl`
- A specific service is suspected of leaking (`journalctl -u <svc>` shows restarts with memory growth)
- User reports "VPS is slow" / "everything is sluggish" / "X is using too much RAM"

## The four-step loop

1. **Diagnose** — what's actually eating RAM, right now
2. **Triage** — sort each hog into "critical" / "optimizable" / "dead weight"
3. **Mitigate** — apply Tier 1 (safe wins) before Tier 2 (with check-in) before Tier 3 (surgery)
4. **Verify** — measure before/after with `free -h` and live smoke test the affected services

---

## Step 1 — Diagnose

Run these in parallel to get a complete picture quickly:

```bash
free -h                              # total / used / available / swap
cat /proc/meminfo                    # anon vs file cache, swap total, dirty pages
ps aux --sort=-%mem | head -25       # top 25 RSS hogs by individual process
uptime                                # load average (CPU pressure vs memory pressure signal)
```

Then bucket the top processes into groups:

```bash
# Group by application family to see where the bulk lives
ps aux | grep -E "(chrome|chromium)" | grep -v grep | awk '{sum+=$6} END {printf "Chromium family: %.0f MB (%d procs)\n", sum/1024, NR}'
ps aux | grep -E "(node|tsserver)" | grep -v grep | awk '{sum+=$6} END {printf "Node/tsserver: %.0f MB (%d procs)\n", sum/1024, NR}'
ps aux | grep -E "(hermes)" | grep -v grep | awk '{sum+=$6} END {printf "Hermes stack: %.0f MB (%d procs)\n", sum/1024, NR}'
ps aux | grep -E "(Xtigervnc|Xorg|Xwayland)" | grep -v grep | awk '{sum+=$6} END {printf "X server/VNC: %.0f MB (%d procs)\n", sum/1024, NR}'
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"  # container memory
```

**Do NOT skip the docker stats call** — containers don't show in `ps aux` with normal process names.

### Hidden bloat checks

```bash
# Journal disk usage (not RAM, but sign of never-pruned system)
journalctl --disk-usage
du -sh /var/log/journal/

# Crash-looping services (zero RAM but constant restart churn)
docker ps -a --filter "status=restarting"
systemctl list-units --state=failed --no-pager

# Orphaned vs attached processes (see "Orphan detection pitfall" below)
```

---

## Step 2 — Triage

Build a table like this before touching anything:

| Category | Examples | Action |
|----------|----------|--------|
| **Critical workload** | gateway, dashboard, MCP servers, application code, currently-active LSP clients | Cap with `MemoryMax`, do NOT kill |
| **Optimizable** | Long-running browsers (LinkedIn MCP, headless chrome), accumulated journal, oversized caches | Cap, vacuum, or move to on-demand |
| **Dead weight** | Crash-looping containers, detached browser sessions from old workflows, swap=0 with disk space available | Stop, remove, or fill the gap |

**The cardinal rule:** every process you reap, you must trace to its parent first. "Looks orphaned" and "is orphaned" are different things. See the orphan-detection pitfall below.

---

## Step 3 — Mitigate

### Tier 1: Safe wins (do these first, zero functional impact)

#### 1a. Cap service memory via systemd drop-in (no upstream unit modification)

For any service with no `MemoryMax`, create a drop-in:

```bash
mkdir -p /etc/systemd/system/<service>.service.d
cat > /etc/systemd/system/<service>.service.d/memory-cap.conf <<EOF
[Service]
MemoryHigh=<soft_limit>
MemoryMax=<hard_limit>
EOF
systemctl daemon-reload
```

Sizing heuristics (8 GB host):

| Service type | MemoryHigh | MemoryMax |
|--------------|------------|-----------|
| Lightweight daemon (watchdog, gateway) | 1.5G | 2G |
| Web/proxy (nginx, dashboard) | 800M | 1.2G |
| Browser-heavy MCP (chromium-based) | 2G | 3G |
| Container runtime (docker) | — | — (let containers have their own cgroups) |

**Caps only take effect after `systemctl restart <service>`.** `daemon-reload` loads the override file but the running process keeps its current cgroup. For long-running services, schedule the restart for a low-traffic window or get explicit confirmation first.

**The gateway-self-restart trap:** If the service you're capping is the one currently executing your shell session (e.g. `hermes-gateway.service` running this very agent), `systemctl restart` from inside the session will kill the subprocess running the command. Use `systemd-run --user` or ask the user to restart from outside.

#### 1b. Add a swap file (only if disk has headroom)

```bash
df -h / | tail -1                          # confirm >= 4 GB free
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  echo "/swapfile none swap sw 0 0" >> /etc/fstab
  swapon /swapfile
fi
swapon --show                              # verify
```

**Size:** 2 GB on a 7-8 GB host is the sweet spot. Larger swap on SSD storage just hides OOM bugs by slowing them down — 2 GB is enough for spike absorption.

**Don't add swap to mask a real leak.** If you're swapping 1.7 GB constantly, you have a runaway service. Fix the cap, not the symptom.

#### 1c. Vacuum journal logs

```bash
journalctl --vacuum-size=200M --vacuum-time=7d
```

Typical win: 1-2 GB of disk reclaimed if the system has been up > 30 days. Not RAM, but indicates system hygiene.

#### 1d. Clean up crash-looping containers

```bash
docker ps -a --filter "status=restarting"
docker logs --tail 30 <container>          # check the actual error
```

**Don't blindly delete.** Common crash causes that need a fix, not a kill:
- `setpriv: setresuid failed: Operation not permitted` → container was started with `--cap-drop=ALL` and the entrypoint drops privileges (impossible without caps). Either add `--cap-add=SETUID` or remove the redundant privilege drop in the entrypoint.
- OOMKilled → container needs a higher memory limit
- Missing env var → fix the env, not the container

If the container is genuinely unused (e.g. `searxng-redis` when searxng itself has no REDIS_URL env), it's safe to stop and remove.

---

### Tier 2: With check-in (ask before doing)

#### 2a. Reap "orphaned" processes

**Always trace parent chains before any kill.** A process with PPID=1 isn't necessarily orphaned from systemd's perspective — many long-running services detach intentionally. See the orphan-detection pitfall.

#### 2b. Switch browser engines

Chromium-based MCP servers (LinkedIn, many Playwright integrations) hold a 1.5-2 GB singleton browser for the lifetime of the server. Firefox headless is ~30% lighter but:
- Library may hardcode `playwright.chromium.launch_persistent_context()` (LinkedIn MCP does — `core/browser.py:90`)
- Switching means forking/patching the library, not a config change
- Verify the MCP server exposes a browser-type knob before assuming this is a flip

#### 2c. Move long-running GUI to on-demand

For services like VNC/X11 that idle 90%+ of the time (nobody connected for days), convert to socket-activated + idle-killer pattern. See `references/vnc-on-demand-design.md` for the three-piece design and **`references/vnc-on-demand-impl.md` for the verified implementation** (working unit files, four wrapper scripts, cron schedule, and the 8 pitfalls that the design doc doesn't cover — incl. `pgrep -q` doesn't exist, `tigervncserver` renames itself to `Xtigervnc`, orphan Chrome re-parents away from Xtigervnc on death, `Restart=no` is mandatory on the main service, and the `Type=simple` + `ExecStartPost` trap that hangs systemd 90s).

---

### Tier 3: Bigger surgery

- Move heavy workloads to separate containers with hard cgroup limits
- Add a second swap volume (zram) for compress-and-cache
- Profile-and-optimize the application code itself

---

## Step 4 — Verify

After any change:

```bash
free -h                              # confirm available memory increased
swapon --show                        # confirm swap active
systemctl show <service> | grep -E "^Memory"   # confirm caps loaded
ps aux --sort=-%mem | head -10       # confirm new top offenders
```

Then **live smoke test** the affected services. `MemoryMax` loaded ≠ `MemoryMax` enforced. A gateway that just got capped to 2 GB still has its old 3 GB allocation in memory until restart, and the cap only applies to NEW allocations after restart.

For browser/MCP servers, run a single tool call and confirm the user-visible output, not just process startup. A LinkedIn MCP that restarts but can't authenticate cookies is worse than the leak.

---

## Orphan detection pitfall (CRITICAL)

**Symptom:** `ps aux` shows 10 tsserver processes, parent PID=1, started days ago. Looks like leaked sessions from old code-editing work. Tempting to `pkill -f tsserver` to free 1.5 GB.

**Reality:** Those processes are all children of one `typescript-language-server` instance which is itself a child of the gateway. Killing them breaks the gateway's own LSP stack — no more code completion, hover, diagnostics.

**Rule:** Before any `pkill` on what looks like an orphan:

```bash
# Trace to grandparent and great-grandparent
for pid in $(pgrep -f <suspect>); do
  ppid=$(awk '/PPid:/ {print $2}' /proc/$pid/status)
  gppid=$(awk '/PPid:/ {print $2}' /proc/$ppid/status 2>/dev/null)
  echo "PID=$pid PPID=$ppid GPPID=$gppid"
  cat /proc/$ppid/cmdline 2>/dev/null | tr '\0' ' '
  echo
done
```

Then check if the parent is itself alive and serving:

```bash
kill -0 $ppid 2>/dev/null && echo "PARENT ALIVE" || echo "PARENT DEAD"
ps -o lstart= -p $ppid
```

If the parent is `node /root/.hermes/lsp/bin/typescript-language-server --stdio` and is alive — **these are NOT orphans**, they're active LSP clients attached to live coding sessions. Killing them breaks the work.

**The right fix isn't `pkill`.** It's adding idle-timeout logic to the LSP launcher (`experimental.tsserver.maxIdleTime` in some configs, or wrap the launcher in a wrapper that SIGTERMs after N minutes of stdin silence).

**Distinguishing signal:**
- **Orphan from prior conversation:** PPID points to a process tree that ends in PID 1 with no gateway. Safe to reap.
- **Orphan from detached service:** PPID=1 but the service was started with `--detach` intentionally. Check `/var/log/<service>.log` for activity — if it's still logging work, it's not orphan.
- **Active session:** Parent or grandparent is the live gateway / dashboard. Don't touch.

**The orphan-detection rule applied both ways in 2026-07-04 session:** the same `chrome --no-sandbox --disable-gpu` process that looked like a false positive against `Xtigervnc :1` was **actually a true positive** because the parent Xtigervnc was also dead (orphaned since June 30). The discriminator was `pgrep Xtigervnc :1` returning empty — once that's empty, the orphan Chrome is genuinely orphaned and safe to kill. The same logic that protects LSP workers from being killed protects you from leaving zombies running when the upstream service is also dead.

---

## Common false positives

| Symptom | Looks like | Actually is |
|---------|------------|-------------|
| `chrome --no-sandbox --disable-gpu` running for 4 days, PPID=1 | Orphan from prior session | Browser launched without `--use-display=`, not connected to anything. Still using RAM but functionally dead. **Safe to kill ONLY if you confirm VNC/Xtigervnc is also dead** (verified on 2026-07-04: this was a real 4-day-old orphan after killing the old manual VNC). The same `pgrep Xtigervnc :1` check distinguishes active from dead. |
| `Xtigervnc :1` running with no clients | Wasted resources | Intentionally idle waiting for noVNC connection. Cap with `MemoryMax`, don't kill. |
| 10 `tsserver.js` processes, 200-400 MB each | Lingering workspaces | Active LSP clients for live code editing (one per open project). |
| `node /hermes/lsp/bin/typescript-language-server --stdio` | Single heavy node process | The launcher for all the workers above. Required. |

## Scripting pitfalls

- **`pgrep -q` does not exist.** `pgrep` has no quiet flag. Use `pgrep ... >/dev/null 2>&1` for silent checks. Symptom: `pgrep: invalid option -- 'q'` — caught on the first run of `vnc-status` during the 2026-07-04 session.
- **`tigervncserver :1` is a wrapper that renames itself** to `/usr/bin/Xtigervnc :1` after fork. Grep patterns must match the renamed child. `pgrep -f "tigervncserver :1"` returns empty; `pgrep -f "Xtigervnc :1"` finds it.
- **`Type=simple` + `ExecStartPost` with `exec <long-running-process>` hangs systemd for 90s** then fails with `start-post operation timed out`. The `exec` replaces the bash process with the post-process, which becomes systemd's new long-runner — and `Type=simple` doesn't know how to supervise post-processes. Fix: split into two services and use `Requires=` + `PartOf=` to keep them tied together.
- **Orphan Chrome from display :1 needs explicit `pkill`** in the idle-killer. It re-parents to PID 1 when Xtigervnc dies and won't die with it.

---

## Reference files

- `references/vnc-on-demand-design.md` — three-piece architecture (socket activation + idle killer cron + smart spin-up wrapper) for GUI services that idle 90%+ of the time
- `references/vnc-on-demand-impl.md` — **verified** implementation on cyberslide: working unit files, wrapper scripts (`vnc-up`/`vnc-down`/`vnc-status`/`vnc-idle-killer`), 8 pitfalls hit during build (incl. the `Type=simple` + `ExecStartPost` trap that hangs systemd for 90s, and the `pgrep -q` gotcha)
- `templates/memory-cap-dropin.conf` — copy-paste drop-in snippet for any systemd service

## Templates

- `templates/memory-cap-dropin.conf` — ready-to-use `[Service]` block with MemoryHigh/MemoryMax

## Verified

- First deployed: 2026-07-04 on cyberslide.terrybot.top
- Diagnosed: 6.8 GB used → 5.2 GB used, 1 GB → 2.6 GB available, swap added (2 GB), 1.3 GB journal reclaimed, dead container removed
- Patterns validated: orphan-detection (caught LSP false positive + a true positive for orphan Chrome from a 4-day-old session), singleton-browser architecture (LinkedIn MCP), systemd drop-in caps, swap file recipe, on-demand VNC stack (200 MB idle → ~1.5 GB reclaim when up + browser)