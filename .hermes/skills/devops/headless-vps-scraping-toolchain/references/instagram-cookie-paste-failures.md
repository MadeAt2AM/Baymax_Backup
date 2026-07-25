# Instagram cookie-paste failures — the things the dashboard won't tell you

Reference for when the in-dashboard `InstagramAuthBanner` paste form
returns a generic "unauthorized" or surfaces an Instagram-side error
like **"token invalid or already consumed"**. The cookie *value*
might look correct; the cookie is still dead. Read this when the
operator reports "I pasted fresh cookies but whoami still fails."

This file is a troubleshooting + decision-tree companion to the
parent SKILL.md ("Instagram pattern" section) and to
`opencli-instagram-recipe.md`. It does not redefine the cookie
format or the four-endpoint API contract.

## The four root causes, in order of frequency

### 1. The cookie was used elsewhere first

Instagram's `sessionid` is single-use across distinct browser
fingerprint + IP combinations. If the operator copied cookies from
Chrome-A and Chrome-A is still open and active on `instagram.com`,
the cookies are consumed by that browser's session. The
OpenCLI/headless Chrome on the dev VPS sees a "different device"
and Instagram rejects it.

Symptoms: HTTP 401/440 from Instagram's mobile/web endpoints,
"token invalid or already consumed" in the OpenCLI log, the
dashboard auth banner flipping back to `wrong-account` or `error`
within seconds of a successful `completeReauth`.

Fix:

1. **Close every other Chrome tab on `instagram.com`** before
   pasting. The cookie's owner must be the headless Chrome on the
   dev VPS, not the operator's desktop browser.
2. If the operator wants the desktop browser logged in too, use
   **separate Instagram accounts** (the dev-VPS path uses
   `mallu.wave`, the operator's primary stays on its own session).
3. After pasting, do not open `instagram.com` in the source Chrome
   until the scrape finishes. Each subsequent request from the
   source browser rotates `sessionid` and the pasted value dies.

### 2. The cookie was extracted from the wrong domain

DevTools shows cookies scoped to the **exact origin** the page is
loaded on. If the operator is on `https://www.instagram.com` but
copies from the Cookies table for `https://i.instagram.com` (or
vice versa), the cookie is scoped to a different domain and
OpenCLI's site-session won't replay it correctly.

Symptoms: paste looks fine in the dashboard, `site-session.json`
writes successfully, `whoami` returns `no-profile` or
`wrong-account`.

Fix: only copy from `https://www.instagram.com`. The DevTools
recipe in the parent skill's "Instagram pattern" section is
explicit about this — when in doubt, navigate to
`https://www.instagram.com/` first, open DevTools, **then** copy.

### 3. The cookie expired between copy and paste

`sessionid` lifetime is roughly 1–7 days depending on Instagram's
risk heuristics. If the operator logged in two days ago and only
just remembered to paste, the cookie is dead.

Symptoms: paste works, `whoami` returns `ok` for one request, then
reverts to `wrong-account` on the next scrape run. Sometimes the
dev-VPS Chrome sees "checkpoint_required" — Instagram is forcing
the operator to verify identity on the original device.

Fix: log out, log back in to `mallu.wave` in a fresh Chrome tab,
copy both `sessionid` and `ds_user_id` again, paste within five
minutes. **Do not let the source Chrome idle** between copy and
paste — Instagram rotates the session after short idle periods
even when the cookie is still "valid" in DevTools.

### 4. The fingerprint doesn't match (most subtle)

Instagram's anti-scrape detection includes IP, User-Agent,
screen size, timezone, and WebGL hash. The dev VPS has a
Hetzner datacenter IP (147.79.18.32), a server-grade Chrome
UA, and Linux-only WebGL signatures. A `sessionid` created in
the operator's MacBook Chrome will look like a "device hop" the
moment OpenCLI uses it.

Symptoms: paste succeeds, `whoami` returns `ok` for *some*
endpoints, but Instagram's `graphql/query` endpoints (which
return the actual reel/post data) return HTTP 401 with
`checkpoint_required` or `unrecognized_device`. The
`opencli instagram whoami` call still passes because Instagram's
session-check endpoint is more lenient than the data endpoints.

Fix (in order of preference):

1. **Switch to the OpenCLI persistent site-session path** rather
   than raw cookie paste. The session is created inside the
   same Chrome OpenCLI uses to scrape, so the fingerprint is
   consistent. See "The right answer when paste keeps failing"
   below.
2. If the operator must paste, set the dev VPS's Chrome
   `--user-agent` to match the source Chrome exactly. This is
   fragile and breaks on the next UA bump.
3. Add residential proxy in front of OpenCLI's Chrome so the
   IP matches the operator's region. Hetzner datacenter IPs
   are on Instagram's risk list.

## The specific Instagram error strings to grep for

These are the messages that show up in OpenCLI logs and in
`whoami` failures. Map them to root causes above.

| Error string | Root cause | Fix path |
|---|---|---|
| `"token invalid or already consumed"` | 1 (used elsewhere) | Close other browsers, re-extract |
| `"checkpoint_required"` | 1 or 4 (fingerprint / device hop) | Verify on source device, re-paste within 5 min |
| `"unrecognized_device"` | 4 (fingerprint) | Switch to OpenCLI persistent session |
| `"login_required"` | 3 (expired) | Log out, log back in, paste fresh |
| `"user_not_found"` (from whoami) | 2 (wrong domain) | Re-extract from `https://www.instagram.com` only |
| `"rate_limited"` (HTTP 429) | Not a cookie problem — Instagram throttling | Back off, reduce parallel scrapes, no re-paste needed |

The dashboard auth banner surfaces these via `error.message` from
the `InstagramAuthError` class. The component's `form-error`
testid displays them, but does not map them to fix instructions
— the operator has to read this file or the dev VPS journal.

## The right answer when paste keeps failing: OpenCLI persistent session

The four headless-login paths in the parent SKILL.md are listed
as a fallback ladder, but the **best path is Path 1: transferred
pre-authenticated Chrome profile**, run through OpenCLI's
persistent site-session. This is *not* the same as the cookie
paste — it's a full Chrome profile copy where:

- The OpenCLI Chrome on the dev VPS uses the same cookies.
- The OpenCLI Chrome's fingerprint matches the operator's source
  Chrome (because it's literally the same profile directory).
- The session is created with the OpenCLI user-agent, which
  Instagram has whitelisted at a different risk tier than
  arbitrary Chrome UAs.

Procedure (run on the **target dev VPS**, not the orchestrator):

```bash
# 1. Stop any existing OpenCLI process that holds the profile lock.
pkill -f opencli || true

# 2. Snapshot the profile on the SOURCE machine (where the
#    operator is already logged in to mallu.wave).
ssh operator-laptop 'tar -C ~/.config/google-chrome -czf - Profile\\ 1' \
  > /tmp/chrome-profile.tar.gz

# 3. Push to dev VPS and unpack into the OpenCLI profile dir.
scp /tmp/chrome-profile.tar.gz dev-vps:/tmp/
ssh dev-vps '
  mkdir -p /srv/competitors-private/opencli-profile/
  tar -C /srv/competitors-private/opencli-profile/ \
      -xzf /tmp/chrome-profile.tar.gz
  chmod -R 0700 /srv/competitors-private/opencli-profile/
'

# 4. Verify on the dev VPS with the persistent site-session flag.
ssh dev-vps '
  opencli instagram whoami --site-session persistent \
    --site-session-dir /srv/competitors-private/opencli-profile/
'
```

Expected: `{"ok": true, "result": {"username": "mallu.wave"}}`.
If the result is anything else, the profile is missing the
OpenCLI extension's state — reinstall it via
`opencli extension install` and try again.

## Other auth paths ranked for Instagram specifically

The parent SKILL.md's fallback ladder is right for general
scraping work. For Instagram specifically, the ranking is
different because Instagram's anti-scrape is fingerprint-heavy:

| Path | Instagram-specific ban risk | When to pick it |
|---|---|---|
| 1. Transferred Chrome profile + persistent site-session | **Low** (same fingerprint) | Production baseline. **First choice.** |
| 2. SSH X-forward + `opencli instagram login` | **Low–Medium** (real Chrome, datacenter IP) | One-off scraping, not a stable pipeline |
| 3. VNC + manual click | **Medium** (datacenter IP + manual cookie rotation) | When SSH X is broken and the VPS already has VNC for cookie extraction (e.g. `cyberslide.terrybot.top/vnc.html`) |
| 4. Cookie paste | **Medium–High** (different fingerprint, single-use cookie) | Dashboard UX fallback. **Last resort.** |
| 5. Residential proxy + headless Chrome | **Low** (IP + fingerprint both match) | When the operator's primary account is being used and ban risk must be near zero |
| 6. Mobile-web cookies (`m.instagram.com`) | **Low–Medium** (different endpoint class, less strict) | When the desktop-web cookie paste keeps failing — try the mobile endpoint cookies, same Chrome |

The decision tree in practice:

- **One stable scrape per week, dedicated `mallu.wave` account:**
  Path 1. Set it up once, let OpenCLI handle rotation.
- **Dashboard UX where the operator must re-auth from a desktop
  browser they don't own the Chrome profile of:**
  Path 4. Accept the friction. Document the "close other Chrome
  tabs" rule prominently in the paste form.
- **Both paths failing repeatedly with `checkpoint_required`:**
  Path 5. The ban risk on the secondary account is now higher
  than the ban risk on a fresh account created from the dev VPS's
  own IP — burn the secondary, create a fresh one, do the
  persistent-session bootstrap once.

## What NOT to do

1. **Don't paste cookies from the operator's primary Instagram
   account.** Ban risk on a primary is much higher than on a
   dedicated secondary, and the operator's primary is the one
   they care about. The competitors project uses `mallu.wave`
   precisely for this reason.
2. **Don't paste the same `sessionid` to multiple dev-VPS boxes.**
   Instagram's single-use detection catches this within hours.
3. **Don't log the cookie value anywhere.** The paste-form
   backend already scrubs `sessionid` from `console.error` in
   the React banner (see `in-dashboard-instagram-banner.md`,
   test 7). Don't add server-side logging of the raw value.
4. **Don't bypass OpenCLI and call Instagram directly from
   Python.** OpenCLI handles User-Agent, header rotation, and
   rate-limit backoff. A raw `requests.get(...)` against
   `instagram.com` will burn the session within minutes.
5. **Don't keep retrying on `checkpoint_required`.** It means
   Instagram has flagged the session. Stop the scraper, fix the
   root cause (usually Path 4 → Path 1 transition), then resume.
   Each retry trains Instagram's classifier to be more
   aggressive on this account.

## Verification after switching from paste to persistent session

After Path 1 is set up:

```bash
# On the dev VPS:
ssh dev-vps '
  for i in 1 2 3 4 5; do
    opencli instagram whoami --site-session persistent \
      --site-session-dir /srv/competitors-private/opencli-profile/ \
      | jq -c .
    sleep 2
  done
'
```

Expected: five `{"ok": true, "result": {"username": "mallu.wave"}}`
lines in a row. If any of them flips to `wrong-account` or
`checkpoint_required`, the profile copy missed something — most
commonly the IndexedDB or the Chrome Local Storage state. Re-copy
the profile, do not re-paste cookies (you'll get the same failure
mode you were trying to escape).
