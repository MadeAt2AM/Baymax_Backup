---
name: calendar-integration
title: Calendar Integration via webcal:// Deep Links
description: Enables native calendar app integration through webcal:// deep-links and iCalendar feeds with cross-platform fallbacks for scheduling applications
type: devops
tags: ["calendar", "webcal", "ics", "deeplink", "apple-calendar", "google-calendar", "outlook", "android"]
related_skills: []
---

## Overview

SYNTRA's "Add to Calendar" feature uses webcal:// URL scheme to launch native calendar apps directly, avoiding the download workflow. Falls back gracefully for Windows/Linux users without webcal:// handlers.

## When to Use

- User clicks "Add to Calendar" in schedule view
- Calendar apps need to sync shifts via recurring .ics feed pulls
- Supporting Apple Calendar, Google Calendar, Outlook, and Android Calendar apps

## Implementation

### Backend
- `artifacts/api-server/src/routes/calendar.ts` - Token mint/revoke + .ics feed
- `artifacts/api-server/src/lib/ical.ts` - RFC 5545 generator with proper escaping
- Schema: `webcal_token` + `webcal_token_created_at` columns on `users` table

### Frontend
- `artifacts/web-app/src/lib/calendar-deeplink.ts` - Token caching + deep-link logic
- `artifacts/web-app/src/pages/schedule.tsx` - Button wired to `openNativeCalendar()`

## Deep-Link Strategy Matrix

| Platform | Primary Strategy | Fallback |
|----------|------------------|----------|
| iOS / macOS | webcal:// native scheme | https:// inline rendering |
| Android | webcal:// native scheme | https:// inline rendering |
| Windows / Linux | https:// inline .ics | Google Calendar import |
| No handler | https:// render as text | Google Calendar import (/calendar/render?cid=) |

## Token Lifecycle

1. **Mint:** POST /api/calendar/token (Bearer auth) → returns opaque UUID
2. **Serve:** GET /api/calendar/shifts.ics?token=... → webcal-authenticated feed
3. **Revoke:** DELETE /api/calendar/token → clears token access
4. **Cache:** Token stored in localStorage (syntra.webcalToken) to avoid re-minting

## Verification Checklist

- [ ] Typecheck passes (pnpm run typecheck)
- [ ] API builds successfully
- [ ] Live endpoint returns valid VCALENDAR with text/calendar Content-Type
- [ ] Content-Disposition: inline (not attachment)
- [ ] Deep-link flow works on target platforms

## Pitfalls

- **Time zone handling:** Always convert to UTC for DTSTART/DTEND
- **Null safety:** Left-joined columns may be null despite DB NOT NULL - use ?? undefined
- **Token persistence:** Cache token in localStorage to avoid unnecessary minting
- **Fallback UX:** If webcal:// fails, show indication and offer Google Calendar import
- **Scope privacy:** Company-scope exposes all shifts - restrict to manager/admin roles
- **Line endings:** iCalendar requires CRLF (\r\n) not LF (\n)

## References

- RFC 5545: Internet Calendaring and Scheduling Core Object Specification
- Apple Developer: Registering Custom URL Schemes
- Google Calendar API: Adding calendars by URL