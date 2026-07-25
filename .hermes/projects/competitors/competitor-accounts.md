# Competitor accounts

The scraper reads every row where **Active = yes**. Exact Instagram usernames, no `@` needed. Start with 3–7 accounts — the ones whose audience you actually want.

Good picks: accounts your size or 1–2 tiers above you, posting reels consistently in your niche. Skip celebrities — their numbers don't tell you anything you can use.

Use a **secondary Instagram account** for the scraper, never your primary account. The session is a credential and lives in `/srv/competitors-private/opencli-profile/` on the dev VPS with restrictive permissions.

| Username | Niche / why tracked | Size (rough) | Active |
| ---------------- | ------------------------------------ | ------------ | ------ |
| mallu.wave | approved secondary account for the OpenCLI scraper | 5k | yes |
| example_handle_2 | one tier up — format ideas | 80k | no |
| example_handle_3 | adjacent niche, strong hooks | 25k | no |

**Maintain it:** when an account goes quiet or drifts off-niche, flip it to `no` (don't delete the row — the history explains itself later). Add new finds as you spot them; the dashboard's "reach by account" view will tell you quickly who's worth keeping.

**Volume warning:** increasing accounts or reel limits increases Instagram request volume, account-ban risk, dev-VPS CPU/disk, and Faster-Whisper processing time. Even though no paid API is used, the cost is real. Keep the per-account/per-run caps honest.

**Validation rules enforced by `pipeline/accounts.py`:**

- Username must match `^[a-z0-9._]{1,30}$` (case normalised to lowercase).
- Each handle is unique; duplicates are rejected.
- `Active` must be exactly `yes` or `no`.
- At least one row must be `Active = yes` before the pipeline can start.
