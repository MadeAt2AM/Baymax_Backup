---
name: unit-testing-db-services
description: Unit-test a service layer that uses pg (or any pool-style DB driver) without running a real database. Stub the pool functions with vi.mock(), capture SQL + params, assert the SQL composition and the returned rows shape. Use for any TypeScript or JavaScript service that talks to Postgres/MySQL/SQLite via a query pool. Triggers on "test this DB-touching service", "stub pg in vitest", "service-layer tests without a database", "how do I test SQL generation", "fake the db pool", "mock pg.Pool".
category: software-development
version: 1.0.0
---
# Unit-testing DB-touching services without a real database

## The class of problem

You have a service file that talks to Postgres through `pg.Pool` or any equivalent pool-style driver. It has functions like `listTemplates(userId)`, `updateLedgerItem(userId, itemId, patch)`, `createUser(email, hash)`. You want to:

1. Verify the **SQL composition** is correct (right columns, right WHERE clauses, right ownership check)
2. Verify the **return type mapping** (NUMERIC string → number, Date → ISO string, null handling)
3. Verify the **kind-tagged result union** (`'ok'` vs `'not_found'`) is correctly populated
4. Run fast (no DB startup, no migration, no fixtures)
5. Run in the same `vitest`/`jest`/`node:test` invocation that typechecks the project

Doing this **without** spinning up a real database gives you all five. Doing it **with** a real database means migrations, ports, charset issues, timezones, and ~2 seconds of fixture setup per test — not worth it for service-layer logic.

## The pattern (Payntra, 2026-07-04)

Payntra's services live in `server/src/services/*.ts` and call into `db.ts` which exposes `query<T>()`, `getPool()`, and `withTransaction()`. The test files in `server/test/*.test.ts` stub `db.ts` entirely via `vi.mock()` and capture the SQL strings + parameter arrays the service produces.

### The three-layer separation that makes this possible

```typescript
// server/src/db.ts — the real module
import { Pool } from 'pg';
export const pool = new Pool({ connectionString: process.env.DATABASE_URL });
export const query = <T>(sql: string, params: unknown[] = []): Promise<{ rows: T[]; rowCount: number }> =>
  pool.query(sql, params);
export const getPool = () => pool;
export const withTransaction = async <T>(fn: (client: PoolClient) => Promise<T>): Promise<T> => { /* ... */ };
```

The service only ever calls the **functions** exported by `db.ts`. It never imports `pg` directly. That thin wrapper is what makes the stubbing trivial — one module, three functions, all synchronous stubs.

### The test stub itself

```typescript
// server/test/templates.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';

interface CapturedCall { sql: string; params: unknown[]; }
const calls: CapturedCall[] = [];
let mockRows: unknown[] = [];
let mockRowCount = 0;

const mockQuery = vi.fn(async (sql: string, params: unknown[] = []) => {
  calls.push({ sql, params });
  return { rows: mockRows, rowCount: mockRowCount };
});

vi.mock('../src/db.js', () => ({
  query: (sql: string, params: unknown[] = []) => mockQuery(sql, params),
  getPool: () => ({}),
  withTransaction: vi.fn(),
}));

import { listTemplates, createTemplate, /* ... */ } from '../src/services/templates.js';

beforeEach(() => {
  calls.length = 0;
  mockRows = [];
  mockRowCount = 0;
  mockQuery.mockClear();
});
```

Three things to notice:

1. **`vi.mock()` is hoisted** by Vitest to the top of the file regardless of where you write it. The dynamic `import()` of the service **after** the mock declaration is a hard requirement — if you `import { listTemplates }` above `vi.mock()`, Vitest will not have replaced `db.ts` yet and you'll be testing the real DB.

2. **`mockQuery.mockClear()` is mandatory in `beforeEach`**. Without it, calls from one test bleed into the next. The captured `calls` array is reset separately.

3. **You must also reset `mockRows` and `mockRowCount`** in `beforeEach`. Each test sets these to whatever it expects the stub to return. `mockRowCount === 0` is the universal "not found" signal.

### Asserting SQL composition

```typescript
it('updates only the status field when only status is provided', async () => {
  mockRowCount = 1;
  mockRows = [{
    id: '11111111-1111-1111-1111-111111111111',
    name: 'Rent', amount: '1190.00', status: 'PAID',
    notes: null, created_at: new Date('2026-07-01T00:00:00Z'),
  }];

  const result = await updateLedgerItem('user-1', '11111111-1111-1111-1111-111111111111', { status: 'PAID' });

  // Assert the parsed result
  expect(result.kind).toBe('ok');
  if (result.kind !== 'ok') return;
  expect(result.item.status).toBe('PAID');

  // Assert the SQL composition
  expect(calls).toHaveLength(1);
  const call = calls[0]!;
  expect(call.sql).toContain('SET status = $1');
  expect(call.sql).not.toMatch(/SET\s+.*default_amount/);  // ← regex, not substring!
  expect(call.sql).toContain('FROM monthly_ledgers ml');
  expect(call.sql).toContain('ml.user_id = $2');
  expect(call.sql).toContain('li.id = $3');
  expect(call.params).toEqual(['PAID', 'user-1', '11111111-1111-1111-1111-111111111111']);
});
```

**Critical pitfall: regex vs substring on the SET clause.** Asserting `expect(sql).not.toContain('default_amount')` will fail if the SQL also mentions `default_amount` in the RETURNING clause or the FROM table. Use:

```typescript
// Right — checks the SET clause specifically:
expect(sql).toMatch(/SET\s+name\s+=\s+\$1/);
expect(sql).not.toMatch(/SET\s+.*default_amount/);
expect(sql).not.toMatch(/SET\s+.*is_active/);

// Wrong — over-broad, matches anything in the SQL string:
expect(sql).not.toContain('default_amount');  // ← catches RETURNING too
```

### Asserting the kind-tagged union

A common pattern for ownership-protected PATCH endpoints is to return a discriminated union. The test exercises both branches:

```typescript
describe('updateTemplate', () => {
  it('returns not_found when no row matches', async () => {
    mockRowCount = 0;
    mockRows = [];

    const result = await updateTemplate('attacker', 'some-id', { name: 'X' });

    // kind-tag asserts no enumeration leak
    expect(result).toEqual({ kind: 'not_found' });
    // ownership WHERE clause must still be present
    expect(calls[0]!.sql).toContain('user_id = $2');
    expect(calls[0]!.sql).toContain('id = $3');
    expect(calls[0]!.params.slice(1)).toEqual(['attacker', 'some-id']);
  });

  it('updates only provided fields', async () => {
    mockRowCount = 1;
    mockRows = [/* valid row */];
    const result = await updateTemplate('user-1', '...', { name: 'Updated Name' });
    expect(result.kind).toBe('ok');
    if (result.kind !== 'ok') return;
    expect(result.data.name).toBe('Updated Name');
  });
});
```

### Asserting NUMERIC string parsing

pg returns `NUMERIC` columns as strings (to avoid losing precision on huge decimals). The service is responsible for converting. Test that:

```typescript
it('parses pg NUMERIC string into a number', async () => {
  mockRowCount = 1;
  mockRows = [{
    id: '...', name: 'Test', amount: '1234.56',  // ← pg returns string
    status: 'PENDING', notes: null, created_at: new Date(),
  }];

  const result = await updateLedgerItem('user-1', '...', { status: 'PENDING' });
  if (result.kind !== 'ok') throw new Error('expected ok');
  expect(typeof result.item.amount).toBe('number');
  expect(result.item.amount).toBe(1234.56);
});
```

### Asserting empty patch is a no-op

```typescript
it('treats empty patch as not_found (defensive)', async () => {
  const result = await updateLedgerItem('user-1', 'some-id', {});
  expect(result).toEqual({ kind: 'not_found' });
  expect(calls).toHaveLength(0);  // ← no SQL emitted at all
});
```

The service guards against the impossible case of "patch with zero fields". The test proves the guard works AND that no DB call was made.

## When to use this pattern

**Use the stub pattern for:** SQL composition, ownership WHERE clauses, kind-tagged result unions, NUMERIC/Date/null type parsing, empty-patch no-op guards, defensive null checks, list/empty-list paths, ordering clauses, RETURNING vs rowCount semantics.

**Do NOT use for:** any test that needs real FK constraints, real `ON DELETE CASCADE`, real transactional rollback, real NUMERIC precision edge cases (e.g. 28-digit numbers), real charset behaviour, real timezone-aware timestamps. For those, run a real Postgres container in docker-compose and use a per-test transaction that rolls back.

**Rule of thumb:** if the test exercises **what the service emits and how it interprets the response**, use the stub. If the test exercises **what the database does with what the service emits**, use a real DB.

## Pitfalls

1. **Import order — service imports must come AFTER `vi.mock()`.**
   ```typescript
   // Right:
   vi.mock('../src/db.js', () => ({ /* stubs */ }));
   import { listTemplates } from '../src/services/templates.js';  // ← AFTER

   // Wrong (Vitest can't hoist over the import):
   import { listTemplates } from '../src/services/templates.js';
   vi.mock('../src/db.js', () => ({ /* stubs */ }));
   ```
   ESM's static imports are hoisted to the top of the file by the runtime, but Vitest's `vi.mock` is hoisted further by the test transformer. Put it before the dynamic-import line that loads the SUT (system under test).

2. **Forgetting `mockQuery.mockClear()` in `beforeEach`**.
   Captured calls from a previous test bleed into the next. Symptom: `expect(calls).toHaveLength(1)` fails because it's actually 3 from the previous test plus 1 from this one. Always clear in `beforeEach`.

3. **`mockRows` and `mockRowCount` must be reset too**.
   `mockQuery.mockClear()` clears the spy metadata but doesn't reset your module-level `let` variables. Set them to `[]` and `0` in `beforeEach`.

4. **The stub's `query` function must be `async`**.
   Even if the service doesn't `await` (it does, but just in case), pg's real query returns a Promise. If your stub returns a non-Promise, TypeScript types may break at the service call site.

5. **`vi.fn()` returns a mock — you can assert on it too**.
   ```typescript
   expect(mockQuery).toHaveBeenCalledTimes(1);
   expect(mockQuery).toHaveBeenCalledWith('SELECT …', ['user-1']);
   ```
   This is the Vitest-native way; the `calls[]` array pattern is equivalent but lets you inspect intermediate state more easily.

6. **For transactional services, stub `withTransaction` separately**.
   If your service calls `withTransaction(async (client) => { await client.query(...); })`, the stub has to either:
   - Run the callback synchronously with a fake client: `withTransaction: vi.fn(async (fn) => fn(fakeClient))`
   - Or return a resolved promise: `withTransaction: vi.fn(async () => undefined)`
   The first option lets you assert what the service did inside the transaction. The second is fine for "did it enter the transaction at all".

7. **Stub `getPool` too if the service uses it directly**.
   Some services do `getPool().query(...)` for one-off queries outside transactions. The stub returns a fake object whose `.query` is the same mock. Don't forget both exports.

8. **Don't try to stub the wrong module path**.
   Vitest matches by the exact import string in the SUT. If the service does `import { query } from '../db.js'`, the stub must use `vi.mock('../src/db.js', …)` (path from test file to source file). If the service does `from '../db'` (extensionless), the stub path must match. Run `vitest --reporter=verbose` to see which path it actually resolved.

9. **The stub can't catch SQL syntax errors**.
   The service emits `INSERT INTO foo VALUES ($1)` and your stub captures it. The stub doesn't actually parse or execute the SQL, so a typo in the table name passes the test. The **build-time hard gates** pattern (typecheck + tests) catches type bugs; the **live curl smoke tests** catch SQL bugs by hitting a real DB. Both are needed.

10. **Parallel test execution can share module-level state**.
    If you put `let mockRows` at module top level and Vitest runs tests in parallel (`threads: true` in config), two tests can race on the same array. Solutions: (a) Vitest's default is single-threaded unless you opt in — fine for service-layer unit tests; (b) if you do opt in, put the state inside a factory function and call it per `it` block.

11. **Don't stub at the wrong layer for transactional integrity tests**.
    If you want to prove "the ownership check is atomic with the UPDATE", you need a real DB to confirm the row's actual state after the query. A stubbed test can prove "the WHERE clause includes the ownership column", but it can't prove "the UPDATE was actually atomic with the SELECT". Live curl smoke tests are the only way to verify the actual atomicity.

12. **Cross-module mocks: `vi.mock` factory referencing a module-level `const` throws `Cannot access X before initialization`.**
    The trap: you write a `vi.mock('../src/rollover.js', () => ({ getOrCreateLedger: getOrCreateLedgerMock }))` and define `const getOrCreateLedgerMock = vi.fn(...)` further down. Vitest hoists the mock factory to the top of the file, **before** your const is initialized, so when the factory runs `getOrCreateLedgerMock` is in the temporal-dead-zone and the whole test file crashes with `ReferenceError: Cannot access 'getOrCreateLedgerMock' before initialization`.

    ```typescript
    // BROKEN — hoisted mock factory tries to use a const that doesn't exist yet
    let mock: ReturnType<typeof vi.fn>;
    vi.mock('../src/sibling.js', () => ({
      siblingFn: mock,  // ← ReferenceError at file load
    }));
    // ... down here you define mock
    const mock = vi.fn();
    ```

    ```typescript
    // BROKEN — same trap, different shape
    const myMock = vi.fn(async () => 'hi');
    vi.mock('../src/sibling.js', () => ({
      siblingFn: myMock,  // ← ReferenceError
    }));
    import { siblingFn } from '../src/sibling.js';
    ```

    **Fix that always works — define the mock INSIDE the factory, then capture it via module re-import + `beforeAll`:**

    ```typescript
    // The factory must be self-contained. Define the spy inline.
    vi.mock('../src/rollover.js', () => ({
      getOrCreateLedger: vi.fn(async (_userId: string, monthYear: string) => ({
        ledgerId: '99999999-9999-9999-9999-999999999999',
        items: [],
        created: false,
        monthYear,
      })),
    }));

    // After the dynamic import below, the mock is installed. Reach into it
    // via the module namespace and stash a reference for assertions.
    import * as rolloverModule from '../src/rollover.js';
    import { createLedgerItem } from '../src/services/createLedgerItem.js';

    let getOrCreateLedgerMock: ReturnType<typeof vi.fn>;

    beforeAll(() => {
      getOrCreateLedgerMock = rolloverModule.getOrCreateLedger as unknown as ReturnType<typeof vi.fn>;
    });

    beforeEach(() => {
      getOrCreateLedgerMock?.mockClear();  // optional chain: safe if beforeAll hasn't run
    });

    it('triggers getOrCreateLedger before any insert', async () => {
      // ...
      expect(getOrCreateLedgerMock).toHaveBeenCalledTimes(1);
      expect(getOrCreateLedgerMock).toHaveBeenCalledWith('user-1', '2026-08');
    });
    ```

    **Why this works:** the factory doesn't reference any outer binding — it creates the spy itself. After the import resolves, `rolloverModule.getOrCreateLedger` IS the mock spy, and we capture it in `beforeAll` for later assertions. The `?.mockClear()` handles the (rare) case where `beforeAll` hasn't run yet for some reason.

    **Alternative: import the module directly in the factory using `await import()`** — but the factory body in `vi.mock` is synchronous in Vitest 1.x, so this doesn't work cleanly. The capture-in-`beforeAll` pattern above is the one that does.

    **Symptom of the bug:**
    ```
    ReferenceError: Cannot access 'getOrCreateLedgerMock' before initialization
      ❯ test/createLedgerItem.test.ts:14:22
      ❯ src/services/createLedgerItem.ts:2:31
    ```
    The error always points to a line inside the mock factory body — that's the giveaway. The line number for the offending reference is in the test file's mock factory; the `at` line is the SUT line that triggered module evaluation.

    **When to use this pattern:** any time your service calls another service (not just a DB pool) AND you want to assert "did the service call into the sibling correctly?" Both the DB pool AND the sibling service need to be stubbed; the sibling needs the capture-in-beforeAll trick because its mock factory must be self-contained.

## The complete working file (Payntra template)

```typescript
// server/test/templates.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';

interface CapturedCall { sql: string; params: unknown[]; }
const calls: CapturedCall[] = [];
let mockRows: unknown[] = [];
let mockRowCount = 0;

const mockQuery = vi.fn(async (sql: string, params: unknown[] = []) => {
  calls.push({ sql, params });
  return { rows: mockRows, rowCount: mockRowCount };
});

vi.mock('../src/db.js', () => ({
  query: (sql: string, params: unknown[] = []) => mockQuery(sql, params),
  getPool: () => ({}),
  withTransaction: vi.fn(),
}));

import { listTemplates, createTemplate } from '../src/services/templates.js';

beforeEach(() => {
  calls.length = 0;
  mockRows = [];
  mockRowCount = 0;
  mockQuery.mockClear();
});

describe('listTemplates', () => {
  it('returns empty array when no templates exist', async () => {
    mockRowCount = 0;
    const result = await listTemplates('user-1');
    expect(result.kind).toBe('ok');
    if (result.kind !== 'ok') return;
    expect(result.data).toEqual([]);
    expect(calls).toHaveLength(1);
    expect(calls[0]!.sql).toContain('FROM expense_templates');
    expect(calls[0]!.sql).toContain('user_id = $1');
    expect(calls[0]!.params).toEqual(['user-1']);
  });
});
```

## Cost on the wire

Each test runs in <1ms. A 12-case test file finishes in ~40ms (the `transform` + `setup` + `collect` phases are non-trivial in Vitest, but the actual test execution is sub-millisecond per case). The full Payntra test suite (~30 cases across 3 files) runs in ~350ms.

Compare: spinning up Postgres-alpine, applying migrations, seeding users, running 30 cases against real DB connections: ~8-12 seconds. Stubbed: ~0.4 seconds.

The tradeoff: stubs don't catch SQL syntax errors or FK constraint violations. Live curl smoke tests catch those. Use both, as documented in the build-time-hard-gates and live-curl-smoke-tests references in the `vps-container-deploy` skill.

## Related skills

- `vps-container-deploy/references/build-time-hard-gates.md` — where this stubbed suite runs as a build-time `RUN npm test` step before `RUN npm run build`
- `vps-container-deploy/references/live-curl-smoke-tests.md` — what catches the SQL bugs that this stubbed suite misses
- `karpathy-guidelines` — the Iron Law of TDD applies here: stubbed tests should be written BEFORE the service code, not after