# SPA auth-state hygiene — wipe everything on every login

## The bug

Multi-role SPAs (a platform-admin app where the same browser tab is
shared with a customer-tenant login) leak the previous user's
identity into the new user's UI for a brief but visible window.
Symptom:

1. User A logs in as `platform@syntra.com`, sees the platform
   dashboard.
2. User A logs out. `localStorage.auth_token` is cleared.
3. User B navigates to `/login` and signs in as
   `chrisspeakseh@gmail.com` (a CYBERSLIDE tenant).
4. The SPA calls `/api/auth/me` with the *new* token. While that
   request is in flight, the React Query cache still has user A's
   `getGetMeQueryKey()` result. Components render with that stale
   profile: `role === "platform_admin"` → router sends the user to
   `/platform`. The login appears to land on the platform dashboard
   even though it's a tenant login. When `/auth/me` finally
   resolves with user B's profile, the SPA re-routes to `/dashboard`,
   but the user has already seen a flash of the wrong UI and may
   have triggered side effects (analytics events, redirect chains).

Same symptom can surface as: a customer logging in on their custom
domain appears to land on `/platform` (their reported "logged in
on customer domain → platform admin session → bounced to base URL"),
when in fact the API and JWT are correct and the SPA just kept a
stale profile in memory.

## The fix (three lines in the `login()` hook)

```ts
// artifacts/web-app/src/hooks/use-auth.tsx (or equivalent)
const login = (newToken: string, mustChangePassword?: boolean) => {
  // 1. Wipe EVERY shape of persisted identity before adopting the new one.
  try {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("must_change_password");
  } catch { /* storage unavailable — kept resilient */ }

  // 2. Invalidate the React Query cache for the current user so no
  //    component renders the previous user's profile while the new
  //    /auth/me is in flight.
  queryClient.removeQueries({ queryKey: getGetMeQueryKey() });

  // 3. THEN set the new token and let /auth/me re-resolve.
  try { localStorage.setItem("auth_token", newToken); } catch {}
  setToken(newToken);
  // ... rest of the login flow
};
```

Without step 2, the stale `useGetMe` data can survive for as long as
`staleTime` allows (default: 0ms in this codebase, but a
`useQuery({ enabled: !!token, staleTime: 0 })` configuration still
shows the cached *loading=false* result for a frame until the new
query resolves). Without step 1, a stale `must_change_password` flag
from a previous session can force a redirect to `/change-password`
even when the new user has `mustChangePassword: false`.

## When this DOESN'T apply

- Single-role apps (only tenants, no platform-admin route). The
  router never branches on `role`.
- Apps where every fresh login is preceded by a hard page reload
  (the in-memory React Query cache is already empty after `window.location.reload()`).
- Apps that never persist the auth token (cookies-only with
  same-origin SameSite). The SPA hydrates fresh on every reload.

## When this DOES apply

- Platform-admin + tenant roles in the same browser tab.
- Customer-company tenant logs in on their custom domain after a
  platform admin logged in on the platform domain in the same
  browser session.
- Users who share a workstation (retail back office, kiosk, family
  device).
- Post-deployment smoke tests where the same browser session is
  re-used to log in as multiple test users back-to-back.

## Companion to other auth-state hygiene moves

This recipe is the **login-side** counterpart to the **stale-token
recovery** recipe already documented in gotcha #18c of the
`deploy-app-to-dev-vps` SKILL.md. Together they cover both
directions:

- 18c: when `/auth/me` returns 401 (token rotated, JWT secret
  changed, account deleted mid-session) — wipe and reset.
- This file: when a fresh login lands — wipe before adopting.

Both are "defense in depth against stale identity" patterns; a
project with platform-admin + tenant roles should ship both.
