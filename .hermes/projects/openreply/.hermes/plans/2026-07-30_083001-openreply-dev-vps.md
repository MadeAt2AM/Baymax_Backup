# OpenReply dev VPS deployment plan

Date: 2026-07-30 (SGT)
Target: https://openreply.terrybot.top
Source: https://github.com/diwenne/openreply.git
Deployment target: existing dev VPS at 147.79.18.32, behind shared Caddy

## Goal

Run OpenReply end to end on the dev VPS with the web/API process, always-on
BullMQ worker, PostgreSQL, and native-protocol Redis sharing the required
configuration. Make the app reachable at `openreply.terrybot.top`, then verify
health, authentication email configuration, Meta OAuth/webhook endpoints, queue
health, and a real worker round-trip before declaring the deployment usable.

This is a plan only. No VPS, DNS, repository, or application changes have been
made.

## What the repository documentation says

OpenReply is not a single web container. It has:

- Next.js 16 web app/API: dashboard, Auth.js magic-link flow, Instagram OAuth
  callback, incoming Meta webhook, health endpoint, legal pages, and cron routes.
- Long-running Node worker (`npm run worker`): BullMQ consumer, DM sending,
  polling reconciler, rate limiting, and worker heartbeat. It cannot be omitted
  or hosted as a short-lived serverless function.
- PostgreSQL: Prisma-managed application data and migrations.
- Redis over TCP: BullMQ queue and account rate limiter; HTTP-only Redis is not
  compatible.

The web and worker must use the same `DATABASE_URL`, `REDIS_URL`, and
`ENCRYPTION_KEY`. The encryption key must be exactly 64 hexadecimal characters.
The documented reference deployment uses Vercel/Railway, but this procedure
will adapt it to the existing Docker/Caddy dev-VPS pattern: one project stack,
private database network with MTU 1400, shared external `web` network, and a
project-specific deploy helper.

## Assumptions to confirm before implementation

1. `openreply.terrybot.top` should be the primary public URL, with DNS managed
   through the existing Cloudflare setup.
2. We should deploy the upstream repository directly or mirror it into the
   MadeAt2AM GitHub organisation using the normal `<name>_VPS` workflow. The
   preferred pattern is a mirror, but the destination repository name and
   visibility still need confirmation before any GitHub write.
3. A PostgreSQL database and Redis may be provisioned as containers in the
   OpenReply stack on the dev VPS, rather than using external Railway/Neon/
   Redis Cloud services. This keeps the procedure consistent with the host and
   avoids inventing credentials or external accounts.
4. The operator will provide or confirm all secrets before provisioning:
   `NEXTAUTH_SECRET`, `CRON_SECRET`, `ENCRYPTION_KEY`, `DATABASE_URL` strategy,
   `REDIS_URL` strategy, `RESEND_API_KEY`, `EMAIL_FROM`, Meta Graph version,
   Instagram App ID/secret, Facebook App secret, and webhook verify token.
5. The first milestone is a single-account/self-hosted instance. Public
   multi-customer use would additionally require Meta App Review, Advanced
   Access, business verification, privacy/terms/data-deletion readiness, and
   separate product decisions.

## Procedure

### Phase 0 — operator confirmation and read-only preflight

- Confirm the assumptions above and the desired initial Meta account scope.
- Confirm the DNS/Cloudflare authority for `terrybot.top` and whether the
  hostname already has an A/CNAME record.
- Inspect the dev VPS read-only: Docker/Compose versions, free disk/RAM,
  existing Caddy site imports, shared `web` network, project-name collision,
  webhook receiver configuration, and occupied ports.
- Inspect the repository read-only: build/runtime requirements, migration
  history, `vercel.json` cron schedule, environment validation, worker health
  implementation, and CI status.
- Establish success criteria: clean image build, migrations applied, all
  required containers healthy, HTTPS root and `/api/health` available, health
  reports database/Redis/worker healthy, magic-link request succeeds, and
  Meta verification/OAuth callback routes respond correctly.

### Phase 1 — deployment topology and source preparation

- Create the project directory under `/srv/projects/openreply/` and secrets
  file `/srv/secrets/openreply.env` only after values are supplied.
- Prepare the source deployment configuration in a clean project worktree.
- Add a VPS-specific compose topology with:
  - `postgres` on a private network only;
  - `redis` on the private network only;
  - `web` on private + external `web` network;
  - `worker` on the private network (and only attach to `web` if needed);
  - explicit private-network MTU 1400;
  - persistent Postgres/Redis volumes;
  - service healthchecks and restart policies;
  - build/start commands matching the repo (`prisma generate`, Next build/start,
    and `npm run worker`).
- Decide whether to use a production Node image and a multi-stage Dockerfile.
  If creating one, include the required Prisma generation/build dependencies
  and a minimal runtime image; do not use Vercel-only assumptions.
- Ensure `.env` remains gitignored and no supplied secrets enter git history.
- Add or adapt the project deploy helper, Caddy site block, and webhook hook
  using the existing host conventions. Do not alter shared Caddy or unrelated
  project helpers.

### Phase 2 — DNS, secrets, and first deployment

- Create/verify the Cloudflare DNS record for `openreply.terrybot.top` pointing
  at the dev VPS, using the existing DNS utility and explicit operator approval
  for the write.
- Materialize the complete environment on the VPS. Generate random secrets
  only where the operator authorizes us to generate them; request external
  provider credentials rather than guessing.
- Configure `NEXTAUTH_URL=https://openreply.terrybot.top` consistently for web
  and worker. Use one shared encryption key and compatible internal service
  URLs. Keep database/Redis credentials out of compose source.
- First-pull/build the stack, then explicitly run the Prisma migration service
  or equivalent migration command. Rebuild the migration image if its source
  is cached. Confirm migration completion from actual command output.
- Install the project-specific webhook helper on the VPS separately from the
  source-controlled copy, because the host helper is not automatically synced.
- Add the GitHub webhook route only after repository topology, webhook secret,
  and target branch are confirmed.

### Phase 3 — application/provider configuration

- Configure Resend sender and verify the login magic-link path. `EMAIL_FROM`
  must be a verified sender; do not test with the placeholder.
- Create/configure the Meta Business app using the repository's documented
  Instagram Login flow, not Facebook Login or Marketing API.
- Add the Instagram Business/Creator account as a tester and accept the invite
  in Instagram.
- Register exactly:
  `https://openreply.terrybot.top/api/instagram/callback`
- Configure the Meta webhook:
  callback `https://openreply.terrybot.top/api/webhook`, the exact verify
  token, and the `comments` subscription.
- Keep the app in development until the self-hosted test succeeds. Publishing
  and App Review are a separate decision; real webhooks require Live state.

### Phase 4 — verification and end-to-end test

- Probe HTTPS root and `/api/health` with retries for certificate issuance.
- Confirm security headers, no unexpected redirects, static asset loading, and
  Caddy upstream resolution.
- Confirm `/api/health` reports database OK, Redis/queue OK, and
  `worker.healthy: true` after the heartbeat interval.
- Request a magic link and verify delivery through the configured email inbox.
- Exercise Meta webhook GET verification with the supplied token and validate
  POST signature handling using a Meta test event.
- Connect the tester Instagram account through Settings and confirm the OAuth
  callback stores the professional `user_id` (not the app-scoped `id`).
- Create a test campaign with a distinctive keyword. Comment from a different
  Instagram account, then verify the webhook event, queue/worker processing,
  and `SENT` DM log plus the received DM. The app intentionally ignores its own
  comments.
- Test worker restart/recovery and confirm the heartbeat becomes healthy again.
- Test the daily cron endpoint with the correct `CRON_SECRET`; do not wait for
  a production schedule to prove it.
- Push a harmless no-op commit to verify GitHub webhook redeploy, watching the
  VPS webhook log and deploy marker. Treat a GitHub 504 as inconclusive until
  the live app behavior/build marker changes.
- Confirm neighbouring applications still return 200 and their Caddy routes,
  networks, and containers are unaffected.

### Phase 5 — handover and operations

- Record the final topology, service names, persistent volume names, secret
  source-of-truth path, deploy helper path, webhook ID, Caddy site path, and
  rollback procedure in project documentation.
- Add a project-local validation script/playbook entry if the deployment needs
  repeatable checks; keep it read-only by default.
- Document Meta development-mode limitations and the App Review prerequisites
  before anyone invites external users.
- Provide the operator with live URLs, health output, test evidence, known
  limitations, and exact commands for logs/status/rollback.

## Files likely to change in the project

These are candidate paths, to be confirmed after the implementation preflight:

- `docker-compose.yml` or a new production compose file
- `Dockerfile` and/or `deploy/docker/*` if multi-stage images are needed
- `.env.example` (names and safe placeholders only)
- `docs/setup.md` and/or a new VPS deployment document
- `deploy/openreply_dev.sh`
- `scripts/validate_app.sh` or project-local validation scripts
- `vercel.json` only if the VPS cron mechanism requires an equivalent route
  adjustment; avoid unrelated hosted-platform changes
- Prisma configuration/migrations only if the clean migration run exposes an
  actual repository issue; do not change schema speculatively

Host-side files (not committed to the application repository):

- `/srv/secrets/openreply.env`
- `/srv/projects/openreply/`
- `/srv/scripts/openreply_dev.sh`
- `/srv/caddy/sites/openreply.caddy`
- `/etc/webhook/hooks.json` entry for the selected repository
- Cloudflare DNS record for `openreply.terrybot.top`

## Risks and tradeoffs

- The upstream guide assumes Vercel + Railway; adapting to the dev VPS creates
  responsibility for backups, upgrades, resource limits, and worker supervision.
- Meta setup is an external dependency and may block the end-to-end test even
  when the deployment is healthy.
- Magic-link login cannot be validated without a real Resend key and verified
  sender.
- Instagram tokens are encrypted at rest; losing or changing
  `ENCRYPTION_KEY` requires reconnecting accounts.
- Public multi-tenant operation is not equivalent to a private self-hosted
  instance and should not be claimed without Meta review/verification.
- Redis must support blocking TCP commands; an HTTP-compatible Redis endpoint
  is not sufficient.
- All disruptive actions (container recreation, Caddy reload if it affects
  active routes, webhook changes, DNS changes, and any database write) will be
  explicitly confirmed before execution.

## Open questions before implementation

- Direct upstream deployment or MadeAt2AM mirror repository, and what exact
  destination repository name/visibility should be used?
- Containerized Postgres/Redis on the dev VPS or operator-supplied external
  managed services?
- Should the first milestone support only Chris's Instagram account, or are
  other testers/users required immediately?
- Which Resend sender address/domain should be used?
- Are the Meta app and Instagram Business/Creator tester account already ready?
- Should we generate the random app secrets on the host, or will the operator
  supply pre-generated values?
- Is Cloudflare DNS currently proxied, and should it remain proxied?
- What backup/retention level is required for the new Postgres volume?

## Rollback

Before any write, capture the current Caddy config, webhook config, DNS record,
compose state, and relevant Docker image/container IDs. On a failed deployment,
stop/remove only the OpenReply stack, remove its Caddy site and webhook entry,
restore the captured host configuration, and leave neighbouring projects alone.
Do not delete persistent data or volumes without explicit destructive-action
confirmation.
