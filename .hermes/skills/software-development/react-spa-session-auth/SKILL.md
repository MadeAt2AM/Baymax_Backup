---
name: react-spa-session-auth
description: "Single-operator session-cookie auth for React SPAs — the `signIn`/`signOut` context pattern, the login-then-redirect bounce trap, auth-gated routing, and tests that pin the state machine. Use when building or fixing a dashboard that uses a single-cookie session (no OAuth, no JWT in localStorage, no third-party auth provider), when the login button succeeds but the page bounces back to /login, when `/api/auth/me` 401s right after a successful login, or when you need to gate multiple routes behind one operator credential."
version: 1.0.0
author: Baymax (Baymax Agent)
license: MIT
metadata:
  hermes:
    tags: [react, auth, session-cookie, spa, frontend, routing, context]
    related_skills: [frontend-tdd-vitest-testing-library, secure-web-dashboard, headless-vps-scraping-toolchain]
---

# React SPA session-cookie auth

Class-level skill for the single-operator / single-cookie dashboard pattern:
one user, one bcrypt password, one signed-cookie session. Covers the
React-side shape that keeps login → dashboard working, the gotchas that
cause the login button to bounce back to `/login`, the auth-gated routing
contract, and the test surface that pins the state machine.

## When to use

- Building any "single user, single password" dashboard (admin panel,
  operator console, internal tool) — no OAuth, no third-party login
- Diagnosing the **"login button works but page bounces back to /login"**
  loop. This is the #1 symptom of the wrong auth-state shape.
- Wiring `/api/auth/login` + `/api/auth/me` + `/api/auth/logout` into a
  React Router SPA so all routes (other than `/login`) are auth-gated
- Replacing the implicit `localStorage.getItem('token')` antipattern
  with a real session cookie + `HttpOnly; Secure; SameSite=Lax` set by
  the server, and a small client-side wrapper that exposes
  `signIn(username, password)` / `signOut()` / `useAuth()`
- Pinning the auth state machine with tests so a refactor doesn't
  silently break login or logout

**Do not use for:** OAuth/OIDC flows (the IdP owns state, not you),
multi-user apps with refresh tokens, browser-extension auth, or any
flow where the session lives in `localStorage` rather than an
`HttpOnly` cookie.

## Iron rule

```
THE APP'S RENDER MUST READ ITS AUTH STATE FROM A SINGLE SOURCE OF TRUTH,
AND signIn() / signOut() MUST BE THE ONLY WAY THAT STATE CHANGES.
```

The trap: a LoginPage calls `navigate("/")` after a successful login,
but the App component is reading from `useEffect(() => me(), [])`
that ran ONCE on mount. After login, the App is still in the
"anonymous" branch, the `<Navigate to="/login" />` catch-all fires,
and the user lands back on /login even though `/api/auth/me` would
return 200. The fix is a context where `signIn` flips the auth
state directly — no navigate needed, no effect re-run needed.

## The shape

### 1. The typed wrapper — `src/lib/auth.ts`

Tiny module, four functions, no React imports:

```ts
export class AuthError extends Error {
  constructor(public readonly statusCode: number, message: string) {
    super(message);
    this.name = "AuthError";
  }
}

export interface DashboardUser { username: string; }

export async function login(username: string, password: string): Promise<DashboardUser> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    credentials: "same-origin",  // cookie set by the API stays scoped to the app
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch { /* ignore */ }
    throw new AuthError(response.status, detail);
  }
  return (await response.json()) as DashboardUser;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
}

export async function me(): Promise<DashboardUser | null> {
  const response = await fetch("/api/auth/me", { credentials: "same-origin" });
  if (response.status === 401) return null;
  if (!response.ok) throw new AuthError(response.status, `${response.status} ${response.statusText}`);
  return (await response.json()) as DashboardUser;
}
```

`credentials: "same-origin"` is the load-bearing flag. Without it, the
browser drops the `Set-Cookie` from `/api/auth/login` and the session
never sticks.

### 2. The auth context — `src/lib/auth-context.tsx`

The single source of truth. Owns the three-state machine
(`"loading" | "anonymous" | "authenticated"`) and exposes `signIn` /
`signOut` / `refresh` / `useAuth()`:

```tsx
type AuthState = "loading" | "anonymous" | "authenticated";

interface AuthContextValue {
  auth: AuthState;
  username: string | null;
  refresh: () => Promise<void>;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>("loading");
  const [username, setUsername] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const user = await me();
      setAuth(user ? "authenticated" : "anonymous");
      setUsername(user?.username ?? null);
    } catch {
      setAuth("anonymous");
      setUsername(null);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const signIn = useCallback(async (u: string, password: string) => {
    const user = await login(u, password);
    setUsername(user.username);
    setAuth("authenticated");
  }, []);

  const signOut = useCallback(async () => {
    await logout();
    setAuth("anonymous");
    setUsername(null);
  }, []);

  const value = useMemo(
    () => ({ auth, username, refresh, signIn, signOut }),
    [auth, username, refresh, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
```

**Why `signIn` flips auth directly:** after a successful login, the
context flips to `"authenticated"`. The App's render re-runs, the
anonymous branch unmounts, the gated branch mounts, and the user lands
on the dashboard. No `navigate()` call needed, no effect re-run needed,
no race window.

### 3. The App — `src/App.tsx`

Two routing branches, gated by `useAuth().auth`. The `*` catch-all in
the anonymous branch is the gate — every non-login URL bounces to
`/login` when the session is missing or expired:

```tsx
import { AuthProvider, useAuth } from "./lib/auth-context";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

function AppRoutes() {
  const { auth, username } = useAuth();
  if (auth === "loading") return <LoadingScreen />;

  if (auth === "anonymous") {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <div>
      <Header username={username ?? "operator"} />
      <main>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          {/* every other gated page lives here */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter><AppRoutes /></BrowserRouter>
    </AuthProvider>
  );
}
```

### 4. The LoginPage — calls `signIn`, not `navigate`

```tsx
const { signIn } = useAuth();
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setError(null);
  setSubmitting(true);
  try {
    await signIn(username, password);  // <-- this is enough
    // No navigate("/") needed — the context flips, the App re-renders.
  } catch (err) {
    setError(err instanceof AuthError ? err.message : "Login failed");
  } finally {
    setSubmitting(false);
  }
};
```

### 5. The Header — calls `signOut`, not `navigate`

```tsx
const { signOut } = useAuth();
const handleLogout = async () => { await signOut(); };
```

## Pitfalls

### 1. The bounce-back loop (the #1 bug)

**Symptom:** user clicks "Sign in", the POST succeeds (200 OK + Set-Cookie),
the URL briefly changes to `/`, then the page is back on `/login`.
`/api/auth/me` 401s in the network panel.

**Cause:** LoginPage called `navigate("/")` but the App's auth state is
still `"anonymous"`. The App's anonymous branch has `<Route path="*"
element={<Navigate to="/login" />} />`, which fires immediately.

**Fix:** move the auth-state ownership into a context. `signIn` sets
`auth = "authenticated"`, the App re-renders, the gated branch mounts.
Delete the `navigate("/")` call.

### 2. `useEffect(() => me(), [])` runs once — stale auth state forever

If you read `me()` only on mount, the auth state is frozen at "loading →
anonymous/authenticated once". A subsequent login or logout (e.g. a
logout button somewhere, a session expiry) will not update the App's
view until a full page reload.

**Fix:** the App's router must read from a context whose state is
updated by `signIn` / `signOut`, not from a one-shot effect.

### 3. `credentials: "same-origin"` is load-bearing

The browser drops the `Set-Cookie` if you omit `credentials` from the
login fetch. The login returns 200 OK but no cookie is set, so the
next `me()` returns 401. Always include `credentials: "same-origin"`
on every auth-related fetch.

### 4. The auth state needs an explicit "loading" — not "anonymous"

On first mount, before `/api/auth/me` resolves, the App must show a
loading state, not the login page. Otherwise the user lands on /login
for ~50ms before the auth check completes, then sees a flash to the
dashboard (if authenticated). The flash is jarring and looks broken.

**Fix:** initial state is `"loading"`, transitions to `"authenticated"`
or `"anonymous"` after the first `me()` resolves.

### 5. The auth context must throw if used outside the provider

`useAuth()` should `throw new Error("useAuth must be used within an AuthProvider")`
when called outside the provider. A silent default value masks
provider-misuse bugs that surface as "the auth state is always anonymous".

### 6. `setAuth("anonymous")` is the right thing on a 401

When `me()` returns 401, the right state is `"anonymous"` (the user
needs to log in again), not `"loading"` or `"error"`. A 401 from
`/api/auth/me` is not an error condition — it is the expected response
when there is no session. Surface it as a normal state transition.

### 7. Logging out is a state transition, not a navigation

`signOut()` should call `await logout()` THEN `setAuth("anonymous")`.
Don't rely on `navigate("/login")` to "log the user out" — the user
may have multiple tabs open and only the originating tab should
navigate. Other tabs stay on their current page until they make the
next API call, which will 401 and the context refresh will route them
to /login.

### 8. Don't put the session in `localStorage`

The cookie is `HttpOnly` — JavaScript can't read it. That's the point.
XSS cannot steal a session it cannot read. If you also stash a JWT in
`localStorage` "for the client to use", you've just made XSS a
session-theft vector. The client doesn't need to read the session —
`credentials: "same-origin"` carries it.

### 9. The login fetch must `await` before the state flip

```ts
const user = await login(u, password);  // await the 200 OK
setUsername(user.username);
setAuth("authenticated");  // then flip
```

Don't optimistically flip auth to "authenticated" before `login()`
resolves. If the login fails (wrong password, rate-limited, server
down), you'll show a gated dashboard that 401s on the next `/me` and
flips back. Awaiting `login()` first means the state flip is honest.

### 10. The Header's logout button must be inside the gated branch

If the logout button is rendered above the auth-gate check, an
anonymous user can see and click it. The click will `signOut()` (a
no-op when there's no session) and the user stays on /login — fine,
but you've leaked a UI affordance that doesn't apply. Render the
Header inside the authenticated branch only.

## The test surface

Pin the state machine with five tests in
`src/test/auth-context.test.tsx`:

1. **starts in loading, then becomes anonymous when /me returns null**
2. **starts in loading, then becomes authenticated when /me returns a user**
3. **falls back to anonymous when /me rejects with AuthError(401)**
4. **signIn flips auth to authenticated on success** (this is the
   bounce-back fix in test form — the test simulates the user
   clicking Sign In and asserts the next render is the gated branch)
5. **signOut flips auth back to anonymous**

Test pattern (Vitest + Testing Library):

```tsx
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../lib/auth", async () => {
  const actual = await vi.importActual<typeof import("../lib/auth")>("../lib/auth");
  return { ...actual, me: vi.fn(), login: vi.fn(), logout: vi.fn() };
});

import { AuthProvider, useAuth } from "../lib/auth-context";
import { login, logout, me } from "../lib/auth";

const mockedMe = vi.mocked(me);
const mockedLogin = vi.mocked(login);
const mockedLogout = vi.mocked(logout);

function AuthProbe() {
  const { auth, username, signIn, signOut } = useAuth();
  return (
    <div>
      <p data-testid="auth">{auth}</p>
      <p data-testid="username">{username ?? "(none)"}</p>
      <button onClick={() => void signIn("operator", "Test123!")}>sign in</button>
      <button onClick={() => void signOut()}>sign out</button>
    </div>
  );
}

function renderProbe() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Routes><Route path="*" element={<AuthProbe />} /></Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

it("signIn flips auth to authenticated on success", async () => {
  mockedMe.mockResolvedValue(null);
  mockedLogin.mockResolvedValue({ username: "operator" });
  renderProbe();
  await waitFor(() =>
    expect(screen.getByTestId("auth")).toHaveTextContent("anonymous"),
  );
  await act(async () => {
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
  });
  await waitFor(() =>
    expect(screen.getByTestId("auth")).toHaveTextContent("authenticated"),
  );
  expect(screen.getByTestId("username")).toHaveTextContent("operator");
});
```

Plus three App-level tests in `src/test/App.test.tsx`:

1. **redirects to /login when the user is not authenticated**
2. **shows the dashboard when the user is authenticated**
3. **shows the login screen after a 401 from /api/auth/me**

These three together pin the routing contract: the gate is the `*`
catch-all, anonymous users cannot reach any non-`/login` path, and a
401 from `/me` is treated as anonymous (not as a crashed app).

## The server-side contract this pattern assumes

- `POST /api/auth/login` accepts `{username, password}`, returns
  `{username}` on success, sets a `Set-Cookie: <name>=<signed-token>`
  with `HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=<ttl>`. The
  cookie has no `Domain` attribute (defaults to the API origin).
- `GET /api/auth/me` returns `{username}` if the cookie is valid,
  401 otherwise.
- `POST /api/auth/logout` deletes the cookie (Set-Cookie with
  `Max-Age=0`) and returns `{status: "ok"}`.
- The cookie's signed token contains `{u: username, t: issued_at}`
  with an HMAC over the secret. Reject if `now - t > ttl`.
- `Secure` is conditional on `app_origin.startswith("https://")` —
  the local dev environment runs over HTTP and a `Secure` cookie
  would never stick.

## When stuck

| Symptom | Likely cause | Fix |
|---|---|---|
| Login button works, then page bounces back to /login | App's auth state still `"anonymous"` after login | Move auth state into a context; `signIn` flips it directly |
| `/api/auth/me` 401s after a successful login | Cookie not set on the login response | Add `credentials: "same-origin"` to the login fetch; check `Secure` flag against the actual `app_origin` |
| `/api/auth/me` 401s on localhost | `Secure` cookie requires HTTPS | Make `_cookie_secure(cfg)` conditional on `app_origin.startswith("https://")` |
| Flash of login screen before dashboard | Initial state is `"anonymous"` instead of `"loading"` | Use three-state machine: `"loading" \| "anonymous" \| "authenticated"` |
| Logout button on login page is visible to anonymous users | Header rendered outside the auth gate | Render Header inside the gated branch only |
| `useAuth()` returns stale auth state after signIn | Two contexts in the tree (e.g. one per route) | Confirm `AuthProvider` wraps the entire `<App />` once, not per-route |
| After logout, other tabs stay on dashboard | That's expected — only the active tab navigates | Accept it, or add a `BroadcastChannel` listener for cross-tab invalidation |
| Login fails but the form clears | `setSubmitting(false)` is inside `try` instead of `finally` | Use `finally` for state-cleanup actions |
| AuthError not surfaced, generic "Login failed" shown | Implementation uses `err.message` on a non-AuthError | Branch on `instanceof AuthError` and use `err.message` only in that branch |

## Related skills

- `frontend-tdd-vitest-testing-library` — the TDD discipline and the
  vitest + Testing Library gotchas this pattern relies on (notably
  the `vi.mock + importActual + instanceof` three-way trap when
  asserting on `AuthError` instances)
- `secure-web-dashboard` — the nginx + Basic Auth + Let's Encrypt
  pattern for exposing a Hermes dashboard. Different threat model
  (Basic Auth at the proxy vs. session cookie at the app), but
  shares the "single operator, one credential" framing
- `headless-vps-scraping-toolchain` — if the dashboard also has an
  in-dashboard reauth flow for Instagram / TikTok / X, the auth
  context here composes cleanly with the cookie-paste banner from
  that skill. The banner does its own start → complete state
  machine; the dashboard's auth context owns operator sign-in only.
