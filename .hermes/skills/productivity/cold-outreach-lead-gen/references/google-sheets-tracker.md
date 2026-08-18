# Google Sheets as Lead Tracker — Reference

Chris's 2026-08-17 explicit preference: "convert the google docs to google sheets, use that sheet for all the leads". Sheets handles tabular lead data natively and avoids the doc-corruption risk from repeated appends.

## Why Sheets over Docs

| Capability | Docs | Sheets |
|---|---|---|
| Tabular display | Poor (just text rows) | Native — sortable, filterable |
| Append without corruption | Risk after 20+ appends | Robust (single update call) |
| Bulk update via API | Slow per-row | One call updates whole range |
| Filter / sort / pivot | Manual | Native |
| Sharing for team review | OK | OK |
| Conditional formatting | Manual | Native |
| Formula column for stats | No | Yes |

**Decision rule**: any lead tracker with >20 rows or that needs sortable columns → use Sheets. Docs only for prose-heavy outreach briefs.

## Schema that worked (2026-08-17)

```
| # | Company Name | Phone | Email | Address | Industry (SSIC) | Website | Google Maps Link | Source | Email Sent | Called | Notes |
```

12 columns. `Source` distinguishes Maps vs RecordOwl vs email-only leads — useful when deduping.

## Step-by-step setup

```bash
cd /root/.hermes/skills/productivity/google-workspace

# 1. Create the sheet
python3 scripts/google_api.py sheets create --title "Singapore Aircon Cold Call Leads"
# → returns spreadsheetId like "1GjD46l-EVN46ApqsGLz5Cz2t1ldIbMbE7f7ktRthJEY"

# 2. Build the rows JSON (see "Building the payload" below)

# 3. Push it
python3 scripts/google_api.py sheets update \
  "<spreadsheetId>" "A1:L54" \
  --values "$(cat /tmp/sheet_payload.json)"
# → {"updatedCells": 648, "updatedRange": "Sheet1!A1:L54"}
```

## Building the payload

Use Python in `execute_code` (not bash heredoc) to build the JSON safely:

```python
import json

rows = [headers]  # header row first
for i, lead in enumerate(all_leads, 1):
    phone = lead.get('phone', '') or ''
    # CRITICAL: prefix with apostrophe to prevent formula interpretation
    if phone.startswith('+'):
        phone = "'" + phone
    row = [
        str(i),
        lead['company'],
        phone,
        lead.get('email', ''),
        lead.get('address', ''),
        lead.get('industry', ''),
        lead.get('website', ''),
        lead.get('maps_url', ''),
        lead.get('source', ''),
        lead.get('email_sent', 'No'),
        lead.get('called', 'No'),
        lead.get('notes', ''),
    ]
    rows.append(row)

with open('/tmp/sheet_payload.json', 'w') as f:
    json.dump(rows, f)
```

## The phone-number gotcha

Sheets interprets any cell starting with `+`, `-`, or `=` as a formula. A cell containing `+65 8389 4134` becomes `#ERROR!`. **Fix: prefix with a literal apostrophe** before pushing:

```python
phone = "'+65 8389 4134"  # apostrophe forces string interpretation
```

The apostrophe doesn't display in Sheets — it's just a type hint. The cell value is the phone number as a literal string.

## Verifying the push

```bash
python3 scripts/google_api.py sheets get \
  "<spreadsheetId>" "A1:E5"
```

Returns JSON. Eyeball the first 5 rows to confirm:
- Header row has the 12 column titles
- Phone cells show actual numbers (not `#ERROR!`)
- No truncation in company names

## Pitfalls

1. **Don't use `sheets append`** — `sheets update` with a full range is more reliable and idempotent. If you accidentally run `append` twice you get duplicate rows.

2. **The range string `"A1:L54"` assumes 12 columns.** Count your columns first; off-by-one column counts silently fail (push succeeds but last column is empty).

3. **`updatedCells` count = rows × columns.** If you see `updatedCells: 648` and you sent 54 rows × 12 cols = 648, that's correct. If the count is wrong, your payload shape doesn't match the range.

4. **Service unavailable (503) errors happen.** Retry once after 5 seconds. If still failing, the API is having a bad day — don't loop, just save the payload to disk and ship later.

5. **The sheet URL pattern is**: `https://docs.google.com/spreadsheets/d/<spreadsheetId>/edit`

6. **Don't try to format headers via the API on first push.** Get the data in first, then use `sheets update --values` with a separate call to format headers bold / freeze row 1 if needed (or do it manually in the UI). Mixing data + formatting in one push is fragile.

## When to switch back to Docs

- Outreach copy / briefs / sales scripts (prose-heavy)
- Sharing with a non-technical stakeholder who hates spreadsheets
- Single-leads-summary docs ("Here's everything I learned about Acme Aircon")