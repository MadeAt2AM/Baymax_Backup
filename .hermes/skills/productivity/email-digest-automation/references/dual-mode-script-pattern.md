# Dual-Mode Script Pattern: `--json` for LLMs, `--pretty` for Humans

## The pattern

When a cron job ingests data, processes it, and delivers a digest, the processing step can live in two places:

1. **In the script** (deterministic, testable, but limited to what code can express)
2. **In an LLM agent** (reasoning-rich, but harder to test, more expensive)

The instinct is to pick one and commit. The pattern is: **build a script that does both, and let the caller choose at invocation time**.

```bash
script.py --json      # Emit structured data to stdout. Caller (LLM agent) processes it.
script.py --pretty    # Format the digest and send it. Caller (human or low-complexity cron) is done.
```

The script becomes a **data fetcher + formatter** rather than a monolithic pipeline. The LLM agent becomes a **reasoning layer** that consumes the same data the script used to format.

## Why this works

The original `email_briefing.py` did everything in one shot: fetch Gmail, classify by keyword, format as HTML, send to Telegram. That worked but had a hidden cost — every improvement to the classification logic required re-deploying the script, and the classification was limited to regex keyword matching.

Splitting into modes fixed three things at once:

- **Reasoning moved to the right layer.** The agent has access to Honcho peer cards, session history, and natural-language judgement. Keyword regexes do not. Drafting a 3-sentence reply for "Should I cut the regional slide for board time?" requires actually understanding the email — the script can't do that.
- **Ad-hoc human runs still work.** `python3 email_briefing.py` with no args still produces the legacy grouped digest and sends it. Nobody's workflow breaks.
- **The data contract is the script's only public surface.** The `--json` output is a stable interface. The script's internal classification can change, or the LLM can use a different skill, or a second LLM-driven cron can be added — none of it requires the script to change.

## When to apply

Use the dual-mode pattern when:

- The output is a **digest, briefing, or report** (not a single response)
- The data source is **a single fetch** (Gmail, RSS, an API) — the script owns the fetch + auth
- The downstream work involves **judgement, classification, or composition** that an LLM can do better than code
- You want **ad-hoc human runs to keep working** alongside the LLM-driven cron

Skip it when:

- The output is a single action (send this email, post this tweet) — there's nothing to "format," and the LLM can just do it directly
- The classification is genuinely simple (e.g. "is this spam? yes/no" with a high-confidence rule)
- The script already does both well and adding a second mode would be over-engineering

## The contract between script and LLM

The `--json` output should be a stable, self-describing payload. For `email_briefing.py --json`:

```json
{
  "fetched_at": "2026-07-02T22:30:00+08:00",
  "count": 8,
  "emails": [
    {
      "id": "...",
      "from": "Sarah Chen (sarah@brandstudio.io)",
      "from_raw": "Sarah Chen <sarah@brandstudio.io>",
      "subject": "Q3 deck — feedback needed by Friday",
      "date": "Thu, 03 Jul 2026 09:14 +0800",
      "snippet": "Hey Chris — sending the updated Q3 deck...",
      "labels": ["INBOX", "UNREAD"],
      "is_unread": true,
      "legacy_flags": ["📌 needs reply"]
    }
  ]
}
```

Key design points:

- **`fetched_at`** — the LLM needs to know when the data was pulled (timezone-aware ISO 8601). Don't make it guess.
- **`count`** — first thing the agent checks. `count: 0` is the silent-run case.
- **Include hints, not just data.** `legacy_flags` here is the old keyword classifier's output. The LLM doesn't have to use it, but having it visible means the agent can either defer to the legacy logic, override it with reason, or surface the disagreement. Information-theoretically, hints are nearly free and let the LLM be both rigorous and efficient.
- **Both `from` and `from_raw`.** The formatted name is for display, the raw RFC 5322 form is for sender-pattern matching. The LLM might need both.
- **Empty list is valid output.** Never throw an error on zero results — that's a normal state, not a failure. The agent decides what to do with it (silent, summary, etc.).

## Cron prompt patterns

### LLM-driven cron (the new normal)

```bash
cronjob create \
  --name "daily-email-briefing" \
  --skills "inbox-triage" \
  --prompt "Run /root/.hermes/.venv/bin/python3 /root/.hermes/scripts/email_briefing.py --json.
           Read the JSON. If count:0, output 'No emails in the last 24h.' and stop.
           Otherwise load the inbox-triage skill and follow it. Classify every email,
           draft 3-sentence replies for ACTION rows, output one Markdown table.
           The platform delivers your final response to Telegram." \
  --schedule "0 3 * * *" \
  --deliver "telegram:-1003825565541"
```

The prompt is short because the skill does the heavy lifting. Resist the urge to inline the bucket rules into the prompt — the skill is the source of truth and inlining duplicates it.

### Legacy keyword-driven cron (low-traffic fallback)

```bash
cronjob create \
  --name "daily-email-briefing-legacy" \
  --prompt "Run /root/.hermes/scripts/email_briefing.py. The script handles
           classification, formatting, and Telegram delivery. Report the result." \
  --schedule "0 3 * * *" \
  --deliver "local"
```

`deliver: local` because the script already sent to Telegram. `local` just records the run outcome. If you use `deliver: telegram:...` here, the platform will double-send.

## Pitfalls

1. **Two classification systems silently disagreeing.** The script's `legacy_flags` and the LLM's `inbox-triage` bucket can disagree. That's fine — the LLM has authority. But the cron prompt should explicitly say so, or the LLM will second-guess itself and produce a hybrid.
2. **Script sends to Telegram AND cron delivers too.** With `--pretty` mode, the script sends. The cron's `deliver` setting must be `local` or `none` to avoid double-sends. With `--json` mode, the script does NOT send — the cron's `deliver` setting handles it.
3. **JSON output is unstable across versions.** If you add/rename/remove fields in `--json` output, every cron prompt that parses the JSON breaks. Pin the schema in a docstring or comment and version it.
4. **Output to stdout vs stderr for `--json`.** Stdout is the contract — JSON only, no chatter. Stderr is for human-run diagnostics. Mixing them breaks anything that pipes the output to `jq` or another agent.
5. **Forgetting the silent-run case.** The LLM prompt must explicitly handle `count: 0` — otherwise the agent will either fabricate a table or fail on an empty array. Make it say "no emails in last 24h" and stop.

## Real example: the daily-email-briefing evolution

| Version | Architecture | Classification | Output |
|---|---|---|---|
| v1.0 | keyword-driven | `classify_email()` in Python | grouped HTML digest |
| v1.1 (current) | LLM-driven + legacy fallback | `inbox-triage` skill (LLM) or `classify_email()` (keyword) | Markdown table (LLM) or grouped HTML (legacy) |

The script gained `--json` and `--pretty` modes without changing its data fetch or Telegram plumbing. The cron switched to `inbox-triage` skill + `--json`. Ad-hoc human runs still work with `--pretty`. Zero breaking changes for any user of the script.
