---
name: sg-service-trade-lead-gen
description: SG service businesses without websites. Cold-call leads.
---

# Singapore Service-Trade Cold-Call Lead Generation

Finds Singapore home-service businesses (aircon, plumbing, handyman, electrician, etc.) that have **no website** and adds them to Chris's Google Sheet for web design cold-call outreach.

## When to use
- Expanding the existing SG no-website lead pipeline (aircon is already at 52 leads)
- Targeting a specific trade (plumber, handyman, electrician, etc.)
- Chris says: "find more leads", "scrape [trade]", "do the same for [trade]"

## Lead tracking format
**Always use Google Sheets, not Google Docs.** Chris prefers Sheets for lead databases — needs filtering and category columns. Add a **Category** column when adding new trades (values: aircon / plumber / handyman / electrician).

Sheet template columns:
| # | Company Name | Phone | Email | Address | Industry (SSIC) | Category | Website | Google Maps Link | Source | Email Sent | Called | Notes |

Sheet prefix-phone with `'` (apostrophe) when pushing via API to prevent Sheets treating `+65` as formula.

## Proven lead-source hierarchy (in order of effectiveness)

### 1. Google Maps scraping (best for: businesses WITH phone but no website)
- Browser pattern: `https://www.google.com/maps/search/{URL_ENCODED_QUERY}+Singapore/`
- Extract: name, phone, hasWebsite (any external link ≠ google/gstatic/youtube/schema.org), mapsUrl
- Save incrementally after every 5-10 queries (browser dies often)
- For aircon in SG: ~35/189 listings (~19%) have no website
- **Critical:** Chrome browser WILL disconnect. Restart between batches. Always run with `cdp("Emulation.setDeviceMetricsOverride", width=1920, height=1080, deviceScaleFactor=1, mobile=False)`

### 2. ACRA open data — Collection 2 (best for: finding fresh sole-proprietorships)
- API endpoint: `https://api-production.data.gov.sg/v2/public/api/collections/2/metadata`
- 27 CSV files (one per letter of alphabet), coverage through 2026-08
- Get dataset IDs per letter from metadata, download CSVs (18MB each)
- Filter by `primary_ssic_code` for the trade:
  - 43220 = plumbing + aircon install
  - 43221/43222 = plumbing only
  - 43301 = renovation contractors (often handyman)
  - 41001 = general contractors (handyman)
  - 81211 = general cleaning (sometimes aircon)
- **SCHEMA LIMITATION: NO PHONE COLUMN** (Section 12(2A) of Companies Act restricts publishing)

### 3. RecordOwl (https://recordowl.com) (best for: getting address + UEN + SSIC + "phone paywalled")
- SSIC industry pages show 12 companies per page, paginated (paywall after page 1)
- Industry page pattern: `/ssic/specialised-construction-activities`
- Use browser to scrape pages (curl returns SPA shell)
- Company page extract: `js("(() => { const text = document.body.innerText; ... return {name, phone, address, primarySSsic_code, industry, uen}; })()")`
- Phone numbers are hidden behind login (recordowl.com hides Contact Number for free tier)

### 4. Parallel subagents (for Maps phone-lookups at scale)
- Spawn 2-3 subagents in parallel with each handling a slice of UENs
- Browser pattern in subagent: search Maps → click first result → extract phone via text regex `[+\s]?65?\s?[0-9]{4}\s?[0-9]{4}`
- Save results to `/tmp/subagent_N_phones.json` incrementally per business
- Expect ~50% success rate on Maps (rest = no Google Business Profile)
- Filter out "matches" where Maps returned a different business with similar name (e.g., "Ace Plumbing" vs "The Golden Concepts")

### 5. Yellow Pages SG (BLOCKED — don't waste time)
- Radware CAPTCHA blocks all scraping. Returns SPA shell with `hcaptcha` challenge.

### 6. Facebook / site: searches
- Returns empty for fresh sole-props with no online presence

## Critical insights (learned Aug 2026)

### Singapore market is bifurcated
For trades like plumbing, **the market is split between**:
- **Big chains** (Mr Plumber SG, HW Singapore, ADM Plumbing, etc.) — ALL have websites, ALL on Maps, well SEO-optimized
- **Invisible sole-props** (UEN-2026 fresh registrations) — NO Maps profile, NO website, NO Facebook, NO Yellow Pages

For invisible sole-props, **free sources are exhausted**. Only path to phone:
1. **BizFile+ paid UEN lookup** (~$2/UEN, ~$30 for 14 ghost businesses) — official Singapore government source
2. **Singapore phone directory subscription** (sgphonebook.com)
3. **Part-time researcher in Singapore** to walk to addresses
4. **Cold walk-in** to registered address

### Phone verification
- Many Maps results for sole-prop businesses return **mismatched business names** (e.g., searching "SJH Interior" returns "Offix Pte Ltd"). Verify by checking unique ACRA name keywords against maps_name — if no shared keywords, mark as **PHONE-UNVERIFIED** in Notes.

### Lead deduping
- Dedupe by phone number (strip `+65`, spaces, dashes)
- Dedupe by company name lowercase + strip PTE/LTD
- Cross-reference with existing leads before adding

## Chrome browser is unreliable
The headless Chrome instance dies repeatedly. Mitigation:
1. After each browser_exec call, check if Chrome is still up: `curl -s http://127.0.0.1:9222/json/version`
2. If dead: `pkill -9 chrome; rm -rf /tmp/chrome-harness; mkdir -p /tmp/chrome-harness`
3. Restart: `google-chrome --headless=new --disable-gpu --no-sandbox --disable-dev-shm-usage --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-harness about:blank &`
4. Wait 5s, write DevToolsActivePort: `cat > /root/.config/google-chrome/DevToolsActivePort <<<"9222\n/devtools/browser"`
5. The DevToolsActivePort file is required for browser-harness to find Chrome

## Workflow steps
1. **Confirm scope with Chris**: which trade, target count
2. **Maps scrape** for the trade (use browser, save incrementally)
3. **ACRA open data download** (if Maps yield is low) — get CSV, filter by SSIC code
4. **RecordOwl** for fresh UEN-2026 sole-props (visit each company page)
5. **Categorize** each lead (aircon/plumber/handyman/electrician)
6. **Filter for no-website** (RecordOwl doesn't surface websites, so default to "no website" for ACRA-sourced leads)
7. **Phone lookups** via parallel subagents on Maps
8. **Push to Google Sheet** with Category column, prefix phones with `'` to prevent formula parse
9. **Honest reporting** to Chris: report blockers when sources fail, don't fabricate results

## Existing project files
- Project folder: `/root/.hermes/projects/singapore-aircon-cold-call/`
- Existing data: `all_leads.json` (52 leads), `maps_scrape.json` (189 listings), `ro_details.json` (60 companies), `all_ro_phones_clean.json` (12 phones)
- Live Google Sheet: `1GjD46l-EVN46ApqsGLz5Cz2t1ldIbMbE7f7ktRthJEY` (Chris's lead database)

## Anti-patterns (don't do)
- Don't waste time on Yellow Pages SG (CAPTCHA-blocked)
- Don't waste time on data.gov.sg datastore_search API (404 — no filter API exists)
- Don't fabricate phone numbers — Chris values honest blocker reports over fake results
- Don't use Google Docs for lead tracking — Chris wants Sheets for filtering
- Don't trust Maps "first result" for sole-prop businesses — many are mismatches