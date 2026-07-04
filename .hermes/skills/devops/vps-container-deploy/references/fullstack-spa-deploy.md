# Full-stack SPA deploy — Vite client + Fastify server + Postgres, single webhook

The parent skill covers the pipeline mechanics (DNS, Caddy, webhook, TLS). This reference covers the **full-stack SPA shape** — a Vite-built React client served by a Fastify server that talks to Postgres, all behind one webhook-driven redeploy. Verified against the Payntra build (2026-07-04, Phases 4–10).

The reference covers:

1. The 3-stage Dockerfile (client-builder || server-builder → runtime)
2. The SPA fallback in Fastify (`setNotFoundHandler` returning `index.html` for non-`/api/` routes)
3. Build-time gates for both client and server (`vite build` + `tsc -b`, plus the existing `typecheck` + `vitest` gates)
4. Frontend verification protocol — `browser_navigate` + console errors + cookie state + JS bundle presence
5. Inline theme-init script — preventing FOUC on the first paint
6. Auth-context handshake on mount — the `/profile` probe that bootstraps the session

## The 3-stage Dockerfile (parallel builders → thin runtime)

```dockerfile
# Stage 1: client build (Vite)
FROM node:20-alpine AS client-builder
WORKDIR /client
COPY client/package.json client/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY client/ ./
# Vite's build does typecheck via tsc -b first (the "build": "tsc -b && vite build" pattern)
RUN npm run build
# Output: /client/dist/{index.html, assets/*}

# Stage 2: server build (Fastify + TS + tests as gates)
FROM node:20-alpine AS server-builder
WORKDIR /server
COPY server/package.json server/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY server/ ./
RUN npm run typecheck       # HARD GATE
RUN npm test                # HARD GATE
RUN npm run build           # produces /server/dist/index.js

# Stage 3: runtime — dist + node_modules + public, nothing else
FROM node:20-alpine
WORKDIR /app
COPY --from=server-builder /server/dist ./dist
COPY --from=server-builder /server/node_modules ./node_modules
COPY --from=server-builder /server/package.json ./
COPY --from=client-builder  /client/dist        ./public   # ← client ships INSIDE the server image
ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000
HEALTHCHECK CMD wget -q -O - http://127.0.0.1:3000/api/health || exit 1
CMD ["node", "dist/index.js"]
```

**Why this shape:**

- Both builders run **in parallel** during the build (Docker's layer cache). First cold build ~3 minutes, subsequent builds ~30s if only one side changed.
- The runtime image is **the union of both outputs**, not a separate `nginx` container. One process serves the API and the SPA. Simpler Caddy config, simpler scaling, simpler debug.
- `public/` contains the built React app (static HTML + JS + CSS). Fastify serves it via `@fastify/static`. SPA fallback sends `index.html` for non-`/api/` routes — see below.
- The test file (`server/test/*.test.ts`) is NOT copied to runtime. The build proves the tests pass; the runtime doesn't ship them.

## Fastify SPA fallback (single process, two roles)

```typescript
// server/src/index.ts
import fastifyStatic from '@fastify/static';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { existsSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const publicDir = join(__dirname, '..', 'public');

if (existsSync(publicDir)) {
  await app.register(fastifyStatic, { root: publicDir, prefix: '/', wildcard: false });

  app.setNotFoundHandler((req, reply) => {
    if (req.url.startsWith('/api/')) {
      return reply.code(404).send({ error: 'not_found' });
    }
    return reply.sendFile('index.html');   // SPA fallback — React Router handles the rest
  });
}
```

Three things to notice:

1. **`existsSync(publicDir)` guard** — during local dev the client is served by Vite's dev server, not Fastify. If `public/` doesn't exist (e.g. running `node dist/index.js` without first running the client build), the SPA fallback simply isn't registered and Fastify only serves `/api/*`. Lets you ship a backend-only container if you ever need to.
2. **`/api/` prefix check in the not-found handler** — without this, hitting `/api/foo` (which returns 404) would also serve `index.html`, masking backend bugs. Only non-API routes get the SPA fallback.
3. **`wildcard: false`** — without this, `@fastify/static` claims every path under `/` as its own and the not-found handler never fires. Critical.

## Client build gates (Vite + tsconfig.node.json references)

The Vite project's `build` script must typecheck BEFORE bundling:

```json
// client/package.json
"scripts": {
  "build": "tsc -b && vite build",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

`tsc -b` (build mode) walks the project references. For a Vite + React + Tailwind project with Vitest, the `tsconfig.json` typically references `tsconfig.node.json` for `vite.config.ts`. **If `tsc -b` is not in the build script, type errors silently slip through** because Vite's bundler doesn't typecheck.

Verified pattern (Payntra client):
- `client/tsconfig.json` — `include: ["src"]`, `references: [{ path: "./tsconfig.node.json" }]`
- `client/tsconfig.node.json` — `include: ["vite.config.ts"]`, `composite: true`
- `client/tsconfig.json` `compilerOptions` adds `"types": ["vitest/globals", "@testing-library/jest-dom"]` so the test setup file imports work without per-file `/// <reference>`.
- `client/vite.config.ts` — uses `defineConfig` from `vite` with `test:` block for vitest config.

## Inline FOUC prevention (sync theme-init in `<head>`)

Vite produces a single `index.html` that React mounts into. The theme decision (light/dark) happens on first render — but by then, the user has already seen a flash of the wrong theme. Fix: an **inline script in `<head>`** that reads localStorage + OS preference and applies the `dark` class to `<html>` before React mounts:

```html
<head>
  <meta name="theme-color" content="#D32F2F" />
  <title>Payntra</title>
  <script>
    (function () {
      try {
        var stored = localStorage.getItem('payntra-theme');
        var theme = stored === 'light' || stored === 'dark'
          ? stored
          : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        if (theme === 'dark') document.documentElement.classList.add('dark');
      } catch (e) { /* localStorage blocked */ }
    })();
  </script>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
```

The `<script>` runs **before** `<script type="module">` (module scripts are deferred by default). Cost: <1ms, no network. Effect: no flash on reload, no flash when navigating to a deep link.

The `ThemeProvider` React component reads the same localStorage key on mount and applies it — the inline script and the React provider agree because they share the key.

## Auth-context handshake on mount

The client needs to know "am I logged in?" before deciding what to render. Pattern that works:

```typescript
// client/src/context/AuthContext.tsx
export function AuthProvider({ children }: { children: ReactNode }): JSX.Element {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async (): Promise<void> => {
    try {
      const data = await apiFetch<ProfileResponse>('/profile');
      setUser(data.user);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setUser(null);  // 401 = not logged in, expected state
      } else {
        throw err;       // network/server error — surface via toast, keep state
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try { await refresh(); } finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [refresh]);

  // ...
}
```

Three things to notice:

1. **`loading: true` initial state** — `RequireAuth` route guard renders a spinner while the profile check is in flight. Prevents a flash of the login page for users who ARE logged in.
2. **`cancelled` flag in `useEffect`** — handles React 18 StrictMode double-invocation cleanly. The first effect's `setUser` is skipped if the component unmounted before the fetch resolved.
3. **401 is not an error** — it's the expected "no session" state. Only network failures or 5xx should be surfaced to the user.

## Frontend verification protocol (after every push that touches client/)

The live-curl-smoke-tests reference covers backend assertions. For an SPA, also verify:

1. **Index HTML serves** — `curl -s https://<app>.<domain>/` returns 200 with your `<title>`, meta tags, and inline FOUC script.
2. **JS bundle serves** — grep the HTML for the bundle path (`<script type="module" src="/assets/index-XXXX.js">`), curl it, expect ~100-300 KB.
3. **No console errors on load** — `browser_navigate` + `browser_console` to the root URL. Zero `js_errors` is the assertion.
4. **Unauthenticated user lands on login** — `browser_navigate https://<app>.<domain>/` → snapshot shows the login form, NOT the dashboard. Proves the `RequireAuth` guard works at the routing layer.
5. **Login flow round-trip** — `browser_type` email + password into the form fields, `browser_click` the submit button, snapshot. If the page transitions to the dashboard, login works. If it stays on login, check `browser_console` for errors and look at the server log for the login attempt's status code.
6. **Theme toggle persists across reload** — `browser_click` the theme toggle, `browser_navigate` the same URL again, snapshot. The theme should still be applied (no FOUC, persisted to localStorage).
7. **Static assets resolve** — images, fonts, CSS files referenced in the HTML should all 200.

Worked example (Payntra Phase 7, 2026-07-04):

```bash
# 1. Index HTML
curl -s -o /tmp/home.html -w "status: %{http_code}, size: %{size_download}\n" \
  https://payntra.terrybot.top/
# Expected: 200, ~1 KB

# 2. JS bundle
grep -oE '/assets/[a-zA-Z0-9_.-]+\.js' /tmp/home.html | head -1 | xargs -I{} \
  curl -s -o /dev/null -w "JS: %{http_code}, size: %{size_download}\n" \
  "https://payntra.terrybot.top{}"

# 3. HTML content sanity check
grep -E '(theme-color|payntra-theme|description|<title>)' /tmp/home.html
# Expected: meta theme-color="#D32F2F", inline FOUC script, title "Payntra"

# 4-6: Browser-based assertions via browser_navigate
# 4. Unauthenticated → redirected to /login
browser_navigate https://payntra.terrybot.top/
browser_snapshot  # expect: LoginPage elements

# 5. Login flow
browser_type @e4 chris@madeat2am.in
browser_type @e5 TestPass1!
browser_click @e6  # sign-in button
browser_snapshot  # expect: dashboard, OR error message + form

# 6. Theme toggle
browser_click @e2  # theme toggle
browser_navigate https://payntra.terrybot.top/
browser_console  # expect: 0 errors, theme persisted
```

## Pitfalls specific to the full-stack SPA shape

### A. `browser_*` cookies don't carry from `curl` sessions

The browser session used by `browser_navigate`/`browser_type`/`browser_click` is a separate cookie jar from the curl cookie file (`/tmp/payntra.cookies`). Logging in via curl does NOT give the browser an authenticated session. To test the authed UI flow, log in THROUGH the browser (`browser_type` + `browser_click`), not via curl beforehand. Verified 2026-07-04 (Payntra — initial verification with curl cookies + browser navigation gave a false negative on the SPA flow).

### B. Vite client build fails silently on type errors

If `client/package.json` has `"build": "vite build"` (no `tsc -b` first), type errors in `.tsx` files are silently ignored — Vite's bundler doesn't typecheck. The build succeeds, the broken component ships, and the bug surfaces in the browser as a runtime crash instead of a build failure.

**Fix:** always `"build": "tsc -b && vite build"`. The first phase of `tsc -b` exits non-zero on type errors, the build fails, and the broken code never ships.

### C. Tailwind `darkMode: 'class'` requires the class to be on `<html>`, not `<body>`

If you set `darkMode: 'class'` in `tailwind.config.js`, Tailwind only applies the dark variants when `.dark` is on `<html>`. Theme-provider logic that sets the class on `<body>` will look correct in DevTools but the colors won't change. Always set the class on `document.documentElement` (= `<html>`).

### D. The Docker `client-builder` cache invalidates on EVERY push because `COPY client/ ./` is the first content-bearing layer

The `npm ci` step is cached after the first run — that's the big win. But `COPY client/ ./` invalidates the cache for any client change, which is fine. **However**: changes to `server/` also invalidate `client-builder`'s cache because Docker doesn't know they're independent. Result: full client rebuild on every push, even server-only changes.

**Fix (optional, only if build time matters):** use build arguments to decouple — `ARG SERVER_HASH=latest` and `COPY server/package.json server/package-lock.json* ./` inside the client stage if the client depends on the server's openapi spec. Most apps don't need this — full rebuilds are 1-2 minutes.

### E. The TS `JSX.Element` namespace requires `@types/react` to be installed

In strict TypeScript with `@types/react@18.3+`, the global `JSX` namespace lives under `React.JSX`, not the bare `JSX`. If your `tsconfig.json` doesn't have `"jsx": "react-jsx"` AND you write `function foo(): JSX.Element`, the LSP shows errors like "Cannot find namespace 'JSX'". Fix:

```json
// tsconfig.json
"compilerOptions": {
  "jsx": "react-jsx",          // ← required for new JSX transform
  "lib": ["ES2022", "DOM", "DOM.Iterable"]
}
```

Or annotate as `React.ReactElement` / `React.ReactNode` instead. Verified 2026-07-04 (Payntra — every `.tsx` file threw "Cannot find namespace 'JSX'" until `jsx: react-jsx` was set explicitly).

### F. Vitest + jsdom + Tailwind: CSS imports in tests break the runner

If your component imports `import './custom.css'` at the top of `main.tsx`, and your test file (or a component it imports) transitively pulls in that CSS, Vitest fails to parse the CSS and aborts. Fix in `vite.config.ts`:

```typescript
test: {
  environment: 'jsdom',
  globals: true,
  setupFiles: ['./src/test/setup.ts'],
  css: false,  // ← skip CSS imports during tests
}
```

Or import CSS in test files via a stub (`import './empty.css'`). Verified 2026-07-04 (Payntra — Vitest crashed on first run because `custom.css` had `@tailwind base` directives it didn't understand).

### G. Strict TS + `forwardRef` + `ButtonHTMLAttributes` requires `Omit<…, 'children'>`

A common shape:

```typescript
interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  variant?: Variant;
  children: ReactNode;
}
```

The `Omit<…, 'children'>` is necessary because `ButtonHTMLAttributes` declares `children?: ReactNode` and adding a stricter `children: ReactNode` (required) in the extension causes a conflict. Without the Omit, TypeScript complains "Type 'string' is not assignable to type 'undefined'" or similar.

### H. React 18 StrictMode double-invokes effects in dev — guard with a `cancelled` flag

React 18 StrictMode invokes `useEffect` cleanup-and-re-run cycles on mount in dev. Any async work inside `useEffect` needs to be guarded against the component unmounting before the promise resolves:

```typescript
useEffect(() => {
  let cancelled = false;
  (async () => {
    const data = await fetch(...);
    if (!cancelled) setUser(data);
  })();
  return () => { cancelled = true; };
}, []);
```

Without this, you get "Can't perform a state update on an unmounted component" warnings and potential memory leaks. Verified 2026-07-04 (Payntra — auth profile fetch in StrictMode caused duplicate state updates without the flag).

### I. Vite bundle includes a 5-10 KB shim for `@fastify/static` paths — too small to matter but verify

The static-asset middleware in Fastify adds a per-request URL normalization layer. For a SPA with 50-200 KB of bundled JS + CSS, the cost is negligible. Don't optimize prematurely. Verified 2026-07-04 (Payntra — JS bundle 186 KB, served in ~80ms from `127.0.0.1` and ~250ms from public URL via Caddy).

### J. `darkMode: 'class'` does NOT auto-flip custom semantic tokens — Tailwind only knows its built-in palette

This is the **deeper, more common** version of pitfall C. When you set `darkMode: 'class'` in `tailwind.config.js` and define your own semantic color tokens (e.g. `surface`, `ink`, `brand`), Tailwind only auto-generates `dark:` variants for **built-in** colors (`bg-white`, `text-gray-900`, etc.). It does **not** know that `bg-surface` should switch to dark values when `.dark` is on `<html>`.

**Symptom that confirms this pitfall (not pitfall C):** the body background flips to dark, but cards/inputs/tables stay light. Page looks "half-light, half-dark." `getComputedStyle(html).getPropertyValue('--color-surface')` returns the dark value, but `<div class="bg-surface">` still shows white.

**Cause:** Tailwind config like this generates utilities with hardcoded values that never reference the theme class:

```js
// BROKEN — Tailwind emits background-color: #ffffff regardless of .dark
colors: {
  surface: { DEFAULT: '#ffffff', raised: '#f9fafb', sunken: '#f3f4f6', border: '#e5e7eb' },
  ink: { DEFAULT: '#111827', muted: '#4b5563', subtle: '#6b7280' },
}
```

Even if you ALSO write `:root.dark { --color-surface: #111827; }` in custom.css, `.bg-surface` was already compiled to `background-color: #ffffff` and never references your CSS variable.

**Fix — make Tailwind compile tokens that reference CSS variables, then drive the variables from a class:**

```css
/* custom.css — both themes, RGB triplets so Tailwind can compose alpha */
:root {
  --color-surface: 255 255 255;            /* light page bg */
  --color-surface-raised: 249 250 251;
  --color-surface-sunken: 243 244 246;
  --color-surface-border: 229 231 235;
  --color-ink: 17 24 39;
  --color-ink-muted: 75 85 99;
  --color-ink-subtle: 107 114 128;
}
:root.dark {
  --color-surface: 17 24 39;               /* Charcoal */
  --color-surface-raised: 31 41 55;
  --color-surface-sunken: 11 18 32;
  --color-surface-border: 55 65 81;
  --color-ink: 249 250 251;
  --color-ink-muted: 209 213 219;
  --color-ink-subtle: 156 163 175;
}
```

```js
// tailwind.config.js — every semantic token references the CSS variable
colors: {
  surface: {
    DEFAULT: 'rgb(var(--color-surface) / <alpha-value>)',
    raised:  'rgb(var(--color-surface-raised) / <alpha-value>)',
    sunken:  'rgb(var(--color-surface-sunken) / <alpha-value>)',
    border:  'rgb(var(--color-surface-border) / <alpha-value>)',
  },
  ink: {
    DEFAULT: 'rgb(var(--color-ink) / <alpha-value>)',
    muted:   'rgb(var(--color-ink-muted) / <alpha-value>)',
    subtle:  'rgb(var(--color-ink-subtle) / <alpha-value>)',
  },
}
```

`<alpha-value>` is Tailwind's placeholder — the framework substitutes the alpha number when generating utilities like `bg-surface/50`. Without that placeholder, opacity utilities don't work. With it, the CSS compiles to `background-color: rgb(var(--color-surface) / 1)`, which re-resolves whenever `.dark` is added or removed from `<html>`.

**Bonus:** this pattern lets you write non-Tailwind CSS that also flips automatically:

```css
/* custom.css */
.dense-table th {
  border-bottom: 1px solid rgb(var(--color-surface-border));   /* flips automatically */
  background: rgb(var(--color-surface-sunken));
  color: rgb(var(--color-ink-muted));
}
```

**Auditing an existing project for this bug:**
1. Toggle `.dark` on `<html>` via DevTools (`document.documentElement.classList.add('dark')`)
2. Pick a custom token usage: `bg-surface`, `text-ink`, `border-surface-border`
3. If the element's computed style for `background-color` / `color` / `border-color` does NOT change, this pitfall applies
4. Built-in tokens (`bg-white`, `text-gray-900`) DO flip — that's pitfall C territory, this is different

**Common wrong fix attempts that don't work:**
- Adding `dark:bg-surface-raised` everywhere — redundant noise; the token already auto-flips once the config references CSS vars
- Wrapping values in `theme()` function calls — same problem, still compiles to hex at build time
- Using `data-theme` attribute instead of `.dark` class — same Tailwind behavior, doesn't help with custom tokens

**Right shape, in one sentence:** semantic tokens in `tailwind.config.js` must be `rgb(var(--name) / <alpha-value>)`, and the variables themselves must be defined under both `:root` (light) and `:root.dark` (or `[data-theme="dark"]` etc).

Verified 2026-07-04 (Payntra Phase 7.7 — body background flipped because it used `var(--color-surface)` directly in custom.css, but every card/input that used the `bg-surface` Tailwind utility stayed white. Same toggle button, same class flip — only the build-time token wiring was wrong. Live screenshot confirmed dark mode showing Charcoal background but white cards; fix flipped both).

### M. Pick an API envelope convention UPFRONT and enforce it on both sides — `{resource: …}` or `{resources: […]}`, never bare

A consistent wrapper on every server response is the cheapest way to keep the API contract future-proof. Pick one and apply it everywhere:

```typescript
// Lists:
GET /api/templates         → 200 { templates: [...] }
GET /api/ledger/:monthYear → 200 { monthYear, created, items: [...] }

// Single resource gets:
POST /api/templates        → 201 { template: {...} }
POST /api/ledger/:m/items  → 201 { item: {...} }
PATCH /api/ledger/items/:id → 200 { item: {...} }

// One exception is fine — auth and health that don't return a resource:
POST /api/auth/login       → 200 { ok: true }
GET  /api/health           → 200 { ok: true, db: 'up' }
```

**Why wrap every resource endpoint:**

1. **Future-proof for sibling fields.** Adding `{ templates: [...], count: 10, totalActive: 7 }` later doesn't break clients — they just ignore fields they don't read. A bare `[...]` response can't be extended without a breaking change.
2. **Symmetry between list/single-resource.** Clients can write a single `unwrap(response)` helper instead of branching per endpoint.
3. **Easier to spot leaked secrets.** A response that's `[{ password_hash: '...' }]` is screaming "enumeration leak"; a `{ users: [...] }` is more obviously a list you forgot to filter.

**Client-side enforcement:**

```typescript
// client/src/lib/templatesApi.ts
interface TemplateListResponse { templates: Template[]; }
interface TemplateResponse { template: Template; }

export function listTemplates(signal?: AbortSignal): Promise<Template[]> {
  return apiFetch<TemplateListResponse>('/templates', { signal })
    .then((r) => r.templates);   // ← always unwrap at the API boundary
}

export function createTemplate(body: TemplateCreate): Promise<Template> {
  return apiFetch<TemplateResponse>('/templates', { method: 'POST', body })
    .then((r) => r.template);
}
```

Two things to enforce:

- **The API wrapper function's return type is the unwrapped inner type** (`Template[]`, not `TemplateListResponse`). Consumers shouldn't have to know the envelope exists.
- **Server response types live next to the API function**, not exported across the codebase. The server's Zod schema is the source of truth; the client type is a sibling.

**The bug shape that bites you when you forget this convention** — see pitfall K below. Symptom: client tries `.map()` on an object, gets `TypeError: e.map is not a function`, React silently crashes the component, the page renders but the table is empty. Curl probes show 200 OK and the right JSON. The browser is the only place this surfaces.

**What to do if you inherit an inconsistent codebase:** don't try to fix every endpoint in one PR. Pick a new endpoint going forward, write the wrapper from day one, and migrate older endpoints as you touch them. The envelope convention only matters at API boundaries, not inside the server.

**TypeScript discriminated union trap** — if your service returns a kind-tagged result like `{ kind: 'ok', item: {...} } | { kind: 'forbidden' } | { kind: 'not_found' }`, the route handler must narrow before accessing the inner field. Otherwise:

```typescript
// BROKEN — TS errors with "Property 'item' does not exist on type '...NotFound'"
return reply.code(201).send({ item: result.item });

// RIGHT — narrow on kind first
if (result.kind === 'forbidden') return reply.code(403).send({ error: 'forbidden' });
return reply.code(201).send({ item: result.item });
```

Or, equivalently, drop the `not_found` variant from the union if your service never produces it — TypeScript's narrowing will then require only `forbidden` | `ok` and the `.item` access is safe. Verified 2026-07-04 (Payntra Phase 11 — initial discriminated union had a `not_found` variant never returned; TS rejected `.item` access as ambiguous until the variant was removed).

### K. Server response shape mismatch is invisible to curl but caught by E2E — always run a browser-based smoke test after API changes

When the **server** returns one shape (e.g. `{ id, email, createdAt }` at the root) and the **client** expects another (e.g. `{ user: { id, email, createdAt } }`), curl-based smoke tests will pass with 200 OK and you will think everything works. The bug only surfaces in the actual browser when React state machines try to consume the response and either crash or set `undefined`.

**Real symptom we hit:** `AuthContext.refresh()` did `apiFetch<ProfileResponse>('/profile')` then `setUser(data.user)`. Server returned `{ id, email, createdAt }` (no `user` wrapper). So `data.user === undefined` → `setUser(undefined)` → React normalised to `null` → `RequireAuth` saw `user === null` → redirected to `/login`. Login API call returned 200. `/api/profile` returned 200 with the right payload. The browser still bounced back to login. Curl tests gave no signal.

**Why curl misses it:** curl-based smoke tests assert HTTP status codes and JSON shape at the HTTP boundary. They don't exercise:
- React state setter behaviour with wrong shape
- React Router redirects based on auth context state
- Component re-renders triggered by `setUser`
- The `loading: true → loading: false → user set` sequence in AuthProvider

**Playwright catches it:** the browser-driven smoke test waited for navigation to `/ledger/YYYY-MM` after login. The page never got there because the auth context never settled. Timeout → readable failure → check the AuthContext → fix the shape mismatch → retest green.

**Diagnostic pattern when a Playwright test "fails on navigation" but server logs show 200:**

```typescript
// Add to your login helper or page fixture — instrument /api/* traffic
page.on('request', (req) => {
  if (req.url().includes('/api/')) {
    console.log(`→ ${req.method()} ${req.url()}  body=${req.postData() ?? '-'}`);
  }
});
page.on('response', async (res) => {
  if (res.url().includes('/api/')) {
    console.log(`← ${res.status()} ${res.url()}`);
  }
});
```

If you see `← 200 /api/auth/login` followed by `← 200 /api/profile`, the server did its job. The bug is on the **client** — the React state machine doesn't like the response shape. Don't keep poking the server.

**Fix patterns (apply whichever matches your situation):**

```typescript
// Before: client expected wrapper, server returned flat
const data = await apiFetch<ProfileResponse>('/profile');
setUser(data.user);  // undefined because data has no `user` key

// After: drop the wrapper expectation, treat response as the shape itself
const data = await apiFetch<User>('/profile');
setUser(data);
```

Or, if the server is wrong and you control it:
- Server returns `data.user` shape → client expects it correctly → no bug
- Server returns flat shape → fix the client (cheaper) or change the server (more disruptive)

**Defensive habit:** write the AuthContext/initial-data-fetch using `apiFetch<TheActualShape>(...)` where `TheActualShape` matches what the server literally returns. Don't invent wrapper objects on the client side "for consistency" — they will diverge from the server and you'll spend an hour finding the bug through Playwright.

### L. React 18 + Playwright: `fill()` does not reliably trigger controlled `onChange` — use `pressSequentially` with a small delay

If your component does `<input value={state} onChange={(e) => setState(e.target.value)}>` (the canonical controlled input), `page.getByLabel('Email').fill('…')` sometimes sets `.value` directly without firing React's `onChange` handler. The form then submits with the **stale** state value (often `''`), the server returns 400 (or worse, 401 if the schema silently drops empty strings), and the test fails on the wrong assertion.

This is **not** a Playwright bug. It's how React's synthetic event system interacts with direct `.value` assignment. Playwright's `fill()` documents this caveat; React 18 StrictMode in dev makes it more common.

**Working pattern for React 18 + Playwright:**

```typescript
// Use a stable DOM attribute selector (autocomplete is the most stable),
// click first to focus, then pressSequentially to fire real keydown/keyup events.
const emailInput = page.locator('input[autocomplete="email"]');
const passwordInput = page.locator('input[autocomplete="current-password"]');

await emailInput.waitFor({ state: 'visible' });
await passwordInput.waitFor({ state: 'visible' });

await emailInput.click();
await emailInput.pressSequentially(TEST_EMAIL, { delay: 10 });
await passwordInput.click();
await passwordInput.pressSequentially(TEST_PASSWORD, { delay: 10 });

// Sanity-check the values stuck before clicking submit
await expect(emailInput).toHaveValue(TEST_EMAIL);
await expect(passwordInput).toHaveValue(TEST_PASSWORD);

await page.getByRole('button', { name: /sign in/i }).click();
```

**Why this works:**
- `page.locator('input[autocomplete="email"]')` finds the native HTMLInputElement directly, bypassing the wrapper div. The custom `<Input>` component renders the `<input>` inside a div with adornments; `getByLabel('Email')` works but is sometimes ambiguous about which element receives the fill.
- `pressSequentially('text', { delay: 10 })` fires each character via real keyboard events with a 10ms gap. React's onChange handler runs for every keystroke, state updates correctly, controlled component reflects the new value.
- `await expect(input).toHaveValue(...)` is a hard assertion — if the controlled state didn't update, the test fails HERE with a clear message, not later in the navigation step with a confusing redirect-loop.

**Patterns that don't work reliably:**
- `await input.fill(value)` — sets `.value` directly; React may not see the change
- `await input.type(value)` — same problem; the older `type` API has the same caveat
- `await input.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event('input')); }, value)` — manually dispatches `input` event but React 18 sometimes still doesn't fire onChange

**When `getByLabel` IS the right choice:**
- Native `<label for="email"><input id="email">` markup
- The component renders the label as a sibling of the input, not a wrapper
- You can verify by `await expect(page.getByLabel('Email')).toHaveAttribute('type', 'email')` to confirm it's the right element

Verified 2026-07-04 (Payntra Phase 10 — first Playwright smoke run had 7/8 tests failing on login, all because `fill()` didn't trigger React's onChange. Switching to `pressSequentially` with autocomplete selectors turned 1/8 into 5/8 passing immediately. The remaining 3 were selector tweaks unrelated to input handling).

## Cost on the wire

| Step | Time |
|---|---|
| First cold build (no cache) | ~3 minutes (both npm ci in parallel + tests + bundle) |
| Subsequent build (cache hot, no changes) | ~10 seconds |
| Build with only server changes | ~30 seconds (only server-builder re-runs) |
| Build with only client changes | ~20 seconds (only client-builder re-runs) |
| Webhook → container live | ~30-60 seconds (build + Caddy reload + cert cache) |

## What this reference adds on top of the parent skill

The parent skill's `pitfalls I/J/K/L/M/N/O` cover the Docker + Caddy + build-time-gate pieces. This reference covers the **client-side pieces** that the parent skill doesn't:

- 3-stage Dockerfile with parallel builders + Vite client output shipped inside the server image
- Fastify SPA fallback (`setNotFoundHandler`)
- Client build gates (`tsc -b` before `vite build`)
- Inline FOUC prevention
- Auth-context handshake on mount with `cancelled` flag
- Frontend verification protocol (browser_navigate + console errors + JS bundle presence)
- Pitfalls E through L (JSX namespace, Vitest CSS, Omit children, StrictMode double-invocation, Vite bundle cost, Tailwind custom-token CSS-var dark mode, server/client shape mismatch caught by E2E, React 18 + Playwright `pressSequentially`)
- **Pitfall M: server-API envelope convention** — wrap list/create/get responses in singular-named keys; client must unwrap. Keeps the contract future-proof for adding sibling fields (pagination, totals, etc.) without breaking consumers.

When adding a frontend to a project already on this deploy pipeline, read this reference alongside the parent's pitfalls. Together they cover the full backend + frontend + deploy + verify loop.