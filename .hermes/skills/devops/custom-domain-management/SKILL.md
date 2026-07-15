---
name: custom-domain-management
title: Custom Domain Management
description: Automated Caddy site generation and webhook integration for white-label tenant domains
type: devops
tags: ["custom-domain","white-label","automation","caddy","db-sync"]
related_skills: ["deploy-app-to-dev-vps","collector-skills","autonomous-ai-agents"]
---

## Overview

SYNTRA supports per-tenant custom domains (e.g., `login.acme.com`) that map to their own branding and login flow while still routing through the central platform.

## Workflow

1. **Create tenant** in platform admin UI → `PUT /api/platform/companies/:id`
2. Set `custom_domain` and run `POST /api/platform/companies/:id/domain/verify`
   * DNS resolver checks `REPLIT_DOMAINS` env var
3. When `domain_status` becomes `verified`, DB records it
4. Auto-sync script runs (`custom-domain-sync.sh`) and:
   * Queries verified domains
   * Generates `/srv/caddy/sites/syntra.auto.caddy` with one `syntra.<domain>` block per domain
   * Diff-checks against existing fragment → only reloads Caddy if changed
5. Tenant's login flow redirects to their domain after auth
6. Branding appears via `useBranding()` on all public pages

## Integration Points

- **Database schema** (`companies.domain_status`, `custom_domain`)
- **Caddy** (`/srv/caddy/sites/syntra.auto.caddy`) – idempotently reloaded on change
- **Automation script** – `/srv/scripts/custom-domain-sync.sh` – called by root's crontab every 5 min
- **Caddyfile** must contain `import /etc/caddy/sites/*.caddy` (already present)

## Steps for a New Tenant

```bash
# 1. Insert company record (via UI or API) – set custom_domain
# 2. Send POST /api/platform/companies/:id/domain/verify
# 3. Verify DNS CNAME (login.acme.com -> syntra.terrybot.top)
# 4. Wait for script to pick it up (or run manually: /srv/scripts/custom-domain-sync.sh)
# 5. Tenant can now log in via their domain – branding appears automatically
```

## Script Details (/srv/scripts/custom-domain-sync.sh)

- Pulls `POSTGRES_PASSWORD` from `/srv/secrets/syntra.env`
- Queries: `SELECT custom_domain FROM companies WHERE domain_status='verified' AND status='active' AND custom_domain IS NOT NULL ORDER BY custom_domain;`
  - **The `status='active'` filter is critical.** It auto-removes soft-deleted tenants (`status='inactive'`) from Caddy on the next cron tick — no manual cleanup needed when a platform admin removes a company via `DELETE /api/platform/companies/:id`.
- Writes `/srv/caddy/sites/syntra.auto.caddy` with blocks
- Uses `docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile` only when file changes

## Tenant Deletion → Caddy Auto-Cleanup

When a platform admin deletes a company (soft delete flips `status='inactive'`):
1. The row is not physically removed
2. `custom_domain` and `domain_status='verified'` remain in the row
3. **Without the `status='active'` filter**, the deleted tenant would still be reverse-proxied by Caddy (broken: hits the app but no DB record matches)
4. **With the filter**, the next `*/5 * * * *` cron tick drops the host block from `syntra.auto.caddy` and reloads Caddy

If you need an immediate purge (without waiting for cron): `sudo /srv/scripts/custom-domain-sync.sh`.

## Reference Docs

- `docs/CUSTOM_DOMAIN_SETUP.md` – full end-to-end walkthrough
- `docs/INFRASTRUCTURE.md` – VPS-level configuration (MTU, DNS, secrets)
- `scripts/custom-domain-sync.sh` – the automation script itself
- `skills/deploy-app-to-dev-vps/SKILL.md` – base deployment playbook for all apps
- `skills/caddy-service-dns-aliases/SKILL.md` – Caddy binding and MTU fix details

## Gotchas & Troubleshooting

| Symptom | Root Cause | Fix |
|---|---|---|
| `domain_status` stuck on `pending` | DNS not propagated | Wait, then re-verify |
| Tenant soft-deleted but their domain still serves | Auto-sync query missing `status='active'` filter | Update query (see above); manual flush via `sudo /srv/scripts/custom-domain-sync.sh` |
| `Caddy reload` fails | Invalid syntax in generated fragment | Run script manually in debug mode |
| `ERR_CERTIFICATE_AUTHORITY_INVALID` on first hit | LE cert issuance delay | Retry – resolves in <30s |
| Custom branding doesn't appear | `useBranding()` not called on new public page | Add `useBranding()` to that page |
| 502 after redeploy | Migrate container not yet built | `docker compose build migrate && docker compose up -d` |

## Pre-Flight: Confirm Where You're Working

**Before debugging or modifying any of this stack, identify the actual host.** With multiple VPSes and local containers, it's easy to:
- Diagnose Payntra while thinking you're in SYNTRA (or vice versa)
- Edit files in `/root/.hermes/projects/` that never reach a running container

Always run before proposing changes:

```bash
ssh dev-vps 'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep -i syntra'
```

Only proceed once you've confirmed the target containers are on the host you can actually `docker exec` and `psql` against.

## Live Verification Recipe (Invitation Flow)

When verifying tenant UI works end-to-end, prefer this loop over reading screenshots:

1. **Confirm the company's row** in the DB:
   ```bash
   ssh dev-vps 'docker exec syntra_postgres psql -U syntra -d syntra -c \
     "SELECT id, name, custom_domain, domain_status, status FROM companies WHERE name ILIKE '\''%cyberslide%'\'';"'
   ```
   Expect `domain_status='verified'` and `status='active'`.

2. **Create a real invitation** via the API (don't pollute /email/DB by hand):
   ```bash
   ssh dev-vps 'TOK=$(curl -sS -X POST https://syntra.terrybot.top/api/auth/login \
     -H "Content-Type: application/json" \
     -d "{\"email\":\"admin@demo.com\",\"password\":\"Test123!\"}" \
     | python3 -c "import sys,json; print(json.load(sys.stdin)[\"token\"])") && \
     curl -sS -X POST https://syntra.terrybot.top/api/invitations/ \
     -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
     -d "{\"email\":\"chris-test@example.com\",\"role\":\"manager\"}"'
   ```
   Returns `{id, token, …}`.

3. **Drive the browser** to the returned URL:
   ```
   browser_navigate(url="https://syntra.terrybot.top/accept-invite?token=…&email=…")
   ```

4. **Confirm visually** with `browser_vision(question="Is the Set Up Your Account form rendered with email shown, name and password fields, and submit button?")`. A blank page = JS bundle error, not an invitation logic bug. Branch from there.

5. **Submit the form** (optional, only if verifying acceptance): fill name + password, click submit, confirm redirect to `/dashboard`.

This recipe catches: blank pages, missing route, JS bundle errors, email/token mismatch, expired tokens, and accept-flow failures — without needing email infrastructure.

## References

- `docs/CUSTOM_DOMAIN_SETUP.md`
- `docs/INFRASTRUCTURE.md`
- `scripts/custom-domain-sync.sh`
- `skills/deploy-app-to-dev-vps/SKILL.md`
- `skills/caddy-service-dns-aliases/SKILL.md`

*This skill supersedes the previous ad-hoc instructions for manual Caddy block edits and provides a repeatable, test-covered automation flow.*