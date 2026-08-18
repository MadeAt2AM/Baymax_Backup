# RecordOwl Scraping — Reference

Proven pattern from 2026-08-17 session for Singapore business-registry scraping. RecordOwl is a free-tier directory that mirrors ACRA registrations and shows 12 companies per SSIC industry page.

## When to use

- Maps yield too low (most Singapore businesses with Maps presence already have websites — only ~10-18% are no-website)
- Need sole proprietors / unlisted operators that never bothered with Google Business Profile
- Have access to UEN, registered address, SSIC industry classification as primary fields (phone is paywalled)

## SSIC industry pages to target for aircon/HVAC

These pages return 12 companies each and contain aircon-relevant businesses:

| URL | Why it matters |
|---|---|
| `/ssic/specialised-construction-activities` | Catches sole-prop aircon contractors; SSIC 43301 subcategory |
| `/ssic/electricity-plumbing-and-construction-installation-activities` | SSIC 43220 (plumbing, heat, aircon install) directly |
| `/ssic/building-completion-and-finishing` | Renovation contractors who do aircon install as part of fit-outs |
| `/ssic/other-specialised-construction-activities` | Catch-all for general contractors with aircon work |
| `/ssic/cleaning-and-landscape-maintenance-activities` | Cleaning firms that do aircon chemical wash (SSIC 81211) |
| `/ssic/civil-engineering` | Some civil firms subcontract aircon |

Each page renders 12 of N companies. Free tier blocks pagination past page 1 (`?page=2` → 302 back to page 1). The paywall says "Page 1 of 141,244 is available to guests" — so don't waste time trying to paginate.

## Step 1 — Collect company slugs from each industry page

```python
EXTRACT_JS = '''
(() => {
  const links = Array.from(document.querySelectorAll('a[href*="/company/"]'));
  return links
    .map(a => a.href)
    .filter(h => /\\/company\\/[a-z0-9-]+/.test(h))
    .map(h => {
      const m = h.match(/\\/company\\/([a-z0-9-]+)/);
      return m ? m[1] : null;
    })
    .filter(s => s);
})()
'''
```

Loop over the 6 industry pages, dedupe by slug, save slugs to `ro_companies.json`.

## Step 2 — Visit each company page to extract details

RecordOwl company pages are reliably scannable (HTTP 200, ~111KB, no bot protection beyond Cloudflare basic).

```python
EXTRACT_JS = '''
(() => {
  const text = document.body.innerText;
  const h1 = document.querySelector('h1');
  const name = h1 ? h1.textContent.trim() : null;
  const phoneMatch = text.match(/Contact Number\\s*([0-9 ]{8,})/);
  const phone = phoneMatch ? phoneMatch[1].trim() : null;
  const addrMatch = text.match(/Registered Address\\s*([^\\n]+(?:\\n[^\\n]+)?)/);
  const address = addrMatch ? addrMatch[1].replace(/\\n/g, ', ').trim() : null;
  const ssicMatch = text.match(/Primary SSIC Code\\s*(\\d{4,5})/);
  const primarySSIC = ssicMatch ? ssicMatch[1] : null;
  const industryMatch = text.match(/Primary Industry\\s*([^\\n]+)/);
  const industry = industryMatch ? industryMatch[1].trim() : null;
  const secSSIC = text.match(/Secondary SSIC Code\\s*(\\d{4,5})/);
  const secondarySSIC = secSSIC ? secSSIC[1] : null;
  const secInd = text.match(/Secondary Industry\\s*([^\\n]+)/);
  const secondaryIndustry = secInd ? secInd[1].trim() : null;
  const uenMatch = text.match(/Registration Number\\s*([A-Z0-9]+)/);
  const uen = uenMatch ? uenMatch[1] : null;
  return { name, phone, address, primarySSIC, industry, secondarySSIC, secondaryIndustry, uen };
})()
'''
```

## Step 3 — Filter for aircon-relevant businesses

Slugs DON'T always include "aircon" — must filter by SSIC code or industry text:

```python
AIRCON_SSIC = {'43220', '43210', '43301', '95220', '81211'}
AIRCON_KEYWORDS = ['aircon', 'air-con', 'air conditioning', 'hvac',
                   'cooling', 'refrigeration', 'heat and air', 'plumbing, heat']

def is_aircon(detail):
    if detail.get('primarySSIC') in AIRCON_SSIC: return True
    if detail.get('secondarySSIC') in AIRCON_SSIC: return True
    combined = (detail.get('industry', '') + ' ' + detail.get('secondaryIndustry', '')).lower()
    return any(k in combined for k in AIRCON_KEYWORDS)
```

## What you get vs what you don't

| Field | Available? | Notes |
|---|---|---|
| Company name | ✅ | h1 of company page |
| UEN | ✅ | "Registration Number" |
| Registered address | ✅ | "Registered Address" |
| Primary SSIC code + industry | ✅ | Free tier |
| Secondary SSIC code + industry | ✅ | Free tier |
| Phone number | ❌ | Paywalled — shows "Not listed on RecordOwl" for sole props |
| Email | ❌ | Not shown at all |
| Google Maps link | ❌ | Must cross-reference manually |

**Workaround for missing phones**: Use ACRA BizFile (https://www.bizfile.gov.sg) directly with the UEN — registered SSIC, address, and sometimes directors' contacts are public. Or call the company at their registered address and ask.

## Pitfalls

1. **Cloudflare blocks the search endpoint by IP** — `/search?q=aircon` returns 200 but content is just the marketing landing page (no actual results). Don't waste time on search.
2. **Free-tier pagination is hard-blocked** — `?page=2` returns 302 to page 1. The only way to get more than 12 companies per SSIC category is paid subscription.
3. **SSIC code URLs like `/ssic/43220` return 404** — must use the named slug `/ssic/specialised-construction-activities`.
4. **Some companies are duplicates across industry pages** — dedupe by slug before extracting details.
5. **Phone is paywalled** — assume you get name, address, SSIC only. Plan to enrich with phone via other channels (Maps at the address, ACRA BizFile, Yellow Pages, manual call).
6. **The 6 industry pages above return ~60 unique companies, ~25-30 aircon-relevant after filtering** — enough for a useful batch but not a flood. Combine with Maps leads for a complete picture.

## What this gets you

A different lead type than Maps:
- **Maps leads**: businesses with a Google presence, polished, often have websites
- **RecordOwl leads**: sole proprietors + small Pte Ltds that registered with ACRA but don't bother with Google. They're the genuine "no-website" targets.

Combined approach: ~60-100 leads per run, mix of both types, each row tells you the source so you know the lead quality.