# AI Agent Spec — Webinar Sales Closer

> Derived from Instagram reel by **Greg Isenberg** (`@gregisenberg`)
> Reel ID: `DbWr5QTRqC6` — "How to use AI agents to make more sales during live webinars/workshops" (62.6s)
> Source: `media/reel.mp4` → `transcripts/reel.txt`

---

## 1. Overview

An AI agent that runs **after every live webinar / workshop call** and produces **personalized, sales-ready follow-up emails** for every attendee — replacing the generic "Thanks for joining!" blast with one-to-one messaging routed by actual attendee behavior.

**Premise (from reel):** *"The sale you're chasing from that webinar was already lost the moment you sent the same email to everyone."*

The agent watches who talked, who stayed, who dropped, what they asked, and what they cared about — then drafts a custom email for each segment and hands it to a human for final review before it ever reaches the inbox.

---

## 2. Core Features

Derived directly from the reel content; numbered so we can reference them.

### Data acquisition
- **F1. Multi-platform meeting ingestion** — pulls from Zoom API or any meeting app API (Zoom-first per reel; same shape works for Google Meet, Teams, Demio, Livestorm, etc.)
- **F2. Multi-modal transcript capture** — grabs the full transcript, chat log, and Q&A interactions from the same call
- **F3. Per-attendee timeline reconstruction** — stitches chat, questions, talk time, and presence into a single per-attendee record

### Behavioral analysis
- **F4. Speaker-vs-silent segmentation** — separates "people who asked questions" from "people who never spoke"
- **F5. Intent detection on questions** — extracts the topic brought up + product feature(s) referenced; e.g. *"asked about WhatsApp scheduling → tag as `high_intent:scheduling`"*
- **F6. Silent-attendee engagement scoring** — measures call duration + exact drop-off point for non-speakers
- **F7. Drop-off correlation** — links the moment someone left to the slide / objection that preceded it (which slide was on screen, which question/objection preceded the exit)
- **F8. Objection taxonomy mapping** — categorizes objections into known buckets: pricing, ROI, integration, trust, timing (extensible)

### Routing & drafting
- **F9. Email-template routing** — maps each attendee profile to the right email style:
  - High-intent question asked → recap + value-aligned follow-up
  - Pricing-objection drop-off → pricing clarification email
  - ROI-objection drop-off → ROI-focused email
  - Generic lurker → soft nurture
- **F10. Personalized email generation** — drafts a one-to-one email per attendee referencing their actual behavior (question text, drop-off point, slide)
- **F11. CRM draft write-back** — saves the draft email directly into the CRM so the human can review in their existing workflow (no new UI required)
- **F12. Human-in-the-loop approval gate** — drafts never auto-send; a human reviews and refines before anything leaves the system

### Operational
- **F13. Works with any meetings application API** — Zoom mentioned explicitly, but the architecture is API-pluggable
- **F14. Webhook-driven trigger** — fires automatically when a meeting/recording ends (via Zoom webhook, no manual kickoff)

---

## 3. Workflow (step-by-step)

This is the exact sequence Greg described, tightened into a single run from "webinar ends" → "emails ready to review."

1. **Trigger** — webhook fires when the Zoom call ends (or call transcript becomes available via recording-ready event)
2. **Ingest** — agent calls the meeting API and pulls **transcript + chat + Q&A + attendance** as one normalized dataset
3. **Segment attendees** — split into two queues:
   - **Speakers (asked at least one question / talked)** → behavior path A
   - **Silent (never spoke)** → behavior path B
4. **Path A — Speaker analysis**
   - Extract every question asked → tag the topic + which product feature(s) it touches
   - Bucket the prospect as `high_intent` if they engaged with a specific feature, otherwise `engaged_curious`
5. **Path B — Silent-attendee analysis**
   - Compute `on_call_duration` and `drop_off_timestamp` for each silent attendee
   - Replay the timeline backward from drop-off → identify the slide + objection/objection-cluster that was on screen in the final moments
   - Map drop-off to objection bucket: `pricing`, `ROI`, `integration`, `trust`, `timing`
6. **Route to email template** — using the bucket from step 4 or 5, pick the matching template:
   - `high_intent` / `engaged_curious` → recap + tailored value email
   - `pricing` → pricing-clarification email
   - `ROI` → ROI-narrative email (with relevant slide)
   - Other objections → objection-handling template
   - Bare lurker (no signal either way) → soft nurture
7. **Draft per-attendee email** — fill the template with personal references (their question, their drop-off slide, their specific feature interest)
8. **CRM write-back** — save each draft as a new draft email / draft activity on the attendee's CRM record, **never as a sent email**
9. **Human review** — a human opens the CRM, reviews each draft, edits if needed, and clicks send
10. **Loop** — feedback on which templates actually convert can be wired back later as `→ step 6 ranking`

---

## 4. Inputs / Outputs

### Inputs
- Meeting API credentials (Zoom first; meetings app API is pluggable per **F13**)
- CRM API credentials (HubSpot / Salesforce / Pipedrive / etc.)
- Product knowledge context (so the agent knows which feature map to which objection) — could be the agent's system prompt + a small product lookup
- Routing rules (configurable: which objection maps to which template)

### Outputs
- One **draft email per attendee** written back to the CRM
- Optional structured log: attendee_id → segment → routed_template → drop_off_at → which_question
- Human approval queue in the CRM (existing UI; no new app)

---

## 5. Human-in-the-Loop Touchpoints

Reel was explicit about this: **the human reviews before any send.** Touchpoints:
- Step 9 above — always. No auto-send under any circumstance.
- Optionally: a daily summary push showing how many drafts were generated, per template, so the team can sanity-check the agent's segmentation.

---

## 6. What's explicitly NOT in scope (per reel)

- Generating or improvising product copy the human didn't approve — agent only personalizes around existing template structure
- Auto-sending — not in spec; human always approves (**F12**)
- Real-time intervention mid-call — the agent runs **after** the call, not during

---

## 7. Open Questions / Next Iterations

Things to nail down before building:

- **Email platform** — where do drafts land? (Gmail drafts via API? HubSpot engagement? Salesforce tasks?)
- **Which meeting app first?** — reel says "Zoom or any" — I'd scope this to **Zoom first**, then Generalize.
- **Product knowledge source** — what's the agent's source of truth on features/objections? A static doc fed at startup, or the CRM's product catalog?
- **Personalization depth** — does the email reference the attendee's **question text verbatim**, or just topic + feature? Verbatim is more personal but needs care (PII).
- **Conversion tracking loop** — wire back "which drafted template converted" later to train the router.
- **Latency** — Zoom webhook → drafts in CRM within how long? (Reasonable target: under 5 minutes.)

---

## 8. Working Artifacts

| File | Purpose |
|---|---|
| `media/reel.mp4` | Original downloaded reel (1080×1920, 4.4 MB, 62.6 s) |
| `media/reel.jpg` | Reel thumbnail |
| `media/reel.ogg` / `media/reel.wav` | Audio extracted for transcription |
| `media/reel.info.json` | Full yt-dlp metadata |
| `transcripts/reel.txt` | Whisper transcript with timestamps + segment-aligned text |
| `transcribe_groq.py` | Reusable Groq Whisper transcription helper (Cloudflare-safe UA) |
| `SPEC.md` | This document |
