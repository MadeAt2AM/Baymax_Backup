# Scheduled Backup Runtime Isolation

## Symptom

A backup launched from a Hermes routine prints only its initial line and then appears hung. Ordinary diagnostics launched from the same gateway context may also stall.

## Diagnostic pattern

1. Inspect the process state and wait channel under `/proc/<pid>/status` and `/proc/<pid>/wchan`.
2. Walk the child PID chain using `/proc/<pid>/task/<pid>/children`.
3. Inspect the gateway service cgroup:
   - `/sys/fs/cgroup/system.slice/hermes-gateway.service/memory.current`
   - `memory.high`
   - `memory.events`
   - `memory.pressure`
4. A child in `mem_cgroup_handle_over_high`, with `memory.current` above `memory.high` and sustained memory pressure, indicates cgroup throttling rather than a Git or network fault.

## Recovery pattern

Run the bounded backup in an isolated transient systemd service with unrestricted memory controls:

```bash
systemd-run --wait --pipe --collect \
  --unit=baymax-backup-retry-$(date +%Y%m%d%H%M%S) \
  --property=MemoryHigh=infinity \
  --property=MemoryMax=infinity \
  /bin/bash /root/baymax_backup/backup.sh
```

If `gh auth status` is the throttled preflight, export the existing token into the transient unit so `gh` uses non-interactive environment authentication:

```bash
export GH_TOKEN="$(python3 -c 'p="/root/.hermes/.env"; print(next((x.split("=",1)[1].strip() for x in open(p) if x.startswith("GITHUB_TOKEN=") and not x.strip().startswith("#")), ""))')"
```

Do not print the token. Keep it scoped to the transient process.

## Shell strict-mode pitfall

The analysis block runs under `set -euo pipefail`. Commands that are described as optional may still terminate the script when used as the first command in a pipeline, for example:

```bash
npm list -g --depth=0 2>/dev/null | awk 'NR>1{print}'
```

If an optional utility is absent or returns non-zero, guard the whole pipeline in the script with a conditional or `|| true`; do not rely solely on stderr redirection. A temporary wrapper can unblock an urgent run, but the durable correction belongs in `backup.sh`.

## Verification

Success requires all of the following:

1. Script exits `0` and prints `Push successful` plus `Daily backup finished successfully`.
2. `git -C /root rev-parse HEAD` equals `git -C /root rev-parse origin/main`.
3. Report the commit short SHA and timestamp in SGT.

Do not claim success from a local commit alone.