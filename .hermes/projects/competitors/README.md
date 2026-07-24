# Competitors Intelligence Dashboard

Private creator-intelligence dashboard for collecting public Instagram reel metadata through the approved self-hosted OpenCLI method, transcribing media locally with Faster-Whisper on the dev VPS, and reviewing validated Hermes analysis.

## Status

Implementation is in progress. Follow `IMPLEMENTATION_CHECKLIST.md` and `docs/IMPLEMENTATION_PLAN.md`. The live Instagram session is intentionally not guessed; authenticated collection remains blocked until the operator confirms the approved secondary account/session method.

## Architecture

- **Dev VPS:** host nginx, Docker Compose, PostgreSQL, OpenCLI/browser scraper, FFmpeg, Faster-Whisper.
- **Hermes host:** project-local analysis playbook and routine orchestration.
- **Exchange:** transcript/metadata JSON and validated analysis bundles over SSH. No public ingest endpoint.
- **Dashboard:** `https://competitors.terrybot.top` after deployment.

## Cost boundary

The scraper and transcription do not use Apify, ElevenLabs, Groq, OpenAI, or another paid external API. Hermes reasoning may use the configured Hermes model provider quota.

## First run

1. Read `IMPLEMENTATION_CHECKLIST.md`.
2. Confirm the OpenCLI secondary account/session gate.
3. Complete the unit and container test gates.
4. Deploy and create the first dashboard user.
5. Run one account and one reel only, then validate the full dashboard round-trip.

## Security

Do not commit `.env` files, cookies, OpenCLI profiles, browser traces, model caches, raw media, transcripts from private sources, or signed media URLs. Do not bypass Instagram checkpoints, login challenges, or rate limits.
