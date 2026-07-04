# Build-time hard gates — typecheck + tests as Docker build steps

The parent skill covers deploy mechanics (DNS, Caddy, webhook, TLS). This reference covers the **build-discipline** discipline for a real production app on this pipeline: every push must pass typecheck + unit tests before the runtime image is even produced.

The motivation: with a webhook auto-redeploy on every push to `main`, a broken commit hits the live URL in ~30 seconds. Unit tests passing locally ≠ tests passing in the build env. Type-checking locally ≠ strict mode passing in the container. **The Docker build is the single source of truth for "is this safe to ship."**

## The pattern (Payntra, 2026-07-04)

```dockerfile
# Stage 2: server build — typecheck + tests + compile
FROM node:20-alpine AS server-builder
WORKDIR /server
COPY server/package.json server/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY server/ ./

# HARD GATE 1: TypeScript strict-mode across src + test
RUN npm run typecheck

# HARD GATE 2: Vitest unit tests (pure functions only — no DB/network)
RUN npm test

# Build only runs if both gates pass
RUN npm run build

# Stage 3: runtime — dist + node_modules + public only (no test/, no tsconfig)
FROM node:20-alpine
WORKDIR /app
COPY --from=server-builder /server/dist ./dist
COPY --from=server-builder /server/node_modules ./node_modules
COPY --from=server-builder /server/package.json ./
COPY --from=client-builder /client/dist ./public
CMD ["node", "dist/index.js"]
```

## The tsconfig split (works around `rootDir` vs test files)

`tsconfig.json` (production build, what `npm run build` uses):
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    ...
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "test"]
}
```

`tsconfig.test.json` (typecheck + IDE, what `npm run typecheck` uses):
```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "rootDir": ".",
    "noEmit": true
  },
  "include": ["src/**/*", "test/**/*", "vitest.config.ts"]
}
```

`package.json` scripts:
```json
{
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "typecheck": "tsc -p tsconfig.test.json",
    "test": "vitest run"
  }
}
```

Without the split: `tsc -p tsconfig.json` rejects test files with `TS6059: File '/server/test/foo.test.ts' is not under 'rootDir' '/server/src'.` and the build fails before any code can ship.

## What this catches (and what it doesn't)

**Catches:**
- Type errors anywhere in `src/` or `test/`
- Failing unit tests (any pure function: math, validators, year-boundary arithmetic, schema parsing)
- Missing imports / typos in route definitions
- Schema shape mismatches between client and server (when types are shared)

**Doesn't catch (need integration / live curl tests):**
- DB shape mismatches (no DB in build)
- Network calls (no Postgres/SMTP in build)
- Fastify-specific runtime errors (`FST_ERR_SCH_*` only fires at server boot)
- Real auth flow (need a running server + real cookies)

Pair this pattern with the **Live curl smoke tests** protocol in `references/live-curl-smoke-tests.md` — build gates catch code-shape bugs, live curl catches runtime bugs.

## Anti-patterns to avoid

- **`|| echo OK`** after `npm test` — silently swallows test failures. The gate is meaningless.
- **`|| true`** after `npm run typecheck` — same problem, hidden.
- **`RUN echo "Skipping tests in build"`** — defeats the whole point.
- **`npm test -- --run` instead of `npm test`** — if your test script runs Vitest in watch mode by default, this works, but don't depend on it. Make `test` itself non-interactive: `"test": "vitest run"`.
- **Running only one test file** in CI to save time — every push must run the full suite.

## Tradeoffs

| Pro | Con |
|---|---|
| Broken commits never hit live URL | Build is ~10s slower per push (typecheck + tests) |
| Tests run in the same env as production | Tests can't reach a real DB (use docker-compose for that, or mocks) |
| `git push` becomes a real CI signal | Slow local dev iteration (you can skip gates with `npm run build` directly) |
| Forces unit tests to actually exist | Tests that need infra must be excluded from `vitest.config.ts` `include` |

For a single-developer project this is overkill. For an app that has real users and a webhook auto-deploy, it's the minimum.

## What to put in unit tests vs what stays in live curl

**Unit tests (`test/*.test.ts`):**
- Pure math (date arithmetic, money math, string parsing)
- Zod schema validation (valid inputs pass, invalid inputs fail with right errors)
- Hash/encoding helpers
- Anything you can run with `node` and no I/O

**Live curl (after every push that touches runtime):**
- Auth flow (login, logout, forgot, reset, profile)
- DB-backed features (rollover engine, ledger CRUD, templates)
- Cookie domain / Secure flag behaviour
- SMTP integration
- Real Postgres connection

The boundary is clean: if it needs a database, network, or filesystem beyond `node_modules`, it's a live curl test, not a unit test.

## The Payntra Phase 4 lesson (concrete)

We hit three build failures in a row before the gates were in place:

1. `TS6059` (test files outside rootDir) — fixed by tsconfig split
2. `TS2355` (missing `return` statement) — fixed by adding `return items;`
3. `FST_ERR_SCH_VALIDATION_BUILD` (Zod + Fastify required-as-string) — fixed by validating with Zod inline in the handler

Without the build-time gate, each of these would have shipped broken code to `https://payntra.terrybot.top` via the webhook. With the gate, the build failed, the old container kept serving, and we could iterate locally until everything passed.

The cost of those gates: about 8 seconds of extra build time per push. The savings: no broken deploys, no emergency rollbacks, no live users seeing 500 errors because we missed a `return`.

Worth it.

## Minimal verification after adding the gates

```bash
# 1. Confirm the Dockerfile has the gates
grep -A1 'typecheck\|npm test' Dockerfile

# 2. Push a deliberately-broken commit (rename a function call, see the build fail)
# 3. Confirm: webhook fires, build fails, NO new container, old container keeps serving
sudo -n tail /var/log/webhook.log
sudo -n docker ps 2>&1 | grep <project>-app

# 4. Revert the commit, push again, confirm: build succeeds, new container appears
```

If step 3 shows a new container — your gate isn't actually a gate.