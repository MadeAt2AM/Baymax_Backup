# GitHub Webhook → Dev-VPS Auto-Deploy Pipeline — Reference

Companion to the umbrella skill `vps-container-deploy`. Read this when debugging
the `git push → webhook → redeploy → live URL` chain.

## Architecture in one diagram

```
┌───────────────────────────────────────────────────────────┐
│ CONTROL VPS (cyberslide)                                   │
│   /root/projects/<name>/     ← you edit here              │
│   project.sh push            ← stages + commits + pushes  │
└───────────────────────────────────────────────────────────┘
                          │ git push
                          ▼
┌───────────────────────────────────────────────────────────┐
│ GitHub                                                      │
│   MadeAt2AM/<name>                                          │
│   webhook fires on push → POST :9000/hooks/github-push     │
└───────────────────────────────────────────────────────────┘
                          │ HTTPS + HMAC
                          ▼
┌───────────────────────────────────────────────────────────┐
│ DEV VPS (147.79.18.32)                                      │
│   :9000  adnanh/webhook daemon                             │
│     /etc/webhook/hooks.json                                │
│     ↓ verifies X-Hub-Signature-256                        │
│     ↓                                                       │
│   /srv/scripts/project_dev.sh redeploy <name>             │
│     ↓                                                       │
│   git fetch --depth=1 origin main                         │
│   git reset --hard origin/main                            │
│   docker compose up -d --build                            │
│   writes /srv/caddy/sites/<name>.caddy                    │
│   docker exec caddy caddy reload                          │
│   curl healthcheck                                        │
└───────────────────────────────────────────────────────────┘
```

## Per-end diagnostics — 4 places to look

When "I pushed but nothing changed on the URL", check these in order:

| # | Where | What you're looking for | Typical signal |
|---|---|---|---|
| 1 | Control: `git log --oneline -3` in `/root/projects/<name>/` | Was a new commit made and pushed? | HEAD == origin/main |
| 2 | GitHub: `GET /repos/<org>/<repo>/hooks/<id>/deliveries` | Did GitHub actually fire the webhook? | `status_code: 200`, duration_ms > 0 |
| 3 | Dev VPS: `sudo -n tail -30 /var/log/webhook.log` | Did the daemon accept it and run the script? | `hook triggered successfully` then `command output: ...` |
| 4 | Dev VPS: `docker ps`, `cat /srv/projects/<name>/.baymax-last-deploy`, `curl https://<name>.<domain>/` | Did the container rebuild and Caddy serve it? | Last-deploy recent + HTTP 200 + new content in body |

Skip step 1 if you trust `project.sh push` (it always confirms push).

## When step 2 (GitHub-side) is the answer: silent push drops

If steps 1, 3, 4 all show "no change" but you definitely ran `git push` recently, the push may have been **silently dropped by GitHub** before the webhook fired. Observed behavior (Payntra Phase 7.7, 2026-07-04): pushed a 3-line dark-mode fix 90s after the previous push. Local `git log` showed the new commit; `git log` on dev VPS still showed the prior commit; `curl https://api.github.com/repos/MadeAt2AM/payntra/commits/main` still returned the prior SHA. No webhook delivery in GitHub's deliveries list either. The push transport returned 0 (no error visible), but the commit was never persisted server-side.

**Why it happens:** appears to be GitHub-side dedup or rate limiting of pushes to the same ref within a short window. No error surfaced to the git client.

**Fix:** re-push:

```bash
git push origin main   # usually succeeds the second time, webhook fires within 10s
```

**Defensive habit:** after every push, wait ~30s and verify the remote advanced:

```bash
curl -s https://api.github.com/repos/<org>/<repo>/commits/main | jq -r '.sha[:12]'
```

If that SHA doesn't match your local `git log -1` SHA, the push was lost — re-push. Avoid double-pushing fixes within seconds of each other (e.g. amend + push, then quick follow-up fix + push); space them out or accept you'll need to re-push.

This is GitHub-side, not the webhook daemon. The `webhook.log` on dev VPS will show **nothing** for a dropped push — that's the diagnostic signal.

## Manual signed POST for fast iteration

Use this when you want to test the dev-VPS webhook logic without going
through GitHub on every cycle (1–3s saved per round trip):

```bash
# on cyberslide
SECRET=$(cat /root/.hermes/.dev-vps-webhook.secret)
NAME=my-cool-app
PAYLOAD=$(cat <<EOF
{"ref":"refs/heads/main","repository":{"name":"$NAME"}}
EOF
)
SIG="sha256=$(printf '%s' "$PAYLOAD" \
  | openssl dgst -sha256 -hmac "$SECRET" -hex \
  | awk '{print $NF}')"

curl -sS -X POST "http://147.79.18.32:9000/hooks/github-push" \
  -H "X-Hub-Signature-256: $SIG" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"

# immediately on dev-vps:
sudo -n tail -15 /var/log/webhook.log
```

What to expect if it works:

```
[webhook] YYYY/MM/DD HH:MM:SS [xxxxxx] github-push got matched
[webhook] YYYY/MM/DD HH:MM:SS [xxxxxx] github-push hook triggered successfully
[webhook] YYYY/MM/DD HH:MM:SS [xxxxxx] executing /srv/scripts/project_dev.sh ...
[webhook] YYYY/MM/DD HH:MM:SS [xxxxxx] command output:   → git fetch + reset to origin/main
...
[webhook] YYYY/MM/DD HH:MM:SS [xxxxxx]   ✓ deploy complete
[webhook] YYYY/MM/DD HH:MM:SS [xxxxxx] 200 | 1.3 KiB | 5.85s | 147.79.18.32:9000 | POST /hooks/github-push
```

## Token-rotation playbook

The chain needs two GitHub tokens that can `git fetch` from `MadeAt2AM/<repo>`:

| Location | File | Owner | When written |
|---|---|---|---|
| Control VPS | `GITHUB_TOKEN` in `/root/.hermes/.env` | root | manual, used by `project.sh` |
| Dev VPS | `/srv/scripts/.gh-token` | deploy (0600) | first SSH-in from `project.sh new` |

If you rotate the control VPS token:

```bash
# on cyberslide
sed -i "s|^GITHUB_TOKEN=.*|GITHUB_TOKEN=$(gh auth token || new-value)|" /root/.hermes/.env

# propagate to dev VPS (deploy needs the new value to git-fetch)
scp /dev/stdin deploy@147.79.18.32:/tmp/.gh-token.new <<< "NEW_VALUE"
ssh -i ~/.ssh/baymax_dev_vps deploy@147.79.18.32 \
  'sudo -n mv /tmp/.gh-token.new /srv/scripts/.gh-token && \
   sudo -n chown deploy:deploy /srv/scripts/.gh-token && \
   sudo -n chmod 600 /srv/scripts/.gh-token'
```

If you rotate the GitHub-side token (the one GitHub uses to authenticate
*the webhook itself* — that's actually the hook's `secret`, not a token),
you have to update `/etc/webhook/hooks.json` and re-POST the same secret
to GitHub's `/repos/.../hooks` config endpoint.

## GitHub-side hook permission errors

403 responses on `POST /repos/<org>/<repo>/hooks`:

| Error message | Cause | Fix |
|---|---|---|
| `Resource not accessible by personal access token` | fine-grained PAT has no `webhooks:write` on the org | https://github.com/settings/tokens → edit → add `Webhooks: Read and write` |
| `Not Found` | path `/repos/<org>/<repo>/hooks` is wrong (case-sensitive org/repo) | re-fetch repo list, double-check spelling |
| `Bad credentials` | token expired or revoked | regenerate PAT, update `/root/.hermes/.env` |
| 422 with `Validation Failed` | hook payload has bad URL or unknown event | see webhook.config schema in GitHub docs |

## What "live" actually means

- Caddy reads the per-site block from `/srv/caddy/sites/<name>.caddy`.
- That file is regenerated on every redeploy.
- `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`
  triggers config pickup; certs don't re-issue unless the domain changes.
- Caddy's `/etc/caddy/data` and `/etc/caddy/config` are persistent volumes
  mounted from `/srv/caddy/data` and `/srv/caddy/config`, so cert state
  survives caddy container restarts.

## Verified end-to-end session (2026-07-03, baymax-pipeline-probe)

| Stage | Time |
|---|---|
| `project.sh push "feat: change greeting..."` (control) | T0 |
| `git push` to GitHub | T0 + ~1s |
| GitHub fires webhook | T0 + ~1–2s |
| webhook daemon verifies sig + invokes `project_dev.sh redeploy` | T0 + ~2–3s |
| script runs `git fetch`, `git reset`, `docker compose up --build`, `caddy reload` | T0 + ~3–10s |
| New container serving, Caddy proxying, live URL returns HTTP 200 with new body | T0 + ~15s |

Total wall time observed: **5.85s** for a no-op rebuild (image cached).

Round-trip from "push to user sees new content": under 20s in all observed runs.

## Common confusions that aren't bugs

- "Hook delivery shows 500 but URL didn't change" — different failure (see step 3 diagnostics above). 500 from webhook daemon = script exited non-zero, container may still be old. Check `docker logs <name>-app`.
- "Push succeeded, webhook fired, URL returns 502" — usually an *app* failure (Python syntax error, missing env var, port mismatch). NOT a webhook problem. Check `docker logs <name>-app`.
- "Container recreating every push" — that *is* the happy path. `docker compose up -d --build` always recreates if the image or config changed. It's idempotent on no changes.
