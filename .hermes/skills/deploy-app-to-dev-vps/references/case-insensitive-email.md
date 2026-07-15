# Case-Insensitive Email Handling (Postgres + Drizzle + Express)

A reusable pattern for any Postgres-backed auth/identity system where email
is the primary key for users, invitations, admins, etc. Solves the recurring
bug: `User@Acme.com` and `user@acme.com` are stored and queried as separate
identities.

## The bug

```typescript
// Looks innocent — but Postgres `eq()` on a `text` column is case-sensitive.
const [user] = await db
  .select()
  .from(users)
  .where(eq(users.email, req.body.email))   // raw input
  .limit(1);
```

If the DB row is `platform@syntra.com` and the user types `Platform@syntra.com`,
the row is not found → 401 → "I can't log in" bug report. Worse: if the user
re-registers with the mixed-case form, you end up with two user rows for the
same human.

## The two-layer defense

The fix is **two layers**, not one. Either layer alone is fragile:

| Layer | What it does | Why it's needed alone isn't enough |
|---|---|---|
| **App-side: `normalizeEmail(v)`** | `v.trim().toLowerCase()` before any lookup or insert | Predictable, deterministic, debuggable. But a legacy mixed-case row inserted before normalization will still mismatch. |
| **DB-side: `lower(column) = lower($1)`** | `sql\`lower(${column}) = ${normalizedValue}\`` in the WHERE clause | Catches legacy mixed-case rows. Cheap (PG has a B-tree on the column? Add a functional index on `lower(email)` for sub-millisecond lookups at scale). |

Doing only the app-side normalization means legacy data still mismatches.
Doing only the DB-side comparison means every developer has to remember to
write `sql\`lower(...) = lower(...)\`` instead of `eq(...)`. One helper kills
both problems.

## The helpers

```typescript
// lib/email-normalize.ts
import { sql } from "drizzle-orm";
import type { AnyPgColumn } from "drizzle-orm/pg-core";

/**
 * Trim + lowercase an email for storage or comparison. We lowercase the
 * whole address — RFC 5321 technically allows case-sensitive local parts,
 * but in practice every major provider treats them as case-insensitive,
 * and we want one identity per human.
 */
export function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

/**
 * SQL fragment for a case-insensitive email match. Use in any WHERE clause
 * that compares against an email column. Handles legacy mixed-case rows
 * that pre-date normalization.
 *
 * Example:
 *   .where(emailEq(users.email, parsed.data.email))
 */
export function emailEq(column: AnyPgColumn, value: string) {
  return sql`lower(${column}) = ${normalizeEmail(value)}`;
}
```

## Endpoints that must use these helpers

Grep your codebase for `eq(.*\.email` and `email.toLowerCase()` — every match
is a candidate. The common list:

| Endpoint | Helper to apply |
|---|---|
| `POST /api/auth/login` | `.where(emailEq(users.email, email))` |
| `POST /api/auth/register` | lookup: `emailEq`; insert: `email: normalizeEmail(...)` |
| `POST /api/auth/forgot-password` | `.where(emailEq(users.email, email))` |
| `POST /api/auth/reset-password` | (keyed by token, not email — no change) |
| `POST /api/platform/companies` (tenant + owner) | lookup + insert with `normalizeEmail` |
| `POST /api/platform/companies/:id/admins` | lookup + insert |
| `POST /api/platform/admins` | lookup + insert |
| `POST /api/invitations` | insert with `normalizeEmail` so the `users.email` join later matches |
| `POST /api/users` (when admins create users directly) | lookup + insert |
| `PATCH /api/users/:id` if email editable | lookup + insert |
| `GET /api/users?email=...` if filterable | `emailEq` |

**Don't forget invitations:** the invitation's `email` column must match the
`users.email` column case-insensitively when the invitee accepts, otherwise
they hit the "This invitation was issued to a different email address" path
even when the only difference is casing.

## Verification (after deploying)

```bash
# All three casings should now log in successfully
for casing in "platform@syntra.com" "Platform@syntra.com" "PLATFORM@SYNTRA.COM"; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" \
    -X POST "https://<name>.<domain>/api/auth/login" \
    -H "Content-Type: application/json" \
    --data "{\"email\":\"$casing\",\"password\":\"Test123!\"}")
  echo "$casing -> $code"   # expect: 200 for all three
done

# Register collision: pre-existing lowercase row blocks mixed-case register
curl -sS -X POST "https://<name>.<domain>/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"Platform@syntra.com","password":"...","name":"X","companyName":"Y"}'
# expect: 409 Email already in use
```

## Pitfalls

- **Don't try to do this with a Postgres `COLLATE` clause on the column.** It
  works, but it changes the semantics of every other query that uses the
  column (sort order, joins, indexes) — usually not worth it.
- **Don't lowercase only the domain part.** `User@gmail.com` and
  `user@Gmail.com` are the same identity (Gmail ignores dots and plus
  aliases), but `User@madeat2am.in` and `user@madeat2am.in` are also the
  same. Treat the whole address as case-insensitive — that's what users
  expect.
- **Indexes:** `eq(users.email, ...)` uses a B-tree index on `users.email`
  (it's a UNIQUE constraint). `lower(users.email) = ...` does NOT use that
  index — it does a sequential scan unless you add a functional index:
  ```sql
  CREATE UNIQUE INDEX users_email_lower_unique ON users (lower(email));
  ```
  For a multi-tenant SaaS with thousands of users, this matters. For a
  dev VPS with dozens, it's fine to defer.
- **`invitations.email` vs `users.email` join:** if the invitation was
  created with mixed case (`User@Acme.com`) and `users.email` is
  lowercased, the accept-invite lookup needs the same normalization on
  both sides. The simplest fix is to normalize on insert into
  `invitations` (gotcha above) so the join is straightforward.

## Related

- `security-hardening-web-stack` — covers auth-endpoint rate-limit, which is
  the protective partner for email lookups (rate-limit prevents brute-force
  enumeration of which casings exist).
- `deploy-app-to-dev-vps/SKILL.md` gotcha #19 — the one-line summary.