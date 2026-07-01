# Cloudflare DNS utility — behavior notes

Notes from real use during the July 2026 deploy bootstrap. The full script lives at `templates/cf-dns.sh` (also installed at `~/.hermes/bin/cf-dns.sh`).

## Reading the env

Source order:
1. `$HERMES_HOME/.env` if `HERMES_HOME` is set
2. `$HOME/.hermes/.env` (default)

Required variables:
- `CF_API_TOKEN` — must have `Zone:DNS:Edit` permission on the target zone
- `CF_ZONE_ID` — find via `GET /zones?name=<domain>` against Cloudflare v4 API
- `CF_DOMAIN` — full apex domain, e.g. `terrybot.top`
- `CF_DEFAULT_IP` (optional) — fallback A record content (defaults to `127.0.0.1` so it's obvious if you forgot to set it)

## `add` is idempotent

We hit a real case mid-session: second invocation of `cf-dns.sh add` correctly reported the existing record instead of failing with "record already exists" 409. Tested:

```bash
cf-dns.sh add smoketest                 # created
OK: created smoketest.terrybot.top → 147.79.18.32
cf-dns.sh add smoketest                 # idempotent
EXISTS: smoketest.terrybot.top already has record id 75d0... → 147.79.18.32
```

That makes `deploy.sh` re-runnable without cleanup between attempts.

## `proxied: false` is policy-locked

The user asked for **DNS-only** (grey-cloud) for everything on `terrybot.top`. Existing DNS records were all `proxied=false`. The script hardcodes `proxied: false` in the create payload. If you ever need orange-cloud proxy for a specific record, manually edit the JSON body — do **not** add a `--proxied` flag to the script without checking with the user first.

## TTL is 60 (not auto)

We explicitly set `ttl: 60` (1 minute) for fast iteration. Production deployments may want TTL 300 (5 min) or 3600 (1 hour) for cheaper DNS lookups. The current value is dialed for development churn.

## Rate limits

Cloudflare v4 API rate limits:
- 1,200 requests per 5 minutes per user
- 100,000 requests per day per user

Our deploy/teardown cycle does 1-2 API calls. No realistic chance of hitting limits even with dozens of deploys per hour.

## Cloudflare MCP vs the script

`https://mcp.cloudflare.com/mcp` is the official MCP endpoint but requires OAuth in browser. We tried:

```
GET https://mcp.cloudflare.com/mcp         → 403 error code 1010 (Cloudflare block on bot-like User-Agent from datacenter IP)
POST same with initialize JSON-RPC payload → 401 Bearer realm="OAuth"
```

Two failure modes. Both require interactive browser context to fix. **Skip the MCP for now** — the script covers everything. If we ever need the MCP, the OAuth flow needs to happen in a browser the user controls, with the resulting access token pasted into `~/.hermes/.env` as `CF_MCP_TOKEN`.

## Existing records to preserve

When this skill was written, the zone had these records the user wanted to keep:

| Name | IP | Purpose |
|---|---|---|
| `cyberslide.terrybot.top` | 147.79.18.59 | THIS VPS — Hermes dashboard |
| `dashboard.terrybot.top` | 147.79.18.59 | Hermes dashboard |
| `obsidian.terrybot.top` | 147.79.18.59 | Obsidian vault |
| `space.terrybot.top` | 147.79.18.59 | Unknown |
| `agent.terrybot.top` | 147.79.18.32 | Dev VPS root |
| `workspace.terrybot.top` | 147.79.18.32 | Dev VPS workspace |

None of these are touched by `deploy.sh` or `teardown.sh` — both operate exclusively on the `<name>` argument plus domain, never on existing records.

## Future hardening suggestions

If `cf-dns.sh` becomes a heavily-used utility:

1. **Support CNAME records** — useful if a target service is on a separate host
2. **Bulk operations** — `cf-dns.sh sync <list.txt>` to sync a desired state
3. **State file at `~/.hermes/state/cf-dns.json`** — track which records we own, so `teardown.sh` can be smarter about cleanup
4. **Alias for common verbs** — `cf-dns.sh rm` as alias for `del`, `cf-dns.sh ls` for `list`

For now the surface is small enough that none of these are necessary.