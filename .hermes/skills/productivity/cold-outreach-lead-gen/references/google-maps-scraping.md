# Google Maps Lead Scraping — Reference

Proven pattern from 2026-08-17 session. Use as a starting point for niche + region lead scraping via browser_exec.

## Chrome setup (REQUIRED)

```bash
# Headless=new does NOT write DevToolsActivePort — harness can't auto-detect.
# Must set BU_CDP_URL explicitly.
export BU_CDP_URL=http://127.0.0.1:9222
export BH_AUTOSPAWN=
google-chrome --headless=new --disable-gpu --no-sandbox \
  --disable-dev-shm-usage \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-harness \
  about:blank &
```

## Browser session setup

```python
# Inside browser_exec — first call after Chrome is up:
cdp("Emulation.setDeviceMetricsOverride", width=1920, height=1080,
    deviceScaleFactor=1, mobile=False)
```

Default viewport 780×437 makes Maps show only ~5 listings. 1920×1080 shows 20-40.

## Query generation

Build queries along two axes:
- **Service type**: `<service> Singapore`, `<service> repair`, `<service> installation`, `<service> contractor`, `<service> maintenance`, `<service> technician`, `<service> chemical wash`, `HVAC Singapore`
- **Region**: `<service> <area>` where area is a Singapore planning area (Tampines, Jurong East/West, Woodlands, Bedok, Hougang, Punggol, Toa Payoh, Choa Chu Kang, Yishun, Ang Mo Kio, Bukit Batok, Bukit Merah, Clementi, Sengkang, Serangoon, Pasir Ris, Sembawang, Bukit Panjang, Geylang, Marine Parade, Kallang, Queenstown, Bukit Timah, Tiong Bahru)

50–60 unique queries gives good coverage of a niche in Singapore.

## Extraction script (per query)

```python
EXTRACT_JS = '''
(() => {
  const feed = document.querySelector('[role="feed"]');
  if (!feed) return [];
  const items = [];
  Array.from(feed.children).forEach((item) => {
    const text = item.textContent || "";
    if (text.length < 50) return;
    if (!text.match(/\\+65/)) return;
    const nameEl = item.querySelector('.qBF1Pd, .fontHeadlineSmall');
    const name = nameEl ? nameEl.textContent.trim() : null;
    if (!name) return;
    const phoneMatch = text.match(/\\+65[\\s\\d]{8,}/);
    const phone = phoneMatch ? phoneMatch[0].trim() : null;
    const anchors = Array.from(item.querySelectorAll('a[href^="http"]'));
    const externalLinks = anchors
      .map(a => a.href)
      .filter(h => !h.includes('google.com') && !h.includes('gstatic.com') &&
                   !h.includes('youtube.com') && !h.includes('schema.org'));
    const hasWebsite = externalLinks.length > 0;
    const website = externalLinks[0] || null;
    const linkEl = item.querySelector('a[href*="/maps/place/"]');
    const mapsUrl = linkEl ? linkEl.href : null;
    if (name && phone) items.push({name, phone, hasWebsite, website, mapsUrl});
  });
  return items;
})()
'''

SCROLL_JS = '''
(() => {
  const feed = document.querySelector('[role="feed"]');
  if (feed) feed.scrollTop = feed.scrollHeight;
})()
'''
```

## Loop pattern

```python
import time, json
all_leads = []
seen = set()  # dedupe by lower(name)

for q in queries:
    new_tab(f"https://www.google.com/maps/search/{q}/")
    wait_for_load()
    time.sleep(2.5)  # Maps render time
    
    for _ in range(3):
        js(SCROLL_JS)
        time.sleep(1.0)
    
    listings = js(EXTRACT_JS)
    for L in listings:
        if L['name'].lower() not in seen:
            seen.add(L['name'].lower())
            L['query'] = q
            all_leads.append(L)
    
    # CRITICAL: save after every query (see Pitfalls)
    with open("/path/to/scrape.json", "w") as f:
        json.dump(all_leads, f)
```

## Cleanup heuristics

Drop these patterns from scraped listings — they're scrape-fail fillers, not real numbers:
- `9222 9999`, `6565 8888`, `6288 5555`, `8111 9999`, `6896 1234`, `9856 7777`, `6555 8888`
- Any number with all-identical repeated digits
- Phone numbers that don't match SG format `\+?65?[689]\d{7}` or `[689]\d{7}`

Keep:
- Numbers matching SG mobile (`[89]\d{7}`) or landline (`6\d{7}`) formats
- Emails on `@gmail.com`, `@yahoo.com`, `@hotmail.com` (personal — likely no business site)
- Emails on custom business domains (e.g. `@acmeaircon.sg`) — flag these as "likely has website", disqualify from no-website pool

## Pitfalls specific to Maps scraping

1. **Maps shows what businesses WANT you to see.** Most have websites, social profiles, hours, photos. The targets (no-website sole props) usually don't have a Maps listing at all.
2. **Cloudflare-blocked sources.** sgpbusiness.com and sg.ltddir.com are blocked by Cloudflare on every request — don't bother.
3. **Cloudflare-protected directory pages** (hvacinformed.com) return a captcha wall — can't scrape directly.
4. **The Maps sidebar scrolls lazily.** Each `scrollTop = scrollHeight` adds ~5-10 more items. 3 scrolls per query is a good balance.

## When Maps is the wrong tool

If the user's goal is "find businesses WITHOUT a website":
- Maps shows ~10% no-website rate (the polished operators self-select into Maps)
- Business registries (ACRA Singapore, Companies House UK, Secretary of State filings US) show ~50% no-website rate
- Use Maps as a verification layer, not the primary source

## Connection resilience

- Connections drop mid-batch. Save after every iteration (see loop pattern above).
- If you see `RuntimeError: no close frame received or sent`, Chrome is still alive but the harness can't reach it. Restart Chrome and the harness subprocess will reconnect on next call.
- 300s timeout is the cap per browser_exec call. For 60-query batches split into 10-query chunks.