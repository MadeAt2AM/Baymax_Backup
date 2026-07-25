# Analysis playbook — what the Hermes playbook entry does with a staged batch

After `scrape.py` stages `data/staging/<run-id>/batch.json`, the Hermes `competitor-intelligence` playbook entry processes each item. The reason for Hermes is to keep the reasoning stage explicit, versioned, and reusable across sessions and routines. The mechanical stages (scrape, download, transcribe) remain on the dev VPS.

Say: **"Process the staged batch `<run-id>` following ANALYZE.md."** The playbook entry reads `competitor-accounts.md`, `config/project.yaml`, and the staged batch, and writes one analysis bundle per reel.

## 0. Your niche (loaded from config/project.yaml)

The niche is loaded from the `niche` field of `config/project.yaml`. Editing the YAML is the only place the niche lives.

```
Example: "I make content about strength training for busy professionals over 30."
```

If the niche is missing, the playbook entry halts and asks the operator to edit `config/project.yaml`. There is no in-line placeholder guessing.

## 1. Score + break down (per reel)

For each reel in the staged batch, the playbook entry scores it for relevance to the niche on a 1–10 scale and extracts the structural breakdown.

- **10**: directly on-niche — the exact topics you post about
- **7–9**: adjacent — same audience, neighbouring topic
- **4–6**: general/hype content with a loose angle on your niche
- **1–3**: off-topic (lifestyle, unrelated verticals)

Per reel, the playbook entry produces:

- `topic`: 4–8 word summary of what the reel teaches
- `tools`: array of named products / services mentioned (if any)
- `hookStyle`: one of `["problem-promise","contrarian-claim","list-tease","demo-first","story-frame","data-shock","identity-call","other"]`
- `verdict`: `true` if score >= 7 AND there's a teachable insight, else `false`
- `reasoning`: one sentence
- `sections`: split the transcript into structural beats — array of `{label, text, note}`:
  - `label`: `Hook` (the first 1–2 lines / attention grab), then `Beat 1`, `Beat 2`, … (each distinct step or argument), then `CTA` (the ask). Use what fits; not every reel has every section.
  - `text`: the verbatim transcript for that segment — split the real words, do not paraphrase.
  - `note`: one short phrase on what the beat is *doing* ("names the pain", "step 1 — setup", "FOMO close"). This is the "what's working" signal.

## 2. Gate

Reels with `score >= 7 AND verdict == true` are kept. Everything else is rejected: its shortcode is appended to `data/ledger.json → low_score` and no analysis is written.

## 3. Research the tools (per keeper — optional but recommended)

For each named tool, the playbook entry does a quick web search (do not rely on memory — these move fast): what it is in one line, how it works, one hook-worthy fact. Source links are kept.

## 4. Write one analysis bundle per keeper → `data/staging/<run-id>/analysis/<shortcode>.json`

The bundle schema is enforced by `scripts/validate_analysis.py`. The slug is derived from the topic (lowercased, non-alphanumerics → `-`, max 50 chars).

```json
{
  "niche": "string",
  "source": {
    "account": "string",
    "url": "https://www.instagram.com/reel/...",
    "shortcode": "string",
    "views": 0,
    "likes": 0,
    "comments": 0,
    "caption": "string",
    "scraped_at": "ISO-8601 with timezone"
  },
  "analysis": {
    "relevance_score": 7,
    "verdict": true,
    "topic": "string",
    "tools": ["string"],
    "hook_style": "problem-promise",
    "reasoning": "string",
    "sections": [
      {"label": "Hook", "text": "verbatim", "note": "names the pain"}
    ],
    "research": [
      {"tool": "string", "one_liner": "string", "how_it_works": "string", "hook_fact": "string", "source_url": "https://..."}
    ],
    "angle_suggestion": "string"
  },
  "model": {
    "provider": "string",
    "model": "string",
    "analyzed_at": "ISO-8601 with timezone"
  }
}
```

The verbatim text rule is enforced: the `text` field of each section must be a non-empty substring of the supplied transcript. Paraphrased or invented text fails validation.

## 5. Validate before publish

Every analysis bundle is validated before it can enter the publish bundle. The validator:

- Asserts score is in 1–10.
- Asserts hook style is in the enum.
- Asserts sections are non-empty arrays, well-ordered, and each `text` is verbatim from the transcript.
- Asserts every URL is well-formed and `https://`.
- Asserts research tool notes have non-empty `one_liner`, `hook_fact`, and `source_url`.
- Asserts `model.provider` and `model.model` are present and non-empty.

A bundle that fails validation is rejected and the reel is marked as `failed` in the ledger. The operator can re-run the playbook entry for the rejected reel once the underlying issue is diagnosed.

## 6. Build the publish bundle

`scripts/build_publish_bundle.py` collects all validated analysis bundles into a single `bundle.json` and writes it to `data/staging/<run-id>/analysis/bundle.json`. The bundle includes the run ID, the SGT timestamp, and the imported bundle is intended for the container-only importer.

## 7. Publish (container-only)

`s scripts/publish_bundle.sh` transfers the bundle over SSH to the dev VPS, drops it into `/srv/projects/competitors/imports/`, and the container-only importer appends it to PostgreSQL in a single transaction. The importer:

- Verifies the run ID is unique.
- Upserts each reel on `shortcode`.
- Inserts the analysis row with `relevance_score`, `hook_style`, `sections`, `research`, and `angle_suggestion`.
- Marks the run as `completed` once all rows are committed.

A duplicate publish returns an explicit `already_imported` result and never silently inserts again.

## 8. Rebuild the dashboard

Once the importer reports success, the dashboard reflects the new reel automatically. Open `https://competitors.terrybot.top`.

> The notes are *research artifacts*, not scripts. When an idea graduates to your own content, write it in your voice — the angle suggestion is the seed, never the copy.
