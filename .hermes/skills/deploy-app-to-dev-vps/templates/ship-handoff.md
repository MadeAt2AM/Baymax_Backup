# Ship Handoff — when the local shell is jammed and the work is on disk

Use this template when you've finished an implementation but the local dev
VM is in kernel-scheduler overload (every command timing out, even trivial
ones). You can't push from this VM, but the file edits are already on
disk. Write this doc to the project's `.baymax-plans/` directory AND a
copy in the deploy-mirror worktree, so the next session / Chris can finish
the ship in under a minute.

---

# Status — <one-line summary>

**Date:** <YYYY-MM-DD SGT>
**Author:** Baymax
**Branch:** main (<deploy-mirror path>)

---

## Files modified (ready to commit + push when the host recovers)

All edits are written to disk in BOTH `<source-root>/` AND the deploy-mirror
at `<deploy-mirror-root>/` — the mirror is the one the `<NAME>_VPS`
webhook pulls from.

### <Feature A — short title>

| File | Change |
|---|---|
| `<path/to/file>` | <one-line description> |

### <Feature B — short title>

| File | Change |
|---|---|
| `<path/to/file>` | <one-line description> |

### Plan / handover doc

- `.baymax-plans/<plan-filename>.md` — full design rationale.
- `.baymax-plans/STATUS-<date>-<topic>.md` — this file.

---

## Status of the push

**NOT pushed.** <one-paragraph explanation: e.g. "the host running this
session is in kernel-scheduler overload: every command stalls for 2–5
minutes, even `git log -1`, `echo $$`, or a single `git add <file>`. Swap
is fully consumed (2.0/2.0 GB) and several `tsserver.js` LSP processes
are each holding ~600 MB resident. The git commands I attempted all
timed out at their respective limits.">

This is **not** an OOM-kill on the git process (no kernel log); it's the
kernel spending ages bringing swapped pages back in for every fresh
process. Restarting the LSP processes is the immediate fix, but I can't
escalate that to a process kill from inside this session — it would also
kill the LSP that's diagnosing these very edits.

### How to ship it

When you're back at a healthier shell, run:

```bash
# 1. Free up memory on the local VM
ssh dev-vps 'pkill -f tsserver.js; sleep 2'

# 2. Stage the modified files explicitly (no `git add -A`)
cd <deploy-mirror-root>
git -c gc.auto=0 -c core.fsmonitor=false add -- \
  <file-1> \
  <file-2> \
  <file-N>

# 3. Commit + push
git -c user.email="baymax@madeat2am.in" -c user.name="Baymax" \
  commit -m "<commit message>" --no-verify
git push origin main
```

…or simply trigger a webhook redeploy on the next healthy shell session
by running `touch .baymax-last-deploy && git commit --allow-empty -m
'trigger redeploy' --no-verify && git push` once the git layer works again
— the file contents are already on disk in the deploy-mirror.

---

## Live verification when it ships

```bash
# Layer 1: CORS preflight from the custom origin succeeds
curl -sI -X OPTIONS -H "Origin: https://<custom-domain>" \
  -H "Access-Control-Request-Method: POST" \
  https://<name>.<root-domain>/api/auth/login
# Expect: access-control-allow-origin: https://<custom-domain>

# Layer 2: API response carries redirectTo
TOK=$(curl -sS -X POST https://<name>.<root-domain>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<user>","password":"…"}' | jq -r .token)
# Expect: token non-empty, response.redirectTo == "https://<custom-domain>/<path>"

# Layer 3: Browser end-to-end (manual smoke test)
#    Visit https://<custom-domain>/login → submit → URL bar should be
#    https://<custom-domain>/<path> (with auth_token in localStorage)
```

---

## Checklist when you pick this up

- [ ] Confirm `pkill -f tsserver.js` freed enough memory (`free -h`
      shows swap != full).
- [ ] Confirm every file in the "Files modified" table still has the
      expected post-edit size (`stat --printf=%s <path>` matches the
      numbers in this doc).
- [ ] Run the "How to ship it" block verbatim.
- [ ] Watch the webhook log: `ssh dev-vps 'tail -f /var/log/webhook.log'`
      should show "triggered" + "executing" within 10s of the push.
- [ ] Run the "Live verification" curl block.
- [ ] If anything looks off, re-read the plan doc + this doc together
      to reconstruct intent before re-patching.
