# Chris's VPS deploy workflow (working preferences)

## Repo mirror pattern

Chris's source repos live in `chrisvincodes/*` (his personal GitHub account).
For VPS deployment he wants me to mirror the source into `MadeAt2AM/<name>_VPS`
under the org, then use the existing webhook + deploy-script infrastructure
unchanged.

Practical sequence:
1. Clone `https://github.com/chrisvincodes/<repo>.git` locally
2. Clone `https://github.com/MadeAt2AM/<repo>_VPS.git` (org mirror)
3. `rsync -a --delete --exclude='.git' <local-source>/ <org-mirror>/`
4. In the org mirror: `git add -A && git commit ... && git push -f origin main`
5. The webhook on the org repo fires, pulls the v2 source, redeploys.

Why: webhook routes match on `repository.name` and the deploy script clones
the same name. Using a single canonical name (`<repo>_VPS` under MadeAt2AM)
means we never have to touch `/etc/webhook/hooks.json` again.

## Autonomous mode

When Chris says "i'll be offline for a while, complete it and report back":

1. **Make sensible defaults without re-asking** — replace vs side-by-side,
   validation thoroughness, port choices, brief sanity checks for ambiguous
   asks. Show the default in your report so he can override next time.
2. **Execute the full lifecycle end-to-end** — teardown → first-pull →
   migrate → seed → validate → webhook → live verify.
3. **Comprehensive validation** — exercise every API group, not just
   smoke-test the happy path. Aim for 0 FAIL on a 50-80 assertion suite.
4. **Brief mid-turn "standing by" notes** for long builds. He wants to see
   progress without re-querying.
5. **Full audit at the end** — PASS/FAIL counts, real findings flagged,
   housekeeping items listed (e.g. "test workplaces left in DB").

## Reporting style

- Technical depth is welcome. He accepts raw bash scripts, curl probes,
  JSON traces, fail/pass counts, lint warnings.
- Don't pad with pleasantries or apologetic hedging.
- If something failed, say so plainly and either fix it or flag it as a
  finding for him to decide on.
- Use Markdown tables for structured data (counts, status grids).
- Real findings at the end — things he should know about that aren't
  blocking. E.g. "custom-domain verify needs a PLATFORM_HOST env var".

## What NOT to do

- Don't ask permission for routine engineering decisions (port choices,
  default users, idempotent vs destructive teardown).
- Don't summarize the conversation at the end — he knows what he asked.
- Don't rerun `curl https://...` 5x in a row to "double-check" — one
  live verification is enough if it's the final state.
- Don't fabricate findings. If a route is 200, that's what to report.
  If a route is 502, that's what to report. Don't guess.

## Test user pattern (for any new app)

Chris usually wants a fixed roster of demo users with bcrypt-hashed
passwords:

```
platform@<app>.com   — platform_admin     (no company)
admin@demo.com        — admin              (Demo Co)
manager@demo.com      — manager            (Demo Co)
staff1@demo.com       — employee           (Demo Co)
staff2@demo.com       — employee           (Demo Co)
all using Test123!
```

Names for the demo users tend to be human short (Alex, Ronny, Alice, Jack).
He names them in advance; don't invent names.

## Repo paths Chris keeps

- Personal source: `chrisvincodes/<name>` — canonical source
- VPS deploy: `MadeAt2AM/<name>_VPS` — webhook target
- Local mirror: `/root/.hermes/projects/<name>/source/` (canonical source)
- Local VPS mirror: `/root/.hermes/projects/<name>/deploy-mirror/`
  (pushed up to MadeAt2AM to drive webhook)
- Deployed on VPS: `/srv/projects/<name>/`
- Secret env: `/srv/secrets/<name>.env` (chmod 600)
- Per-project seed script: `/srv/scripts/<name>_seed_demo_users.sh`