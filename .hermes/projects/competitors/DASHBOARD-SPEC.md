# Dashboard spec — the React/FastAPI dashboard at competitors.terrybot.top

The dashboard is a single-operator React + FastAPI application behind host nginx on the dev VPS. It is authenticated, read-only, and refreshed by the publish-bundle importer; there is no "Run now" button in the first release.

The data is sourced from PostgreSQL on the dev VPS. Updates are immediate after a successful import. The dashboard never serves transcript data without authentication.

## Routes (FastAPI)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/healthz` | Public | Container and DB health |
| `POST` | `/api/auth/login` | Public, rate-limited | Create secure session |
| `POST` | `/api/auth/logout` | Session | Clear session cookie |
| `GET` | `/api/auth/me` | Session | Confirm authenticated operator |
| `GET` | `/api/dashboard/summary` | Session | KPIs, reach, taxonomy, latest run |
| `GET` | `/api/reels` | Session | Paginated, filtered reel list |
| `GET` | `/api/reels/{id}` | Session | Full transcript, research, and angle |
| `GET` | `/api/runs` | Session | Pipeline history and failures |

## Layout — two tabs (React)

### Tab 1 — Dashboard (the daily read)

Top to bottom:

1. **KPI tiles** (animate: count up on load) — total reels tracked · accounts tracked · combined views · top reel's views · most-common hook style this batch.
2. **Reach by account** — horizontal bar chart (bars grow from zero on load): total views per account. This is the "who's actually pulling reach" view.
3. **Hook taxonomy** — one card per hook style (`problem-promise`, `contrarian-claim`, `list-tease`, `demo-first`, `story-frame`, `data-shock`, `identity-call`, `other`) showing count + combined views. Sort by combined views.
4. **Reel cards** — every keeper as a card, sorted by views (desc). Each card: account · topic · views/likes/comments · hook-style tag · relevance score. Click to expand: the full sectioned transcript (Hook / Beats / CTA with their notes), the research block, and the angle suggestion. Collapse on second click.
5. **Date-window selector**: latest batch, 7 days, 30 days, all time.
6. **Filters**: account, hook style, relevance score, date range, text search.

### Tab 2 — Pipeline (how the machine works)

A horizontal node graph of the pipeline, drawn with plain HTML/CSS:

```
[OpenCLI scrape] → [OpenCLI download] → [FFmpeg normalize] → [Faster-Whisper] → [Hermes: score + break down] → [Validate] → [Postgres] → [this dashboard]
```

Each node: name + one-line description + per-run resource cost (scrape = dev-VPS bandwidth · transcribe = dev-VPS CPU + RAM · Hermes stages = operator's model quota). Animate the nodes cascading in left → right on tab switch.

Below the graph: the latest run status, a historical run table with start/end timestamps rendered in SGT first and UTC second, and explicit failed/skipped counters.

## Design rules

- Light theme, generous whitespace, one accent color (Crimson `#D32F2F`) used consistently, system font stack. No dark-mode toggle in the first release.
- Load animations matter — tiles count up, bars grow, cards fade in staggered. They make the thing feel alive without external dependencies.
- All UI text is rendered as text, never raw HTML. User-provided strings are escaped.
- Reduced-motion fallback: animations disabled when `prefers-reduced-motion: reduce` is set.
- WCAG AA colour contrast.
- Desktop-first responsive behaviour. Mobile is a non-goal for the first release.

## Data contract (API)

The `GET /api/dashboard/summary` response shape:

```json
{
  "kpis": {
    "reels_kept": 0,
    "accounts_tracked": 0,
    "combined_views": 0,
    "top_reel_views": 0,
    "top_hook_style": "string"
  },
  "reach_by_account": [{"account": "string", "views": 0, "reels": 0}],
  "hook_taxonomy": [{"hook_style": "string", "count": 0, "combined_views": 0}],
  "latest_run": {
    "run_id": "string",
    "started_at": "ISO-8601 with timezone",
    "finished_at": "ISO-8601 with timezone",
    "status": "string",
    "scraped_count": 0,
    "analyzed_count": 0,
    "kept_count": 0,
    "rejected_count": 0,
    "failed_count": 0
  }
}
```

The `GET /api/reels` response shape supports `account`, `hook_style`, `score_min`, `date_from`, `date_to`, `q` (text), `page`, `page_size`. The `GET /api/reels/{id}` response includes the full transcript segments, the research block, the angle suggestion, and the source URL with safe rendering.

## Required states

Every data surface must implement:

- Loading skeleton matching the final layout.
- Empty state that explains how to populate the first batch.
- Error state with retry action and a readable cause category.
- Reduced-motion fallback.
- Keyboard navigation and visible focus.
- WCAG AA colour contrast.

## Test IDs

Test IDs are reserved for a small number of stable, top-level interactive elements. They are stable across renders; they are not glued to internal CSS classes.

## Performance targets

- LCP < 2.5 s on a fast 3G profile against the deployed dashboard.
- INP < 200 ms.
- CLS < 0.1.
- API `GET /api/dashboard/summary` p95 < 250 ms on the dev VPS.

## Security headers

The dashboard serves `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy` headers at root, `/api/`, and static asset paths. The session cookie is `HTTPOnly`, `Secure`, `SameSite=Lax`, scoped to `competitors.terrybot.top`.
