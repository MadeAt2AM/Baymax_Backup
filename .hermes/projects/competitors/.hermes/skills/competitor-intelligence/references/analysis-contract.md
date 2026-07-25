# Analysis Contract — JSON Schema and Validation Rules

The analysis bundle is the single source of truth for a single reel's
analysis. It is enforced by `pipeline.models.AnalysisBundle` (Pydantic v2)
and `scripts/validate_analysis.py`.

## Top-level shape

```json
{
  "niche": "I make content about X for Y.",
  "source": { ... },
  "analysis": { ... },
  "model": { ... }
}
```

## Per-field rules

### `niche`

- Loaded from `config/project.yaml`. Must be a non-empty string.

### `source` (a `ReelInput`)

- `shortcode`: matches `^[A-Za-z0-9_-]{6,20}$`.
- `username`: lowercase, no leading `@`, max 64 chars.
- `url`: must begin with `https://www.instagram.com/`.
- `views`, `likes`, `comments`: non-negative integers.
- `caption`: max 4000 chars.
- `transcript`: max 20000 chars. Empty is allowed for music-only reels.
- `scraped_at`: ISO-8601 with timezone offset.

### `analysis` (an `AnalysisSection`)

- `relevance_score`: integer in `[1, 10]`.
- `verdict`: boolean. `true` only when `score >= 7` AND a teachable insight exists.
- `topic`: 1–120 chars.
- `tools`: array of strings (named products/services mentioned).
- `hook_style`: one of `problem-promise`, `contrarian-claim`, `list-tease`,
  `demo-first`, `story-frame`, `data-shock`, `identity-call`, `other`.
- `reasoning`: 1–1000 chars.
- `sections`: array of `Section` objects. Each section must have:
  - `label`: one of `Hook`, `Beat 1..8`, `CTA`.
  - `text`: 1–4000 chars. Must be a **verbatim** substring of the
    supplied transcript.
  - `note`: 1–240 chars.
- `research`: array of `ToolResearch` objects. Each must have:
  - `tool`: 1–120 chars.
  - `one_liner`: 1–240 chars.
  - `how_it_works`: 1–1000 chars.
  - `hook_fact`: 1–240 chars.
  - `source_url`: must be a valid `http://` or `https://` URL.
- `angle_suggestion`: 1–600 chars.

### `model` (a `ModelMetadata`)

- `provider`: 1–64 chars.
- `model`: 1–128 chars.
- `analyzed_at`: ISO-8601 with timezone offset.

## Hard rejections

The validator fails closed with a non-zero exit on:

- Score outside `[1, 10]`.
- Hook style outside the enum.
- An empty `text` in any section.
- A `text` field that is not a substring of the supplied transcript.
- A `source_url` that is not a valid HTTPS URL.
- A `model.provider` or `model.model` that is empty.
- A bundle that fails to parse as JSON.

The validator never silently fixes or transforms the input. The operator
must rewrite the bundle and re-run the validator.
