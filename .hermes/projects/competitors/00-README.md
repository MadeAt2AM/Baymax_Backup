# Competitors Intelligence Dashboard — full setup guide (Hermes adaptation)

This is the system from the reel: every morning it can rebuild a dashboard of your competitors' latest reels — who's posting, which hooks are pulling views, the full script of every reel broken into Hook / Beats / CTA — so you review your niche in about three minutes instead of scrolling for hours.

You are getting the whole thing:

| File | What it is |
|---|---|
| `00-README.md` | This guide — start here |
| `scrape.py` | The thin CLI wrapper that schedules the pipeline (mechanical orchestration only) |
| `ANALYZE.md` | The analysis playbook the Hermes playbook entry follows to score + break down every reel |
| `DASHBOARD-SPEC.md` | The spec for the React/FastAPI dashboard at `https://competitors.terrybot.top` |
| `competitor-accounts.md` | Your competitor list — a Markdown template to fill in |

The mechanical stages (Instagram scrape → download → FFmpeg normalize → Faster-Whisper → publish) run on the dev VPS via Docker Compose. The reasoning stage (score, beats, research, angle) runs as a Hermes playbook entry on the Hermes host. There is no paid external API for scraping or transcription.

---

## The 5-minute version (recommended)

1. Confirm the dev VPS (`147.79.18.32`) is reachable and that the competitor-intelligence directory exists on it.
2. Confirm the OpenCLI installation on the dev VPS (`opencli --version`) and that the Browser Bridge is connected.
3. Edit `competitor-accounts.md` and add the approved 3–7 Instagram handles with `Active = yes`.
4. Edit `config/project.yaml` and replace the `YOUR NICHE` placeholder with `"I make content about X for Y."`
5. Run the pipeline once with the safety caps:

```bash
python3 scrape.py --check-session
python3 scrape.py --check-whisper
python3 scrape.py --limit 1 --cap 1 --accounts <one_approved_account>
```

6. Hermes will find the staged batch at `data/staging/` and produce the analysis bundle. Validate it with `scripts/validate_analysis.py`, then publish it via `scripts/publish_bundle.sh`.
7. Open `https://competitors.terrybot.top` to see the reel in the dashboard.

---

## What it costs to run

- **Scraping**: self-hosted OpenCLI Instagram method on the dev VPS. No Apify, no third-party scraping API.
- **Transcription**: self-hosted Faster-Whisper + CTranslate2 + FFmpeg on the dev VPS. No ElevenLabs, no OpenAI, no Groq.
- **Reasoning**: Hermes uses the operator's configured model provider, which may consume the model's quota. This is a separate cost from scraping/transcription. The pipeline cannot run without explicit provider configuration.
- **Infrastructure**: dev VPS CPU, RAM, disk, and outbound network. The default caps (3 reels per account, max 50 per run, max 100 MiB per reel, max 180 s per reel) keep the resource footprint trivial.

Realistic total: **dev-VPS time + your existing Hermes model quota.** No external API spend.

---

## What you need before running

1. **OpenCLI**: installed on the dev VPS with a browser session authenticated against the approved secondary Instagram account. The Browser Bridge extension must be enabled in Chrome/Chromium.
2. **Faster-Whisper model**: the pinned model revision pre-downloaded into the dev-VPS cache. The first download is the only network egress.
3. **PostgreSQL**: a database created for the dashboard with the migration applied.
4. **Dashboard account**: a single-operator username and bcrypt password hash stored in `/srv/secrets/competitors.env`.
5. **Niche statement**: a single sentence loaded into `config/project.yaml` so the analysis playbook stays grounded.

None of these are guessed. The implementation will halt and ask for the exact value if it is missing.

---

## Manual setup (if you'd rather drive)

1. Fill in `competitor-accounts.md` — one row per competitor, `Active = yes` for the ones to track.
2. Edit `config/project.yaml` and replace the `YOUR NICHE` placeholder with what you actually make content about.
3. Run the preflight checks (session and Whisper model):

```bash
python3 scrape.py --check-session
python3 scrape.py --check-whisper
```

4. Run the scraper with safety caps:

```bash
python3 scrape.py --limit 1 --cap 1 --accounts <one_approved_account>
```

5. Find the staged batch in `data/staging/<run-id>/batch.json`. Run the analysis playbook from Hermes on each reel. Validate the output:

```bash
python3 scripts/validate_analysis.py data/staging/<run-id>/analysis/<reel-id>.json
```

6. Build the publish bundle and transfer it back over SSH:

```bash
python3 scripts/build_publish_bundle.py data/staging/<run-id>/analysis/
bash scripts/publish_bundle.sh data/staging/<run-id>/analysis/bundle.json
```

7. Reload the dashboard at `https://competitors.terrybot.top` to see the reel.
8. Repeat whenever you want fresh data. The ledger and the `reels.shortcode` unique constraint ensure only new reels are charged against Instagram.

---

## The weekly rhythm

Run it once or twice a week. Open the dashboard, read the top hooks and the taxonomy (which hook styles keep winning in your niche), pick your angles. The dashboard updates as soon as the publish bundle is imported.

For automation, schedule a Hermes routine once the manual path is green. The routine prompt is self-contained, pinned to the project `workdir`, attached to the `competitor-intelligence` skill, and restricted to the required toolsets. The schedule is SGT, recorded in SGT first and UTC second.

---

## Fair-use notes (read this once)

- This is **research signal**, not a content-theft kit. You are studying what works — hooks, structures, topics — not republishing anyone's reels. Do not repost the videos or transcripts.
- Use a **secondary Instagram account** for the scraper, never the operator's primary account. The session is a credential; treat it like one.
- The downloaded videos in `data/staging/<run-id>/videos/` are working files for transcription. Delete them after successful transcription and validated import, subject to the approved retention policy.
- Do not bypass Instagram checkpoints, login challenges, rate limits, or account protections. If any of those appear, the run halts and the operator is notified.
- Transcripts are private research material. The dashboard is single-operator and authenticated. Transcript text is never embedded in unauthenticated responses.

## Troubleshooting

- **"OpenCLI Browser Bridge not connected"** — open Chrome/Chromium on the dev VPS with the OpenCLI extension enabled. Re-run `--check-session`.
- **"Whisper model not found"** — run the model download once with the network enabled, then verify the cache loads with `--check-whisper`. Subsequent runs work offline.
- **"No rows with Active = yes"** — edit `competitor-accounts.md` and mark at least one account as `Active = yes`.
- **"Empty transcript"** — some reels are music-only. They still stage; the analysis playbook scores them from the caption.
- **Anything else**: paste the error into Hermes. The `competitor-intelligence` skill has the procedure, the validation, and the recovery paths.
