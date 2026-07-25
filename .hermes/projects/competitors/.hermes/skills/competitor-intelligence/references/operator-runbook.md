# Operator runbook — what to do when something goes wrong

This is the recovery flow for the competitor-intelligence pipeline. Each
section assumes the operator has read `IMPLEMENTATION_CHECKLIST.md` and
knows which phase is currently in progress.

## OpenCLI Browser Bridge is not connected

1. Open Chrome/Chromium on the dev VPS (via the VNC desktop or `ssh -X`).
2. Verify the OpenCLI Browser Bridge extension is enabled.
3. Re-run `python scrape.py --check-session` from the project root.
4. If the session is still unhealthy, the operator must log into the
   approved secondary Instagram account in that browser.

If Instagram presents a checkpoint, login challenge, or rate limit, halt
the pipeline and notify the operator. Do not bypass these protections.

## Whisper model fails to load

1. Confirm `faster_whisper` is installed in the Python environment:
   `python -c "import faster_whisper; print(faster_whisper.__version__)"`
2. Confirm the model cache directory exists and is writable.
3. Re-run `python scrape.py --check-whisper --whisper-model tiny`.
4. If the model is missing, run one download with the network enabled:
   `python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"`.
5. Re-run the offline check with the network disabled to confirm the
   inference is fully local.

## A reel returns an empty transcript

1. The reel is likely music-only. The pipeline still stages it.
2. The analysis playbook should score from the caption alone and mark
   `transcript_status: empty`.
3. The dashboard renders empty transcripts gracefully.

## A bundle fails validation

1. Open the failed bundle path.
2. Run `python scripts/validate_analysis.py <bundle.json>` to see the
   error.
3. Adjust the bundle (or the upstream analysis) and re-run the validator.
4. Until the validator passes, the bundle cannot be published.

## Publish script fails

1. Confirm the dev VPS is reachable: `ssh dev-vps hostname`.
2. Confirm the importer is implemented and the API container is running.
3. Re-run `bash scripts/publish_bundle.sh <bundle.json> --dry-run` to see
   the intended transfer.
4. Investigate the SSH error or the importer error before retrying.

## The dashboard is not responding

1. Confirm the API container is healthy: `ssh dev-vps docker ps`.
2. Confirm nginx is serving the right upstream:
   `ssh dev-vps nginx -T 2>/dev/null | grep competitors.terrybot.top`.
3. Confirm the DNS A record resolves to the dev VPS IP.
4. Verify the session cookie is set correctly and has not expired.

## Rolling back a deployment

1. List the previous image tags: `ssh dev-vps docker images`.
2. Edit the deploy helper to point at the previous tag.
3. Run `bash /srv/scripts/competitors_dev.sh deploy-prev`.
4. Reload, do not restart, shared nginx.
5. Re-run the health, auth, and dashboard smoke checks.

## Removing the operator account

The first-user account is created with `--once`. To remove it:

1. SSH to the dev VPS.
2. Connect to PostgreSQL: `docker exec -it competitors-db psql -U competitors`.
3. `DELETE FROM users WHERE username = 'your_username';`
4. Confirm the dashboard rejects the cleared credentials.

## What this runbook does NOT do

- It does not bypass Instagram account protections.
- It does not delete session files or cookies from the dev VPS.
- It does not expose cookies, session IDs, signed media URLs, or
  dashboard secrets in any output.
