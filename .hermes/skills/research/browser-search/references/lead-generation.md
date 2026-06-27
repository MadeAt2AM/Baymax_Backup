# Lead Generation / Web Scraping Findings (June 2026)

## What Works — Primary Sources

**RecordOwl (recordowl.com) — BEST for SG business leads**
- Returns company name, phone, email, registered address, AND whether they have a website
- Directly browseable via Camofox — no bot protection encountered
- URL pattern: `https://recordowl.com/company/<slug>`
- Search: `site:recordowl.com aircon Singapore` via SearXNG, then browse individual pages
- Each page shows: UEN, status (Live/Ceased), age, contact number, email, website presence, address, BCA licenses
- Key for lead gen: companies with NO website link in their RecordOwl entry = high-priority cold call targets

**sg.ltddir.com** — Singapore business directory, directly browseable
- Example: `https://sg.ltddir.com/companies/jas-aircon-services-2/`

**SethLui / Yahoo / blog articles** — public articles listing aircon companies with locations
- Scrape for company names, then verify details on RecordOwl

## What Doesn't Work — Blocked Platforms

| Platform | Blocker | Alternative |
|---|---|---|
| Carousell | Cloudflare / anti-bot | RecordOwl, Carousell API (official) |
| HardwareZone Forums | Login required | Reddit r/askSingapore (public) |
| Yelp | Bot protection on all pages | RecordOwl for basic data |
| Facebook | Extensive bot/fingerprinting | Carousell listings, forums |
| HVAC Informed | hCaptcha / Imperva | RecordOwl, sg.ltddir.com |
| Scribd | Login/paywall for PDFs | Use RecordOwl instead |
| Google Maps | Requires scraping API | RecordOwl (maps addresses are listed) |

## Proven Lead Gen Workflow

1. **Search**: `site:recordowl.com aircon Singapore` via SearXNG
2. **Browse**: Individual RecordOwl pages via `browser_navigate`
3. **Extract**: phone, email, address, website presence per company
4. **Filter**: Prioritize companies with NO website link listed
5. **Save**: Compile to text file, send via `hermes send --to telegram --file /path.txt --subject "Subject"`

## Camofox Tab Timing

- Create tab → wait ~8 seconds → snapshot. Don't poll in a loop — just wait once then snapshot.
- JSON snapshot output can be parsed with jq:
  ```
  jq -r '.. | objects | select(.text and (.text | test("^[89]\\d{7}"))) | .text'
  ```

## Telegram File Delivery

```bash
hermes send --to telegram --file /root/leads.txt --subject "🧊 Subject Here"
```
File content becomes the message body. Subject line is prepended as a header.
