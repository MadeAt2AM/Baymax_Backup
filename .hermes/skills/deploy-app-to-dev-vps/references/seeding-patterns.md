# Seeding patterns for VPS-deployed Postgres apps

## bcrypt via Postgres `crypt()` (no Node bcryptjs needed)

Production API runtimes are usually slim and don't ship bcryptjs (only what's
in the esbuild bundle + explicitly-installed runtime deps like nodemailer).
Don't try to bcrypt in the API container — generate the hash in Postgres
directly. The format `$2a$12$...` is identical to bcryptjs's expected format
because bcryptjs reads the standard bcrypt header.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO users (email, password_hash, name, role, status, must_change_password, company_id)
VALUES (
  'admin@demo.com',
  crypt('Test123!', gen_salt('bf', 12)),
  'Alex',
  'admin',
  'active',
  false,
  (SELECT id FROM companies WHERE name='Demo Co' ORDER BY id LIMIT 1)
)
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  name          = EXCLUDED.name,
  role          = EXCLUDED.role,
  company_id    = EXCLUDED.company_id;
```

Then on the API side, `bcryptjs.compareSync('Test123!', stored_hash)` succeeds.

## The `companies.name` is not unique gotcha

Most schemas treat `name` as unique on `companies`. SYNTRA's doesn't. This
breaks idempotent seeds:

```sql
-- BROKEN: returns N rows if N "Demo Co" exist, causing
-- "ON CONFLICT DO UPDATE command cannot affect row a second time"
SELECT 'admin@demo.com', crypt(...), c.id
FROM companies c WHERE c.name='Demo Co';

-- FIX: pin to one row
SELECT 'admin@demo.com', crypt(...), c.id
FROM companies c WHERE c.name='Demo Co' ORDER BY c.id LIMIT 1;
```

Always check `information_schema.table_constraints` to see whether `name`
has a UNIQUE before assuming.

## Sequence-not-resetting DELETE

Postgres sequences don't reset when you `DELETE FROM users`. After running
the v2 seed script, user IDs may have advanced past the v1 IDs even after
`DELETE` cleanup. Validation scripts that hard-code `employeeId: 4` for
Alice will fail with "Employee 4 not found in this company".

Always resolve live IDs:

```bash
USER_IDS=$(curl -sS -H "Authorization: Bearer $TOK_ADMIN" \
  "$BASE/api/users" | python3 -c "
import json, sys
d = json.load(sys.stdin)
m = {u['email']: u['id'] for u in d}
print(f\"{m.get('admin@demo.com','')} {m.get('staff1@demo.com','')}\")
")
```

## Idempotent seed shell template

```bash
#!/usr/bin/env bash
# seed_demo_users.sh — runs against the running syntra_postgres container.
set -euo pipefail
PASSWORD="Test123!"
ESCAPED_PW=$(printf "%s" "$PASSWORD" | sed "s/'/''/g")

docker exec -i syntra_postgres psql -U syntra -d syntra -v ON_ERROR_STOP=1 <<EOF
CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO companies (name, plan, status, timezone, currency)
VALUES ('Demo Co', 'starter', 'active', 'Asia/Singapore', 'SGD')
ON CONFLICT DO NOTHING;

INSERT INTO users (email, password_hash, name, role, status, must_change_password, company_id)
SELECT 'admin@demo.com', crypt('${ESCAPED_PW}', gen_salt('bf', 12)),
       'Alex', 'admin', 'active', false, c.id
FROM companies c WHERE c.name='Demo Co' ORDER BY c.id LIMIT 1
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash, name = EXCLUDED.name,
  role = EXCLUDED.role, company_id = EXCLUDED.company_id;
EOF
```

## Verifying the seed

```sql
SELECT email, role, COALESCE(company_id::text, '-') AS company_id,
       SUBSTRING(password_hash, 1, 10) || '...' AS hash_prefix
FROM users
WHERE email IN ('platform@syntra.com','admin@demo.com',
                'manager@demo.com','staff1@demo.com','staff2@demo.com')
ORDER BY email;
```

All five should appear with `active` status, bcrypt `$2a$12$...` hashes, and
correct `company_id` (NULL for platform_admin, 1 for the four Demo Co users).