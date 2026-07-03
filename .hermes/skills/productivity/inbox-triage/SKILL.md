---
name: inbox-triage
description: "Use when I want to process my inbox in one pass — paste or list emails and get a single ACTION / WAIT / ARCHIVE table with 3-sentence draft replies for every ACTION item. Default to ACTION for human senders; do not auto-archive personal threads."
version: 1.0.0
author: Baymax (CYBERSLIDE)
platforms: [linux]
---

# Inbox Triage

Sort every email in a given window into one of three buckets and **draft a reply for every ACTION item**. Output is a single clean Markdown table — no prose around it.

## When to use

- The user pastes / lists emails and asks for triage
- The `daily-email-briefing` cron loads this skill to format its daily digest
- Any ad-hoc "process my inbox" request

## When NOT to use

- Single-email reply drafting (just draft it directly)
- Email composition from scratch (use the himalaya skill under `email/himalaya/`)
- Calendar / contact / drive work (use `google-workspace`)

## The three buckets

| Bucket | Meaning | Reply required? |
|---|---|---|
| **ACTION** | Needs a reply or decision from Chris | Yes — 3-sentence draft |
| **WAIT** | Awaiting someone else's reply; Chris has nothing to do yet | No |
| **ARCHIVE** | Newsletters, notifications, marketing, automated system mail, social pings — no decision value | No |

## Bucket rules (apply in this order)

1. **Direct ask for Chris** (asks for his input, sign-off, decision, approval, opinion) → **ACTION**. Examples: "Can you weigh in?", "Thoughts?", "Approve this?", "Pick a date."
2. **Time-bound ask with a deadline** (today / tomorrow / by EOW / before standup) → **ACTION**. Even if it feels routine — deadlines are decisions.
3. **Genuine 1:1 from a person Chris knows** (real name, not a brand) and not a notification → **ACTION by default**. **Do not auto-archive personal threads.** When the relationship or thread history is unclear, classify as ACTION and flag it for Chris's review.
4. **Genuine 1:1 where Chris is the recipient of an FYI** ("FYI", "looping you in", "no action needed", "for context") → **WAIT**. He might reply out of courtesy but isn't blocked.
5. **Calendar invites and RSVPs** → **WAIT** unless Chris must accept/decline or there's a scheduling conflict.
6. **Newsletters, product updates, release notes, GitHub digests, Substack, Medium, LinkedIn notifications, "trending", cold recruiter outreach, marketing, Stripe / payment processor receipts for charges Chris already expected, GitHub bot comments on PRs he didn't open** → **ARCHIVE**.
7. **Automated system mail** (CI/CD alerts that already resolved, "your ticket was updated") → **ARCHIVE** unless it crosses the security threshold below.
8. **Anything ambiguous** → **ACTION** and explicitly flag in a separate line below the table: `⚠️ Needs your call: <From> — <reason you couldn't decide>`. Defaulting to ACTION is safer than accidentally archiving something personal.

### Security carve-out (overrides rule 6 / 7)

These are ACTION even if they look automated:

- **Password resets / sign-in alerts / new-device logins Chris did NOT initiate** → **ACTION** with ⚠️ and surface immediately. Do not bury in archive.
- **Bank transfers, crypto withdrawals, domain renewals, hosting bills, AWS/GCP spend alerts above ~$50** → **ACTION** (financial decisions, even if amounts are small). Note: routine Stripe receipts for subscriptions Chris already pays are NOT in this bucket — those are ARCHIVE per rule 6. The distinction is "something I need to do" vs. "something that already happened and is just informing me."
- **Anything from `security@`, `noreply@<bank>.com`, `account-alerts@`** that Chris did not trigger → **ACTION** until proven otherwise.

### "Don't archive personal on instinct" guardrail

The old briefing's `classify_email()` flagged keywords and called everything else "other". That hid real threads. This skill inverts it: **the default for human senders is ACTION, not ARCHIVE.** Only mark ARCHIVE when the email is clearly automated / mass-distributed.

If a sender appears in any of these, treat as known-person (default ACTION):
- Recent Telegram / Hermes / email correspondence (last 30 days, per Honcho or session history)
- People Chris has worked with on CYBERSLIDE / MadeAt2Am projects
- Senders on the agency / brand / partner side (loaded from Honcho peer card)

If a sender is a no-reply / noreply / notifications@ / news@ / digest@ address → ARCHIVE-eligible, except for the security carve-out above.

### Worked examples (the edge cases that come up)

These were the ambiguous cases verified during the inbox-triage skill's first live dry-run. Use them as reference for new senders:

| Sender pattern | Example subject | Bucket | Why |
|---|---|---|---|
| Real person, real name, no FYI marker | "Q3 deck — feedback needed by Friday" | ACTION | Direct ask with deadline (rules 1 + 2) |
| Real person, "hey — quick one" personal opener | "hey — quick one" | ACTION | Genuine 1:1 from person Chris knows (rule 3) |
| Cold recruiter, real name, but no prior thread | "Senior role at a stealth AI startup" | ACTION | Ambiguous → rule 8. Flag in "needs your call" so Chris can decide. If Chris later says "always archive recruiters", add the domain to the cold-recruiter exclusion. |
| `noreply@cal.com` | "New booking: Strategy sync with David Lin" | WAIT | Calendar automation, no decision needed (rule 5) |
| `calendar-notification@google.com` | "Invitation: Friday planning" | WAIT | Calendar invite, no ask (rule 5) |
| `receipts+acct_1Q@stripe.com` | "Receipt #1029 — MadeAt2Am Pro plan" | WAIT | Routine charge that already happened. The skill puts this in WAIT (not ARCHIVE) because Chris may want to glance at spend; rule 6 would also be defensible. When in doubt, WAIT over ARCHIVE for receipts. |
| `noreply@github.com` | "[repo] 3 new issues assigned to you" | ARCHIVE | Automated, mass-distributed, no decision (rule 6) |
| `digest@substack.com` | "The 5 best reads on content + AI this week" | ARCHIVE | Newsletter (rule 6) |
| `noreply@<bank>.com` | "Wire transfer of $5,000 initiated" | ACTION | Security carve-out — even if Chris initiated it, surface it for review |

## Output format

One Markdown table, no preamble. Telegram renders pipe tables as compact groups, so keep columns narrow.

```
| From | Subject | Bucket | Draft reply (if ACTION) |
|---|---|---|---|
| Sarah Chen (sarah@brandstudio.io) | Q3 deck — feedback needed by Fri | ACTION | Got it — opening the deck tonight, will send focused edits by EOD Thursday. Two quick questions: does the new logo lock land, and should I keep the regional slide or cut for time? |
| Stripe (receipts+acct_1Q@stripe.com) | Receipt #1029 — MadeAt2Am | WAIT | — |
| GitHub Digest (digest@substack.com) | 12 trending repos this week | ARCHIVE | — |
```

### Draft reply rules (CRITICAL — this is the value)

- **Exactly 3 sentences.** No more. No fewer.
- Sentence 1: **Acknowledge** ("Got it.", "Thanks for the heads-up.", "Will do.")
- Sentence 2: **The substance** — the actual reply Chris would send (decision, question, next step, info). Not a meta-statement about needing to think.
- Sentence 3: **A concrete next step or close** ("Will send edits by EOD Thursday.", "Confirming for 3 PM SGT.", "Will loop back once X lands.")
- **Match Chris's voice** — direct, no fluff. Use Honcho / memory / session context to inform. If Chris has spoken to this person before, mirror the register from past replies.
- **Don't invent facts.** If the email asks a question you can't answer from context, draft the question back ("Need to check on X — will confirm by [time]") rather than fabricating a number.
- **Strip the greeting and sign-off** — Chris pastes the reply, not an email client. No "Hi Sarah," or "Best, Chris". Body only.
- **If Chris would obviously defer** ("Let me think about it" with no timeline), say so explicitly and propose a follow-up time. Don't ghost the sender in the draft.

### For WAIT / ARCHIVE rows

Leave the Draft reply column as a single em-dash: `—`.

### Below the table (only if needed)

After the table, optionally add one of:

- A short summary line: `**N** ACTION · **M** WAIT · **K** ARCHIVE`
- An "ambiguous" flag list (see rule 8 above)
- An optional second table with the top 3 ACTION items expanded (full email snippet) if any look time-sensitive

Do NOT add prose like "Here's your briefing for today!" — table only.

## How the daily cron calls this skill

The `daily-email-briefing` cron runs:

```bash
/root/.hermes/.venv/bin/python3 /root/.hermes/scripts/email_briefing.py --json
```

(Use the venv python — bare `python3` returns empty Gmail results because `googleapiclient` only lives in the venv.)

The script fetches the last 24h of Gmail and emits one JSON object per email to stdout (no Telegram send). The agent's prompt then invokes this skill against that JSON and posts the resulting table to Telegram.

The script's `--json` mode is the canonical interface for any LLM-driven triage. The old HTML / grouped-by-flag formatting is preserved as the `--pretty` default for any human-run ad-hoc use.

## Pitfalls

1. **Drafting replies that sound like a corporate lawyer.** "I will review this and revert" is useless. Match Chris's actual register: short, direct, says what's happening.
2. **Treating "no-reply" senders as people.** noreply@stripe.com, notifications@github.com, news@ — these are ARCHIVE candidates unless the email is security-critical.
3. **Auto-archiving 1:1 from a known person.** This is the failure mode Chris explicitly called out. If the sender is a real person Chris has talked to recently, default ACTION unless the email is a clear FYI with no ask.
4. **Dumping every email into one mega-table with no header.** The header row `| From | Subject | Bucket | Draft reply |` is required.
5. **Drafting a reply for ARCHIVE / WAIT rows.** Em-dash only. Drafts are ACTION-only.
6. **Inventing facts to fill a draft.** If Chris's reply would need info not in the email, ask for it back, don't fabricate.
7. **Skipping the cron context.** The cron run has no current-chat context. The skill + Honcho are the only sources of "who is this person" — load the Honcho peer card at the start of the run.
8. **Sending the briefing twice.** Once the cron runs and posts to Telegram, do not re-send. If the script fails, log the error to stderr; do not fall back to a second Telegram send.

## Verification

After triage is posted to Telegram, the run is "done" when:
- The table header is present
- Every ACTION row has a 3-sentence draft
- Every WAIT / ARCHIVE row has `—`
- No invented facts (sanity-check by re-reading drafts against the source snippets)
- The post landed in chat_id `-1003825565541` (Baymax_Home) — if the cron is the agent, the agent's final response is auto-delivered by the platform layer