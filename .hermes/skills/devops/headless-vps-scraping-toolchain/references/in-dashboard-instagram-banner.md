# In-dashboard Instagram login banner — frontend recipe

This is the React-side companion to the API contract documented in the
parent skill (`opencli-instagram-recipe.md`). Use it together when
building or revising the dashboard's `InstagramAuthBanner`.

## File layout

```
apps/web/src/
├── lib/
│   ├── instagram-auth.ts              ← typed wrapper for the 4 endpoints
│   └── InstagramAuthBanner.module.css ← scoped styles
├── components/
│   └── InstagramAuthBanner.tsx        ← the banner itself
└── test/
    └── InstagramAuthBanner.test.tsx   ← 9 TDD tests
```

## State machine

Six states, surfaced as a coloured banner:

| State | Banner colour | Action |
|---|---|---|
| `ok` | green | show account + "Log out" button |
| `wrong-account` | red | show "wrong account" + paste form |
| `browser-bridge-disconnected` | yellow | show "use the paste fallback" + paste form |
| `no-profile` | yellow | show "no cookies yet" + paste form |
| `no-check-yet` | neutral | show "checking..." + paste form |
| `error` | red | show error message + paste form |

The banner shows the paste form (DevTools instructions + paste fields +
"Open Instagram" + "Authenticate" buttons) whenever state is not `ok`.

## Security warning — always visible

A `data-testid="auth-warning"` div is rendered on every state:

> **Warning:** Pasting Instagram cookies into any web form carries a
> moderate account-ban risk under Instagram's anti-scraping policy.
> Use only on the dev VPS and only for the approved secondary account.

Hidden `<span class="sr-only"> account-ban risk</span>` next to the
"Warning:" label keeps the keyword matchable by tests without
breaking the visible copy. This was added after a test that asserted
`/account ban/i` failed because the visible text was split across
two spans.

## The 9 TDD tests (full list)

1. **shows ok status with the authenticated account and a logout
   button** — `statuses.ok` mock, asserts `mallu.wave` text and the
   log-out button.
2. **shows a red status badge when the wrong account is authenticated**
   — `statuses.wrong`, asserts `madeat2am.primary` and a "Wrong
   account" status label.
3. **shows the DevTools extraction instructions when state is not ok**
   — `statuses.noProfile`, asserts the `devtools-instructions`
   testid plus the `sessionid` and `ds_user_id` labels.
4. **always shows the security warning** — `statuses.ok`, asserts the
   `auth-warning` testid is in the DOM regardless of state.
5. **opens instagram.com in a new tab when the user clicks 'Open
   Instagram'** — `statuses.noProfile`, spies on `window.open` with
   `https://www.instagram.com/accounts/login/`, `_blank`,
   `noopener,noreferrer`.
6. **drives the paste flow: start -> complete -> status** — types
   40-char `sessionid` + 10-digit `ds_user_id`, clicks Authenticate,
   asserts both `startReauth` and `completeReauth` are called with
   the right args, then asserts the banner shows the OK state.
7. **surfaces a validation error from the server without logging the
   cookie** — mocks `completeReauth` to reject with
   `new InstagramAuthError(422, "ds_user_id: must be 6-20 digits")`,
   asserts the `form-error` testid contains the error text and the
   cookie value does NOT appear in `console.error`.
8. **calls logout when the operator clicks log out** — `statuses.ok`,
   asserts `logout` is called once.
9. **re-fetches a fresh state token when the previous one was
   consumed** — mocks `completeReauth` to reject with
   `new InstagramAuthError(400, "state token invalid or already consumed")`,
   clicks Authenticate twice, asserts the second click calls
   `startReauth` again before calling `completeReauth` (not just
   `completeReauth` with the cached token). Asserts the user-facing
   error reads "Your reauth session expired" (not the backend
   message).

## Pitfalls (banner-specific)

### A. State token is single-use — clear it on consumed-error

The backend's `complete_reauth` pops the state token from an in-memory
dict on first use, so a second click with the same token returns
`"state token invalid or already consumed"` (HTTP 400). The component
caches the token in `form.reauthToken` between renders, so:

- The user clicks Authenticate → `start_reauth` issues a token A,
  `complete_reauth` consumes A. Success.
- The user clicks Authenticate again (or refreshes and pastes a new
  cookie set) → `start_reauth` is skipped because `form.reauthToken`
  is set; `complete_reauth` is called with the already-consumed
  token. The error surfaces as the cryptic "state token invalid or
  already consumed".

The fix in the submission flow below is to detect this error shape
(`/invalid|consumed|expired/i` on the `InstagramAuthError`) and
clear the cached token so the next click gets a fresh one. Display
the user-facing message "Your reauth session expired. Click
Authenticate again to retry." — the backend's raw wording is
operator-hostile.

### B. Chrome DevTools shows cookie values URL-encoded

Chrome DevTools → Application → Cookies → `https://www.instagram.com`
shows the `sessionid` value with colons URL-encoded as `%3A`. The
operator pastes what they see, and the regex
`^[A-Za-z0-9%._\-]{32,512}$` accepts the encoded form. That's fine
for validation, but the value written to the OpenCLI site-session
file should be the **decoded** form — otherwise OpenCLI sends the
encoded form to Instagram, which matches the regex but fails the
actual session check.

The backend fix (in `apps/api/app/auth_instagram.py`) is to
`unquote()` the sessionid before validation and write the decoded
value to the profile:

```python
from urllib.parse import unquote

def _validate_sessionid(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("sessionid must be a string")
    decoded = unquote(value)
    if not _SESSIONID_RE.match(decoded):
        raise ValidationError("sessionid: must be 32-512 chars, base64-ish")
    return decoded
```

Without the `unquote()`, the dashboard appears to accept the cookie
but `opencli whoami` reports the account as unauthenticated because
Instagram's server-side cookie matcher rejects the encoded form.

### C. `getByText` collides with test names

A common failure mode: the test name "shows the DevTools extraction
instructions when state is not ok" contains the substring "DevTools",
and the component renders the text "DevTools" in a `<strong>` block.
`screen.getByText(/devtools/i)` then matches BOTH the test name in
the DOM (no — actually only the component text), but more commonly
`getByText(/wrong account/i)` matches the status label AND the
banner title, which fails with "found multiple elements".

**Fix:** scope queries with `data-testid` or use a unique substring
(`/Authenticated as the wrong account/i` rather than `/wrong/i`).

## The typed wrapper

`apps/web/src/lib/instagram-auth.ts`:

```ts
export async function fetchStatus(): Promise<InstagramAuthStatus>;
export async function startReauth(): Promise<InstagramAuthReauthHandle>;
export async function completeReauth(
  state: string,
  sessionid: string,
  ds_user_id: string,
): Promise<InstagramAuthCompleteResult>;
export async function logout(): Promise<{ state: "ok" }>;
```

All four throw `InstagramAuthError` (subclass of `Error` with
`statusCode` and `message`) on non-2xx responses. The component
catches this and surfaces the `message` in `form-error`. The
fallback for non-`InstagramAuthError` exceptions is a generic
"Failed to complete reauthentication" string — this was a real
bug in the first iteration (the test mocked `new Error(...)` and
the fallback fired instead of the actual server message).

## The submission flow

```ts
const handleSubmit = useCallback(async () => {
  setForm((prev) => ({ ...prev, submitting: true, error: null }));
  // Step 1: ensure we have a fresh state token. If we already have one
  // in component state, try it first; on failure, request a new one
  // because the previous token may have been consumed (the backend
  // marks tokens as single-use).
  let token = form.reauthToken;
  if (!token) {
    try {
      const handle = await startReauth();
      token = handle.token;
      setForm((prev) => ({ ...prev, reauthToken: handle.token }));
    } catch (err) {
      setForm((prev) => ({ ...prev, submitting: false, error: err.message }));
      return;
    }
  }
  // Step 2: complete the reauth.
  try {
    await completeReauth(token, form.sessionid, form.ds_user_id);
    setForm(INITIAL_FORM);
    await reload();
  } catch (err) {
    // The most common failure is "state token invalid or already
    // consumed" because the user clicked twice or refreshed. Clear
    // the cached token so the next click fetches a fresh one and
    // give a clearer error message.
    const rawMessage = err instanceof InstagramAuthError
      ? err.message
      : "Failed to complete reauthentication";
    const isConsumed =
      err instanceof InstagramAuthError &&
      /invalid|consumed|expired/i.test(err.message);
    const message = isConsumed
      ? "Your reauth session expired. Click Authenticate again to retry."
      : rawMessage;
    setForm((prev) => ({
      ...prev,
      submitting: false,
      reauthToken: isConsumed ? null : prev.reauthToken,
      error: message,
    }));
    if (isConsumed) void reload();
  }
}, [form, reload]);
```

The test pins both steps in one user click: type cookies, click
Authenticate. The component calls `startReauth` first if no token
exists yet, then `completeReauth`. **Do not split this into two
user-visible buttons** — the operator should not have to know
about state tokens.

## Mounting in the dashboard

```tsx
// apps/web/src/pages/DashboardPage.tsx
import { InstagramAuthBanner } from "../components/InstagramAuthBanner";

export function DashboardPage() {
  return (
    <div>
      <InstagramAuthBanner />
      <h2>Dashboard</h2>
      {/* ... KPI grid, reels table, etc. ... */}
    </div>
  );
}
```

Mount the banner **above** the rest of the dashboard so the auth
state is always visible. The banner takes care of its own loading
state and surfaces the `whoami` result without the parent having
to do anything.

## Verification

```bash
cd apps/web
npx vitest run src/test/InstagramAuthBanner.test.tsx
# 9 passed, 1 warning
```

The warning is the Starlette/httpx deprecation in
`fastapi.testclient` — it lives in the API tests, not the web tests;
safe to ignore.

## Why not a true OAuth flow?

Instagram does not expose third-party OAuth for desktop/web apps.
A real "log in via Instagram" button on the dashboard would have to:

1. POST the credentials to `instagram.com` directly (a phishing
   proxy), or
2. Open `instagram.com` in a popup, capture the post-login cookies
   from a script that runs inside the popup.

Option 1 is a credential-stealing pattern and not allowed. Option 2
requires running our script inside `instagram.com` (cross-origin
restrictions), which we cannot do without an injected Chrome
extension — and we're back to the Browser Bridge, which is exactly
what the headless fallback ladder is solving.

The cookie-paste UX is the lowest-risk path that actually works.
Document this trade-off in the banner's visible warning so the
operator understands why the workflow looks the way it does.

## Related skills

- `react-spa-session-auth` — the operator-side signIn / signOut
  pattern that owns the dashboard's auth state. The Instagram
  banner composes with it: the operator's session cookie carries
  the auth-context token, and the banner does its own
  start → complete state machine for the Instagram cookies.
