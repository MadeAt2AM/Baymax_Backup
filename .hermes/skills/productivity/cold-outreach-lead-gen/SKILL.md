---
name: cold-outreach-lead-gen
description: "Source, draft, send, track cold-outreach business leads."
version: 1.0.0
author: Baymax
license: MIT
metadata:
  hermes:
    tags: [leads, cold-outreach, scraping, google-maps, gmail, google-docs]
    category: productivity
    related_skills: [google-workspace, google-workspace-auth, browser-use, headless-vps-scraping-toolchain]
---

# Cold Outreach Lead Generation

End-to-end playbook for sourcing, enriching, drafting, sending, and tracking cold-outreach leads for service businesses. Each phase is a stand-alone step; run them in order or stop at any phase if you only need a partial result.

## When to use

- User asks for a list of local businesses to cold-call/email
- User wants to find businesses **without a website** in a specific niche/region
- User wants email drafts that don't sound salesy
- User wants leads tracked in a Google Sheet or Doc

## Phases

### Phase 1 — Lead source cleanup
- Drop placeholder/filler numbers (e.g. `9222 9999`, `6565 8888`, `8111 9999` are scrape-fail patterns — not real leads)
- Keep only entries with verifiable phone/email/address
- Store in `~/.hermes/projects/<project-slug>/leads.csv` per the one-folder-per-procedure rule

### Phase 2 — Multi-source enrichment
- **Google Maps** for businesses WITH Google Business Profiles (often have websites)
- **Business registries** (e.g. ACRA/RecordOwl in Singapore) for sole proprietors and unlisted businesses — these are usually the **no-website** targets. See `references/recordowl-scraping.md` for the proven free-tier extraction pattern (SSIC industry pages → company slugs → per-company SSIC/address/UEN extraction).
- Cross-reference: if Maps shows a website, mark `has_website=true`. If only registry has them, assume no-website.
- See `references/google-maps-scraping.md` for browser_exec pattern

### Phase 3 — Email drafting
- Sign-off: confirm name and brand inclusion with user **before sending** (Chris: 2026-08-17 explicitly chose "Christus Vincent" with **no brand** — first-class preference)
- Tone: conversational, low-pressure, lead with a question not a pitch
- Personalize first paragraph with company name + area
- Subject: question-led, not pitch-led ("Quick question about X's online presence")

### Phase 4 — Sending via Gmail
- Use `gws gmail send` (via `google_api.py`) from the user's account
- Send one at a time with ~15s delays — avoids spam triggers at scale
- Confirm draft content with user **before** sending the first one
- `Email Sent` / `Called` columns start as `No`, fill in after

### Phase 5 — Tracker maintenance
- **Google Sheet (NOT Doc)** for tabular lead data — Chris's 2026-08-17 preference. Columns: #, Company Name, Phone, Email, Address, Industry (SSIC), Website, Google Maps Link, Source, Email Sent, Called, Notes
- Doc only for prose-heavy outreach briefs/copy
- Save raw scraped JSON to `~/.hermes/projects/<slug>/scrape_<batch>.json`
- See `references/google-sheets-tracker.md` for the full setup (Sheets vs Docs decision, schema, push commands, phone-number formula gotcha)

## Pitfalls (from 2026-08-17 session)

1. **Maps ≠ no-website source.** 90%+ of Singapore aircon businesses on Maps already have websites. For "no-website" leads, the **business registry** is the better source. Maps is only useful as a verification layer.

2. **Headless Chrome + browser_exec needs `BU_CDP_URL`.** With `--headless=new`, Chrome does NOT write the `DevToolsActivePort` file that browser-harness auto-detects. Set env vars:
   ```bash
   export BU_CDP_URL=http://127.0.0.1:9222
   export BH_AUTOSPAWN=
   google-chrome --headless=new --disable-gpu --no-sandbox --disable-dev-shm-usage --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-harness about:blank
   ```

3. **Save after EVERY query in a scrape batch.** browser_exec connections drop mid-batch. If you save only at the end of a 30-query loop, a single timeout loses everything. Use `json.dump(all_leads, f)` after each append.

4. **Headless Chrome viewport matters.** Default is 780×437 which makes Maps show only ~5 listings per search. Resize via `cdp("Emulation.setDeviceMetricsOverride", width=1920, height=1080, ...)` at the start of the session.

5. **`page_info()[:2000]` slices — the helper returns a dict, slicing a dict raises TypeError.** Just `print(page_info())` or access fields explicitly.

6. **JS variables do NOT persist across browser_exec calls.** Variables defined in one call are gone in the next. Store state to workspace files (`/root/.hermes/cache/browser-use/workspace/<session>/`) instead.

7. **Always confirm sign-off name with user before sending emails.** Chris's 2026-08-17 correction: no brand in sign-off. Embed as a pitfall because it's a recurring preference, not a one-off.

8. **Filter emails where domain looks like a registered business domain.** If a lead's email is `info@acmeaircon.sg` rather than `acmeaircon@gmail.com`, they likely have a website at acmeaircon.sg — disqualify from "no-website" pool.

9. **Headless Chrome dies repeatedly during long scrape batches.** Symptom: `RuntimeError: no close frame received or sent` mid-batch, then harness fails every subsequent call with `fatal: chrome-not-running`. Reliable recovery sequence:
   ```bash
   pkill -9 chrome && sleep 2
   rm -rf /tmp/chrome-harness && mkdir -p /tmp/chrome-harness
   google-chrome --headless=new --disable-gpu --no-sandbox \
     --disable-dev-shm-usage --remote-debugging-port=9222 \
     --user-data-dir=/tmp/chrome-harness about:blank &
   sleep 5
   curl -s http://127.0.0.1:9222/json/version  # verify
   cat > ~/.config/google-chrome/DevToolsActivePort << 'EOF'
   9222
   /devtools/browser
   EOF
   ```
   The `DevToolsActivePort` file is what browser-harness auto-discovers; without it the harness refuses to attach even though Chrome is healthy. BU_CDP_URL env does NOT persist across `browser_exec` calls — the file is the persistent fix.

10. **Use Google Sheets, not Google Docs, for tabular lead data.** Chris's 2026-08-17 explicit redirect: "convert the google docs to google sheets, use that sheet for all the leads". Sheets handles tabular data natively (filter, sort, conditional formatting, formulas) and prevents the doc-from-getting-corrupted-as-you-append risk. See `references/google-sheets-tracker.md` for the working format.

11. **Sheets interprets phone numbers starting with `+` as formulas → `#ERROR!`.** Prefix with a leading apostrophe (`'+65 1234 5678`) before pushing via the API. The API will store it as a literal string.

12. **RecordOwl free-tier SSIC industry pages are a viable secondary source.** Each `/ssic/<category-slug>` page returns 12 company slugs (e.g. `/ssic/specialised-construction-activities` shows 12 of 114,410). Company slugs DON'T always contain "aircon" — visit each company page to extract SSIC code/industry. Filter by SSIC codes 43220 (plumbing/HVAC install), 43210 (electrical works), 43301 (renovation contractors), 95220 (household goods repair), 81211 (general cleaning incl aircon). See `references/recordowl-scraping.md` for the working extraction JS.

13. **Chain-exclusion list for Maps no-website results.** Big operators show up as "no-website" on Maps (their Google listing exists but they push customers to phone/WhatsApp). When filtering, exclude slug-name matches for: gain city, midea, york, sharp (singapore electronics/service center), sommerville, claymore, new york air-conditioning, general electric international, tomika. Verify each exclusion against the Maps listing — sometimes legitimate small operators share names.

## Verification checklist (end-to-end)

Before declaring a lead-gen run complete:
- [ ] CSV/Doc has columns matching user's brief (name, phone, email, Maps link, etc.)
- [ ] Each row has at least ONE verified contact (phone OR email)
- [ ] No-website filter applied (website column empty or marked `None`)
- [ ] User sign-off name confirmed and embedded in drafts
- [ ] Tracker opened in browser, visually inspected

## References

- `references/google-maps-scraping.md` — Maps extraction patterns, query lists, viewport config
- `references/recordowl-scraping.md` — RecordOwl free-tier SSIC industry pages, per-company extraction JS, SSIC-code filter pattern
- `references/email-drafts-tone.md` — non-salesy cold email templates and tone guide
- `references/google-sheets-tracker.md` — Sheets vs Docs decision, schema, push commands, phone-number formula gotcha
- `templates/leads.csv` — starter CSV with header row matching this skill's tracker format

## Related skills

- `google-workspace` — Gmail send, Docs create/append
- `google-workspace-auth` — OAuth2 setup for madeat2am.ai@gmail.com
- `browser-use` (CLI/skill) — browser_exec tool
- `headless-vps-scraping-toolchain` — broader scraping infrastructure on VPS