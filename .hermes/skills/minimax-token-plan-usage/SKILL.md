---
name: minimax-token-plan-usage
description: Check live MiniMax Token Plan quota usage (5-hour + weekly window) for the Starter ¥29 grandfathered tier using the official /v1/token_plan/remains endpoint.
trigger: User asks about M3 / MiniMax-M3 usage, quota, "how much M3 left", "starter plan", "token plan remaining", or wants to check Token Plan burn-down.
---

# MiniMax Token Plan — Live Usage Check

## What this does
Fires the official subscription quota endpoint for the user's Token Plan key (Starter ¥29, grandfathered) and returns a clean usage report: 5-hour rolling window + weekly window, plus reset times.

## Stored credentials
- **MINIMAX_TOKEN_PLAN_KEY** — credential pool entry in `/root/.hermes/auth.json`, source = `file:/root/.hermes/.credentials/minimax_token_plan.json` (mode 0600)
- Plain text in the credentials file (Hermes credential-pool native pattern, matches existing MINIMAX_API_KEY convention)
- The `auth.json` entry only stores a `sha256:...` fingerprint, never the secret itself
- DO NOT log, print, or echo the raw key value in any output to the user. Use it via header only.

## Endpoint
- **URL:** `https://api.minimax.io/v1/token_plan/remains` (NOT `www.minimaxi.com` — that endpoint rejects this key type with status 2049 "invalid api key"; the `.io` host returns status 0 success)
- **Method:** GET (curl `--location`)
- **Headers:** `Authorization: Bearer <key>`, `Content-Type: application/json`

## Reusable shell snippet
```bash
curl -s --location 'https://api.minimax.io/v1/token_plan/remains' \
  -H "Authorization: Bearer $(jq -r .api_key /root/.hermes/.credentials/minimax_token_plan.json)" \
  -H 'Content-Type: application/json'
```

## Response shape (parsed)
Each entry in `model_remains[]`:
- `model_name`: `"general"` (text + multimodal) or `"video"`
- `current_interval_status`: `1`=active, `3`=not_active (not entitled)
- `current_interval_remaining_percent`: 0-100 — % of 5h window left
- `current_weekly_remaining_percent`: 0-100 — % of weekly window left
- `remains_time` (ms): time until 5h reset
- `weekly_remains_time` (ms): time until weekly reset
- `start_time` / `end_time` (ms epoch): 5h window bounds
- `weekly_start_time` / `weekly_end_time` (ms epoch): weekly window bounds
- `current_interval_usage_count` / `current_interval_total_count`: only populated when usage exists; often 0/0 on a fresh window

## Output format
Render as a table:
| Window | Used | Left | Resets in | Window (UTC) | Window (SGT) |
Always present both UTC AND SGT (Asia/Singapore) — operator is in Singapore.

## Pitfalls
1. **Wrong host**: `www.minimaxi.com` returns `2049 invalid api key` for this Token Plan key. Use `api.minimax.io` — that's where Token Plan endpoints live for international keys.
2. **Don't use the `MINIMAX_API_KEY`** in `.env` (the `sk-cp-...` Coding Plan key) for this endpoint — different key type, different entitlements. Always use the Token Plan key from the credential pool.
3. **The response is mostly usage-driven**: `current_interval_total_count` is often 0/0 because the API doesn't expose the raw cap — it only returns the percentage. To find the absolute token cap, the user has to read it from the console (`platform.minimaxi.com/console/usage`).
4. **Starter tier is grandfathered** — don't recommend cancelling; it can't be re-subscribed (per the official migration doc).
5. **No auto-fallback to M2.7**: per the migration doc, Starter's M2.7 quota and M3 quota now share the same pool. After the limit is hit, the next request errors out — user must use purchased credits, upgrade, switch to pay-as-you-go, or wait for the 5h reset.

## When the user asks "what about M2.7 after the limit?"
There is no M2.7 fallback. Quote from the FAQ:
> 达到 5 小时固定窗口或周窗口上限时，您可以选择：使用已购积分 / 升级订阅套餐 / 切换到按量付费 / 等待额度窗口重置。

## Verification (Karpathy guideline)
After fetching, verify the response status (`base_resp.status_code == 0`) before rendering. If non-zero (especially `2049`/`1004`/`1008`), surface the error literally — do NOT fabricate a usage report.