---
name: webcal-deeplink-subscribe
description: "Use when a web app needs an 'Add to Calendar' or 'Subscribe' button that opens the user's NATIVE calendar app instead of downloading an .ics file. Covers the webcal:// URL scheme, server-side .ics endpoints with token-in-query auth, RFC 5545 generation, Content-Disposition: inline, and the platform deep-link matrix (iOS/macOS/Android vs Windows/Linux). Trigger on 'add to calendar', 'subscribe to calendar', 'ical deep link', 'webcal://', '.ics opens in calendar app', 'iCal subscription URL', 'Outlook calendar subscribe', 'Google Calendar subscribe'."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [calendar, ical, webcal, deeplink, subscriptions, frontend, backend]
    related_skills: [vps-container-deploy, security-hardening-web-stack, hermes-agent-skill-authoring]
---

# Add-to-Calendar Deep-Linking (webcal:// + .ics subscription)

## Overview

The naive "Add to Calendar" button creates a Blob from an `.ics` string and triggers a download. That lands in the user's Downloads folder and they have to manually open it in a calendar app. Useless on mobile, painful on desktop.

The correct pattern: serve the `.ics` over HTTP with the right MIME type and auth, then deep-link the OS calendar handler via the `webcal://` URL scheme. Every Apple device, every Android device with Google Calendar installed, and most macOS apps recognize `webcal://`. Desktop Windows / Linux fall back to the `https://` form, which renders inline thanks to `Content-Disposition: inline` + `Content-Type: text/calendar`.

The trick: **token-in-query-string** instead of Bearer header. Calendar apps re-fetch the subscription URL on every sync — they have no way to carry a header. Treat the token like a credential (revocable, scoped to one user, never logged).

## When to Use

Use when:

- A web app exposes user-owned event data (shifts, bookings, reservations, classes, deadlines, payroll dates)
- The user expects to see those events in their system calendar app, not just in the app's UI
- "Sync to calendar" or "Add to my calendar" is a requested feature
- The deployment can host a public-by-token HTTP endpoint

Do NOT use when:

- The data is highly sensitive and the subscription URL might be shared accidentally — calendar apps may sync to other devices the user didn't intend
- The event data is so volatile that calendar-app polling (every few hours) would mislead users
- You only need a one-time import — use a plain `.ics` download or the Google Calendar "import by URL" flow

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Client (web app)                                                │
│                                                                  │
│   1. Click "Add to Calendar"                                     │
│   2. POST /api/calendar/token (Bearer auth) → mint/return token  │
│   3. Build: webcal://<host>/api/calendar/feed.ics?token=<tok>    │
│   4. window.location.assign(webcalUrl)  ← native handoff         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │ (deep-link, no HTTP)
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  OS Calendar Handler (Apple Calendar, Google Calendar, Outlook)  │
│                                                                  │
│   - Opens URL, fetches the .ics via HTTP                         │
│   - Subscribes; re-syncs on a schedule (15min–24h)               │
│   - Token in query string IS the credential                      │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Server                                                          │
│                                                                  │
│   GET /api/calendar/feed.ics?token=<token>[&scope=mine|company]  │
│   - Lookup user by token (NOT by Bearer)                         │
│   - Filter: published/active events only — never leak drafts     │
│   - Generate RFC 5545 VCALENDAR server-side                      │
│   - Response:                                                    │
│       Content-Type: text/calendar; charset=utf-8                 │
│       Content-Disposition: inline; filename="..."                │
│       Cache-Control: no-store                                    │
└──────────────────────────────────────────────────────────────────┘
```

## Critical Implementation Details

### 1. The `Content-Disposition: inline` trick

Most tutorials get this wrong — they serve `.ics` with `Content-Disposition: attachment`, which forces browsers to download. The fix:

```ts
res.set({
  "Content-Type": "text/calendar; charset=utf-8",
  "Content-Disposition": `inline; filename="feed-${userId}.ics"`, // ← inline, NOT attachment
  "Cache-Control": "no-store",
});
```

`inline` lets the browser either render or hand off to a registered handler. Browsers without a calendar handler render the raw `.ics` text — not pretty, but not broken, and the user can save/copy.

### 2. Token-in-query authentication

Calendar apps can't send a Bearer header. Two acceptable patterns:

**A. Long-lived opaque token** (recommended): UUID stored in the `users` table. Minted on first click. Cached client-side in `localStorage` so subsequent clicks skip the round-trip. Revocable via DELETE endpoint.

**B. Short-lived signed token** (Google-style): a JWT with 1-year expiry baked into the URL. Easier to revoke (rotate secret) but you can't scope-revoke individual users.

```ts
function mintWebcalToken(): string {
  return crypto.randomUUID(); // 122 bits of entropy, URL-safe
}
```

Store in a dedicated column (`webcal_token` + `webcal_token_created_at`). Index it later if it becomes a hot lookup.

### 3. RFC 5545 server-side generator

Single source of truth — don't fork logic between client Blob downloads and server responses.

Required:
- CRLF line endings (`\r\n`), not `\n`
- Lines folded at 75 octets with CRLF + single-space continuation
- `DTSTART`/`DTEND`/`DTSTAMP` in UTC with `Z` suffix (basic format: `20240101T090000Z`)
- Escape `\` `;` `,` and newlines in TEXT values
- Stable, deterministic `UID` per event so calendar apps dedupe across syncs: `UID:appname-event-<id>@<host>` — the `@<host>` part matters for iCloud etc.
- `METHOD:PUBLISH` for read-only subscriptions

Optional but recommended:
- `X-WR-CALNAME:<display name>` so the calendar is labelled in the user's app
- `X-WR-TIMEZONE:UTC` if all your events are in UTC (otherwise omit and let the app use its default)

### 4. Platform deep-link matrix

| Platform | Primary path | Fallback |
|---|---|---|
| iOS / iPadOS | `webcal://` | App share sheet → Save to Calendar |
| macOS | `webcal://` | `https://` (Calendar.app registers handler) |
| Android | `webcal://` | Google Calendar import-by-URL |
| Windows | `https://` (rendered inline → Outlook if installed) | Google Calendar import-by-URL |
| Linux | `https://` (rarely registered handler) | Google Calendar import-by-URL |

Frontend decision tree:

```
try webcal:// deep-link first
   ↓ (success: OS handed off — no way to detect, just trust)
   ↓ (failure or no registered handler)
if (Windows || Linux) → open https:// URL in new tab
else → open Google Calendar import-by-URL with the https URL
```

Last-resort: trigger a one-shot Blob download (preserves the original behavior). Never let the user be left with NO option.

### 5. Security considerations

- **Treat the token like a password.** Never log it. Never include in URLs that get cached by intermediate proxies. Long-lived = long-lived. 1-year minimum.
- **Filter the response aggressively.** Only return `status = published` (or equivalent). Drafts and unannounced data must NEVER reach a calendar app — users share those URLs with family.
- **Tenant scoping.** Filter by `company_id` (or equivalent). Don't leak cross-tenant data through subscription URLs.
- **Role gating on `scope=company`.** If you support a "company-wide" calendar feed, gate it behind manager/admin role.
- **Revocation.** Provide a DELETE endpoint. After call, the subscription URL returns 401 on next sync and the calendar app eventually removes the events.
- **CORS open is OK** for the `.ics` endpoint specifically (calendar apps fetch from native code, not browser XHR). The token IS the auth. Don't preflight this.

## Minimal Server Implementation

```ts
// Express example
router.get("/feed.ics", async (req, res) => {
  const token = String(req.query.token ?? "");
  if (!token) return res.status(401).type("text/plain").send("Missing token");

  const [user] = await db.select(/*...*/).from(users).where(eq(users.webcalToken, token)).limit(1);
  if (!user || user.status !== "active") return res.status(401).send("Invalid token");

  const events = await fetchEventsForUser(user); // only published, only tenant-scoped
  const ical = generateIcal(events, "My Calendar Name");

  res.status(200).set({
    "Content-Type": "text/calendar; charset=utf-8",
    "Content-Disposition": `inline; filename="feed-${user.id}.ics"`,
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-store",
  }).send(ical);
});

router.post("/token", requireAuth, async (req, res) => {
  // Mint or return existing token for the authenticated user
});

router.delete("/token", requireAuth, async (req, res) => {
  // Revoke
});
```

## Minimal Client Implementation

```ts
async function openNativeCalendar() {
  const token = await getOrMintToken();
  const httpsUrl = `${window.location.origin}/api/calendar/feed.ics?token=${encodeURIComponent(token)}`;
  const webcalUrl = httpsUrl.replace(/^https?:/, "webcal:");

  // Strategy 1: native deep-link (iOS/macOS/Android)
  if (tryWebcalDeepLink(webcalUrl)) return;

  // Strategy 2: open HTTPS — browser renders inline, OS picks up handler
  if (isWinOrLinux) return openInNewTab(httpsUrl);

  // Strategy 3: Google Calendar import — guaranteed path
  openInNewTab(`https://calendar.google.com/calendar/render?cid=${encodeURIComponent(httpsUrl)}`);
}
```

## Common Pitfalls

1. **Serving `.ics` as `Content-Disposition: attachment`.** Forces a download instead of native handoff. Use `inline`.
2. **Using Bearer auth on the subscription URL.** Calendar apps can't carry headers. Use token-in-query.
3. **Generating `.ics` with `\n` instead of `\r\n`.** Some parsers (Outlook, older Apple Calendar) reject it.
4. **Forgetting line folding.** Lines > 75 octets without CRLF + single-space continuation break older parsers.
5. **Putting PII (employee name, email) in the event SUMMARY or DESCRIPTION.** Calendar apps sync to other devices — keep it generic.
6. **Not filtering by `status = published`.** Drafts leak. Always filter at the server.
7. **Trusting `window.location.assign(webcalUrl)` to fail loudly.** It silently no-ops if no handler is registered. Always provide a visible fallback path in the UI (toast message, "didn't open? try this link").
8. **Logging the token.** Pino serializers MUST drop query strings for this endpoint, or you'll have credentials in your log files.
9. **Caching the `.ics` response aggressively.** Shift changes need to reflect on next sync. Use `Cache-Control: no-store` or very short max-age.
10. **Token rotation logic that invalidates all subscriptions at once.** If a user signs out and back in, preserve the existing token; only mint a new one on explicit revoke.

## Verification Checklist

After implementing, verify:

- [ ] `curl https://host/api/calendar/feed.ics?token=<token>` returns 200 with `Content-Type: text/calendar; charset=utf-8`
- [ ] Response `Content-Disposition` header starts with `inline` (not `attachment`)
- [ ] Body starts with `BEGIN:VCALENDAR\r\n` and ends with `END:VCALENDAR\r\n`
- [ ] `DTSTART` / `DTEND` use UTC `Z` suffix
- [ ] No draft / unpublished events in the response
- [ ] Token-revoked request returns 401
- [ ] `webcal://` URL is well-formed (origin swapped, query preserved)
- [ ] On mobile: clicking the button leaves the browser and opens the calendar app
- [ ] On desktop Win/Linux: clicking opens a new tab with the `.ics` rendered inline
- [ ] Rate limiter doesn't block calendar app polling (it'll hit the URL many times per day)
- [ ] No token in server access logs (Pino serializer strips query string)

## One-Shot Recipe: Add to Existing App

1. Add `webcal_token TEXT` + `webcal_token_created_at TIMESTAMP` columns to your `users` table.
2. Drop `lib/ical.ts` (RFC 5545 generator) into your server project — keep CRLF + line folding.
3. Add three routes: `POST /calendar/token`, `DELETE /calendar/token`, `GET /calendar/feed.ics?token=...`.
4. Frontend: `openNativeCalendar()` helper that mints token (cached), tries `webcal://`, then falls back.
5. Wire your existing "Add to Calendar" button to the helper instead of the Blob download.
6. Verify with `curl` + a real device (deep-link behavior must be tested on a phone, not just a desktop browser).

## Related Skills

- `vps-container-deploy` — for setting up the HTTPS reverse proxy that serves the `.ics` endpoint with proper TLS (calendar apps refuse non-HTTPS `webcal://` URLs)
- `security-hardening-web-stack` — for ensuring the new public-by-token endpoint doesn't expand your CORS / auth attack surface more than necessary
