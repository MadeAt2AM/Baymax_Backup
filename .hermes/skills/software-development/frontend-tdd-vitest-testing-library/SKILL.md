---
name: frontend-tdd-vitest-testing-library
version: 1.0.0
description: "Frontend test-driven development with Vitest and Testing Library — RED-GREEN-REFACTOR for React/Vue/Svelte components. Covers the gotchas that bite every project: vi.mock + importActual + instanceof, screen.getByText collisions with test names, userEvent.type on controlled inputs, testing-library/jest-dom setup. Use when writing component tests, choosing assertion surfaces, or debugging why a green assertion suddenly goes red after a refactor."
author: Baymax (Baymax Agent)
license: MIT
metadata:
  hermes:
    tags: [testing, tdd, frontend, vitest, react, testing-library, red-green-refactor]
    related_skills: [test-driven-development, karpathy-guidelines, systematic-debugging]
---

# Frontend TDD with Vitest + Testing Library

Class-level skill for RED-GREEN-REFACTOR on React/Vue/Svelte components
using Vitest and @testing-library. The core discipline is the same as
the bundled `test-driven-development` skill: write a failing test, watch
it fail, write the minimum code, watch it pass, refactor. The gotchas
below are specific to the frontend stack and almost always surface as
"the test passed in isolation but fails when I run the full suite"
or "the implementation renders correctly in the browser but the test
rejects it."

## When to Use

- Writing component tests for any UI built with React/Vue/Svelte + Vite
- Choosing between `getByText`, `getByTestId`, `getByRole`, `getByLabelText`
- Deciding whether to mock a module, a hook, or a fetch
- Debugging a test that finds "multiple elements" or "no element" when
  the rendered DOM clearly has the right thing

**Don't over-apply to:** unit-testing pure functions (Vitest is fine, no
testing-library needed), E2E tests (use Playwright/Cypress instead),
visual regression tests (use Chromatic/Percy).

## The Iron Law (same as TDD)

```
NO PRODUCTION COMPONENT WITHOUT A FAILING TEST FIRST
```

The frontend stack makes it tempting to skip TDD — "I'll just render it
and see if it looks right" — but that's manual testing, not TDD. The test
captures the contract (what the user sees + what fires when they act).
A refactor that breaks the contract will fail the test. A refactor that
only changes implementation will not.

## RED-GREEN-REFACTOR (frontend variant)

### RED — Write a failing component test

A good component test asserts:
1. **One behavior** the user can observe (what they see, what fires)
2. **Real behavior** — no snapshot tests, no internal-state inspection
3. **One clear name** — "shows the auth warning", not "renders correctly"

```tsx
it("shows the auth warning when state is not ok", async () => {
  mockedFetchStatus.mockResolvedValue(STATUSES.noProfile);
  render(<InstagramAuthBanner />);
  await waitFor(() => {
    expect(screen.getByTestId("auth-warning")).toBeInTheDocument();
  });
});
```

### Verify RED — Watch it fail

`npx vitest run src/test/Foo.test.tsx -t "<test name>"` — confirm it
fails for the right reason (missing component or missing element), not
for a typo or import error.

### GREEN — Minimum component

Write the smallest component that satisfies the test. No speculative
features, no premature prop spreads, no "I'll need this later" states.

### Verify GREEN — Watch it pass + full suite

Run the specific test, then the full frontend suite. Then the backend
suite. Then the E2E if you have one. A green component test in isolation
proves nothing about the rest of the app.

## Gotchas — the ones that bite every project

These are listed in approximate order of "how often did this happen in a
real session."

### 1. `vi.mock` + `importActual` + `instanceof` — three-way trap

When you mock a module with the spread pattern:

```ts
vi.mock("../lib/foo", async () => {
  const actual = await vi.importActual<typeof import("../lib/foo")>("../lib/foo");
  return {
    ...actual,
    fetchStatus: vi.fn(),
  };
});
```

…an `instanceof` check in the implementation against the *real* class
reference can fail when the test's `new RealError(...)` literal resolves
to the mock's `RealError`, but the implementation's `err instanceof
RealError` resolves to the real module's `RealError`. The two are not
always `===`, and the check returns `false`.

**Symptom:** the implementation falls through to the "unexpected error"
branch and the test sees a generic message instead of the specific one.

**Fix:**
- Import the error class from the same module path the implementation uses
  (no re-aliasing).
- Or, in the test, assert by `message` substring or by `statusCode` property
  on the error object — don't rely on `instanceof`.
- Always assert the rendered output, not the implementation branch. If the
  banner shows "Failed to complete reauthentication" instead of the
  specific message, the test passed but the contract is wrong.

### 2. `screen.getByText(/phrase/i)` collides with the test name itself

When the test description is `it("shows the DevTools extraction
instructions when state is not ok", ...)` AND the rendered DOM contains
the text "DevTools" inside a `<strong>` tag, `screen.getByText(/devtools/i)`
finds **two** matches: the rendered element AND (in some test runners)
the test wrapper. The error: "Found multiple elements with the text:
/devtools/i".

**Fix:**
- Use `getByTestId("...")` for any text that might appear in the test
  description. Reserve `getByText` for phrases unique to the rendered
  DOM.
- Scope with `within(screen.getByTestId("banner"))` if you need
  `getByText` semantics inside a specific subtree.
- Same trap applies to fixture keys: a `STATUSES = { wrong: {...} }`
  object with key `wrong` will collide with `screen.getByText(/wrong/i)`.

### 3. `userEvent.type` fires `onChange` per character

For long secret inputs (a 40-character `sessionid`, a JWT, a pasted token),
`userEvent.type` produces one `onChange` per character. If the
implementation validates on every change (rather than on submit), you'll
see 40 validations including 40 toasts, 40 API calls, or 40 rerenders.

**Fix:**
- Validate on submit, not on change, when the input is a long secret.
- For tests that need to submit a long value, build the string and use
  `await userEvent.paste(input, longString)` which fires one event.

### 4. `@testing-library/jest-dom` matchers need explicit setup

`toBeInTheDocument`, `toHaveTextContent`, `toBeVisible` are NOT vitest
matchers by default. They're provided by `@testing-library/jest-dom`.

**Setup checklist:**
1. `import "@testing-library/jest-dom/vitest"` in `src/test/setup.ts`
2. Reference `setup.ts` from `vitest.config.ts`:
   ```ts
   test: { setupFiles: ["./src/test/setup.ts"] }
   ```
3. Add to `tsconfig.json` `compilerOptions.types`:
   ```json
   "types": ["vitest/globals", "@testing-library/jest-dom"]
   ```

Missing any of the three leaves the matchers as undeclared identifiers at
typecheck time and as `undefined is not a function` at runtime.

### 5. `mockedStartReauth.mockResolvedValue(...)` doesn't trigger a re-render

If your component reads `mockedStartReauth` from a hoisted `vi.mock`,
the mock is replaced at module-load time. The component's call site
sees the new mock on every render. But the test's expectations must
`await waitFor(...)` after each interaction, because React state updates
are batched and the assertion can run before the re-render.

**Fix:** `await waitFor(() => { expect(mockFn).toHaveBeenCalledWith(...); })`
after every click, type, or submit.

### 6. The `setup.ts` import path is relative to `vitest.config.ts`

If your project has `apps/web/vitest.config.ts` and the setup file is at
`apps/web/src/test/setup.ts`, the path is `./src/test/setup.ts`. A wrong
path silently fails — the matchers appear to be missing but vitest
doesn't error. Verify with `npx vitest run --reporter=verbose` and look
for the setup line.

### 7. `act()` warnings on async state updates

When a test types into an input and the component's `onChange` calls
`fetchStatus()` (async), React logs "An update to X inside a test was
not wrapped in act(...)". Two fixes:

- (a) Use `await userEvent.type(input, value)` — `userEvent` is already
  wrapped in `act()`.
- (b) If you must use `fireEvent` (e.g. for a custom event), wrap the
  state-update-triggering call in `await act(async () => { ... })`.

### 8. `import` cycles with `vi.mock` — hoist the mock

Mocks declared inline at the top of the test file are auto-hoisted by
Vitest, but mocks declared inside a `beforeEach` or after a `describe`
are NOT hoisted. Symptom: "Cannot access 'X' before initialization".

**Fix:** declare all `vi.mock(...)` calls at the top of the test file,
above any `import` statements. Or use `vi.hoisted(() => ({ ... }))` for
shared fixtures.

### 9. `screen.debug()` with no args returns the DOM as a string

When a test fails and you want to inspect the DOM without rendering a
huge diff, drop a `console.log("DEBUG:", screen.debug(undefined, 30000))`
inside the `waitFor`. `screen.debug(undefined, 30000)` returns the
DOM tree as a plain string (truncated to 30000 chars). Combined with
`grep -E "data-testid|form-error|button"` in the test runner output,
it tells you exactly which elements are rendered without reading a
whole diff.

This is faster than `prettyDOM(container)` for large trees, and it
survives through `vi.mock` because it reads the real DOM, not the
mocked module surface. After debugging, **remove the debug line** —
leaving it in CI pollutes the test output.

### 10. `{ selector: "label" }` scopes label-text lookups

When the rendered DOM contains text that is also used as a label
(e.g. `<label>sessionid</label>` and the rendered status contains
the word "sessionid"), `screen.getByText(/sessionid/i)` returns both.
Use `{ selector: "label" }` to scope the lookup:

```ts
screen.getByText(/sessionid/i, { selector: "label" })
screen.getByText(/ds_user_id/i, { selector: "code" })
```

Generalises to any HTML tag. Combine with `within(...)` for sub-tree
scoping when the same text appears in two siblings.

### 11. Two-step `instanceof` with vi.mock + importActual — deeper trap

Gotcha #1 covers the basic trap. The deeper version: when you mock a
module via the `...actual` spread pattern AND the implementation
imports the same module via a *different relative path*
(`from "../lib/foo"` in the test vs `from "./foo"` in the
implementation), the `instanceof` check inside the implementation can
return false even though both look like the same class.

**Symptom:** the implementation falls through to the
`err.message` fallback instead of the specific class branch. The
component shows the generic "Failed to complete reauthentication"
instead of the actual server error message. The test passes
`mockedFn.mockRejectedValue(new RealError(422, "..."))` but the
component never sees the right class.

**Fix:** either
- (a) Pin the implementation and test to the **same canonical import
  path** (`from "./foo"` vs `from "./foo"` vs `from "./foo/index"`
  are not the same to Vite),
- (b) import the error class in the test by its full path
  (`import { RealError } from "../lib/foo"`), and assert by
  `err.statusCode === 422 && /pattern/.test(err.message)` instead of
  `err instanceof RealError`,
- (c) in the component, always branch on `statusCode` first and only
  use `instanceof` as a fallback for type discrimination.

Option (b) is the most robust and avoids coupling tests to
implementation import paths.

## The Verification Checklist (frontend-specific)

- [ ] Every component has at least one test asserting user-observable behavior
- [ ] Every test failed for the expected reason before the implementation was written
- [ ] `screen.getByTestId` is the primary assertion surface; `getByText` only for unique rendered phrases
- [ ] `vi.mock` + `instanceof` checks avoided; assert by message/statusCode/property
- [ ] `userEvent.type` only for short inputs; `paste` for long secrets
- [ ] `await waitFor(...)` after every interaction that triggers async state
- [ ] Full suite passes: `npx vitest run` returns 0 with no warnings
- [ ] Typecheck passes: `npx tsc -b --noEmit` returns 0
- [ ] Build passes (or the build is intentionally deferred to CI)

## When Stuck

| Symptom | Likely cause | Fix |
|---|---|---|
| "Found multiple elements with the text: /X/i" | Test name contains `X` AND rendered DOM contains `X` | Use `getByTestId` or `within(...)` |
| "Unable to find an element with the text: /X/i" | Render not yet committed, or text is split across nodes | `await waitFor(...)` or use function matcher |
| "expected spy to be called with arguments: [...]" | Mock not called yet (async not awaited) | `await waitFor(...)` after the click |
| "An update to X inside a test was not wrapped in act(...)" | Used `fireEvent` instead of `userEvent`, or missed `await` | Use `userEvent` (auto-act) or wrap in `await act()` |
| "Cannot find module 'X'" in test | `vi.mock` path is wrong, or `X` not installed | Check path is relative to the test file; install if missing |
| Tests pass individually, fail when run as a suite | Module state leaking between tests | `vi.clearAllMocks()` in `beforeEach`, or `vi.resetModules()` between files |
| "instanceof X returned false" but message matches | `vi.mock` + `importActual` shadowed the class reference | Assert by message substring, not `instanceof` |
| Test passes but rendered DOM lacks expected text | Mock returned `null` / `undefined` and the component rendered a fallback | `await waitFor` and inspect rendered output with `screen.debug()` |

## References

- **Skill: `test-driven-development`** — the bundled class-level TDD
  skill. The frontend-specific gotchas here extend it; the iron law and
  RED-GREEN-REFACTOR discipline are unchanged.
- **Skill: `karpathy-guidelines`** — surgical-changes discipline
  applies especially hard to frontend: a `<div>` wrapper added "for
  layout" can break a `getByTestId` assertion in a test that greps for
  the testid at a different DOM depth.
- **Skill: `systematic-debugging`** — when a frontend test fails after
  a refactor, the four-phase debug (reproduce → isolate → root cause →
  fix) avoids the "let me tweak the test" trap.
