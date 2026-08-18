# Google Maps bulk scrape from a headless Chrome session

Concrete patterns for extracting many business listings from
`google.com/maps/search/...` via the `browser_exec` tool, plus the
headless-Chrome connection fixes that make long-running scrape jobs
survive more than ~30 queries.

## The extraction pattern

The Maps results page renders a scrollable list inside a
`role="feed"` container. Each card is a child of that feed. The
business name sits inside `.qBF1Pd` or `.fontHeadlineSmall`, the phone
number appears in the card's textContent as a `+65 XXXX XXXX` token,
and the website is the first non-Google external anchor.

```python
EXTRACT_JS = r'''
(() => {
  const feed = document.querySelector('[role="feed"]');
  if (!feed) return [];
  const items = [];
  Array.from(feed.children).forEach((item) => {
    const text = item.textContent || "";
    if (text.length < 50) return;
    if (!text.match(/\+65/)) return;
    const nameEl = item.querySelector('.qBF1Pd, .fontHeadlineSmall');
    const name = nameEl ? nameEl.textContent.trim() : null;
    if (!name) return;
    const phoneMatch = text.match(/\+65[\s\d]{8,}/);
    const phone = phoneMatch ? phoneMatch[0].trim() : null;
    const anchors = Array.from(item.querySelectorAll('a[href^="http"]'));
    const externalLinks = anchors
      .map(a => a.href)
      .filter(h => !h.includes('google.com')
                && !h.includes('gstatic.com')
                && !h.includes('youtube.com')
                && !h.includes('schema.org'));
    const hasWebsite = externalLinks.length > 0;
    const website = externalLinks[0] || null;
    const linkEl = item.querySelector('a[href*="/maps/place/"]');
    const mapsUrl = linkEl ? linkEl.href : null;
    if (name && phone) {
      items.push({ name, phone, hasWebsite, website, mapsUrl });
    }
  });
  return items;
})()
'''

SCROLL_JS = r'''
(() => {
  const feed = document.querySelector('[role="feed"]');
  if (feed) feed.scrollTop = feed.scrollHeight;
})()
'''
```

Usage inside a `browser_exec` call:

```python
new_tab(f"https://www.google.com/maps/search/{query}/")
wait_for_load()
import time; time.sleep(2.5)         # let results render
for _ in range(3):
    js(SCROLL_JS)
    time.sleep(1.0)                  # virtualised scroll - 1s per scroll
listings = js(EXTRACT_JS)
```

Notes:
- The first card in a feed is usually an ad or sponsored slot
  (no `+65` token). The `+65` filter naturally drops those.
- The headless viewport defaults to ~780×437. Use
  `cdp("Emulation.setDeviceMetricsOverride", width=1920, height=1080,
  deviceScaleFactor=1, mobile=False)` at the start of the session —
  Maps shows ~36 listings instead of ~5 at 1920×1080.
- Each Maps search returns the same handful of businesses for the
  top of the result set. The dedupe key must be
  `name.lower().strip()` — phone is not unique across listings.
- One search yields 20–40 listings with phones, of which roughly
  2–6 are no-website businesses in a saturated market like Singapore
  aircon servicing. Plan for ~5% no-website yield when sizing
  queries for a target lead count.

## The headless Chrome connection problem

`browser_exec` shells out to the `browser-harness` binary, which
probes Chrome by reading
`/root/.config/google-chrome/DevToolsActivePort` and trying to
connect to whatever port is on the first line. Two failure modes:

### Mode 1: `headless=new` Chrome writes nothing to that path

When you launch Chrome with
`google-chrome --headless=new --remote-debugging-port=9222
--user-data-dir=/root/.config/google-chrome`, Chrome 147+ does
**not** write `DevToolsActivePort`. The probe returns empty and
the harness fails with:

```
browser-harness: Chrome isn't running — launching it.
browser-harness: fatal: chrome-not-running: no supported
  Chromium-family browser is running -- start Chrome, then retry
```

**Fix:** write the marker file manually before the first
`browser_exec` call:

```bash
cat > /root/.config/google-chrome/DevToolsActivePort << 'EOF'
9222
/devtools/browser
EOF
```

The two lines are: port number, then the WebSocket path Chrome
exposes on `/json/version`. Both are stable for a given Chrome
build. After writing the marker, `browser_exec` connects on the
next call and stays connected.

### Mode 2: Chrome dies mid-batch with "no close frame" / RuntimeError

Long scrape loops that open dozens of `new_tab` calls eventually
trigger the Chrome remote-debugging WebSocket to drop with
`no close frame received or sent`. This is not a Maps rate-limit
problem — Chrome itself has lost the harness connection.

**Fix:** restart Chrome between batches (~30 queries max per batch).
The full reset cycle takes ~10 seconds:

```bash
pkill -9 chrome 2>/dev/null; sleep 2
google-chrome --headless=new --disable-gpu --no-sandbox \
  --disable-dev-shm-usage \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-harness about:blank &
sleep 5
cat > /root/.config/google-chrome/DevToolsActivePort << 'EOF'
9222
/devtools/browser
EOF
```

Then `browser_exec` reconnects on the next call.

### Mode 3 (alternative): bypass the file probe entirely with BU_CDP_URL

Setting `BU_CDP_URL=http://127.0.0.1:9222` makes the harness skip
the `DevToolsActivePort` file check and connect directly to the
remote-debugging port. This works in shell, but **does not
propagate to the `browser_exec` tool** — each tool call spawns a
fresh subprocess without the env var. The DevToolsActivePort file
fix is the durable workaround.

## Saving scrape progress so a crash doesn't lose data

When the connection dies mid-batch, anything in `all_leads` that
hasn't been written to a file is lost. Save to a workspace file
**every N queries**, not at the end:

```python
SAVE_PATH = "/root/.hermes/projects/<project>/scrape.json"
for qi, q in enumerate(queries):
    # ... run query, accumulate into all_leads ...
    if qi % 5 == 0:
        with open(SAVE_PATH, "w") as f:
            json.dump(all_leads, f, indent=2)
```

Then on the next call, resume with:

```python
all_leads = json.load(open(SAVE_PATH))
seen = {(l.get("name") or "").lower().strip(): True for l in all_leads}
```

This pattern is what kept a 200-query Singapore aircon scrape from
zero across five Chrome crashes — partial results survived each
crash and the next batch picked up where the last left off.

## Anti-patterns

- **Don't** trust `time.sleep(N)` alone to load Maps results. The
  feed loads incrementally — scroll the inner container with
  `feed.scrollTop = feed.scrollHeight` to force lazy-load.
- **Don't** filter by `item.querySelector('.qBF1Pd')` only. Some
  cards use `.fontHeadlineSmall` instead. Match both.
- **Don't** detect "has website" by checking for the literal word
  `Website` in the textContent. Every listing shows that label
  regardless of whether they actually have a site. Filter
  `externalLinks` by hostname, not label.
- **Don't** write a single `browser_exec` call with more than ~30
  queries. Even with the save-progress pattern, Chrome will die
  around query 30–40 in a saturating scrape. Batch smaller.