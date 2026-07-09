#!/usr/bin/env bash
# seed_demo_users.sh — seeds test users into any Postgres-backed app's DB.
#
# Usage:
#   1. Edit the user block at the bottom (or pass via env).
#   2. Set CONTAINER=<postgres-container-name> and DB_USER / DB_NAME if not default.
#   3. ./seed_demo_users.sh
#
# Test users (all with password Test123! by default; override with SEED_PASSWORD):
#   platform@demo.com  platform_admin     (no company)
#   admin@demo.com     admin              (Demo Co)
#   manager@demo.com   manager            (Demo Co)
#   staff@demo.com     employee           (Demo Co)
#
# Uses Postgres' pgcrypto crypt(pw, gen_salt('bf', 12)) to produce a standard
# bcrypt hash ($2a$12$...) that bcryptjs / bcrypt / Python bcrypt / Go bcrypt
# all accept. This avoids needing bcryptjs installed in a slim runtime image.
#
# Idempotent — re-runs are safe (ON CONFLICT DO UPDATE).

set -euo pipefail

CONTAINER="${CONTAINER:-syntra_postgres}"
DB_USER="${DB_USER:-syntra}"
DB_NAME="${DB_NAME:-syntra}"
PASSWORD="${SEED_PASSWORD:-Test123!}"

red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  red "${CONTAINER} is not running. Start it before seeding."
  exit 1
fi

ESCAPED_PW=$(printf "%s" "$PASSWORD" | sed "s/'/''/g")

yellow "  → seeding company + 4 users (idempotent)..."
docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<EOF
CREATE EXTENSION IF NOT EXISTS pgcrypto;
EOF

docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<EOF
-- Demo company
INSERT INTO companies (name, plan, status, timezone)
VALUES ('Demo Co', 'starter', 'active', 'UTC')
ON CONFLICT DO NOTHING;

-- Platform admin (no company)
INSERT INTO users (email, password_hash, name, role, status, must_change_password, company_id)
VALUES ('platform@demo.com', crypt('${ESCAPED_PW}', gen_salt('bf', 12)), 'Platform Admin', 'platform_admin', 'active', false, NULL)
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role          = EXCLUDED.role,
  status        = EXCLUDED.status;

-- Demo Co users
INSERT INTO users (email, password_hash, name, role, status, must_change_password, company_id)
SELECT 'admin@demo.com', crypt('${ESCAPED_PW}', gen_salt('bf', 12)), 'Demo Admin', 'admin', 'active', false, c.id
FROM companies c WHERE c.name='Demo Co'
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role          = EXCLUDED.role,
  company_id    = EXCLUDED.company_id;

INSERT INTO users (email, password_hash, name, role, status, must_change_password, company_id)
SELECT 'manager@demo.com', crypt('${ESCAPED_PW}', gen_salt('bf', 12)), 'Demo Manager', 'manager', 'active', false, c.id
FROM companies c WHERE c.name='Demo Co'
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role          = EXCLUDED.role,
  company_id    = EXCLUDED.company_id;

INSERT INTO users (email, password_hash, name, role, status, must_change_password, company_id)
SELECT 'staff@demo.com', crypt('${ESCAPED_PW}', gen_salt('bf', 12)), 'Demo Staff', 'employee', 'active', false, c.id
FROM companies c WHERE c.name='Demo Co'
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role          = EXCLUDED.role,
  company_id    = EXCLUDED.company_id;
EOF

green "  ✓ seeded"
docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -A -F'|' -c "
SELECT email, role, COALESCE(company_id::text, '-') AS company_id, status,
       SUBSTRING(password_hash, 1, 10) || '...' AS hash_prefix
FROM users
WHERE email IN ('platform@demo.com','admin@demo.com','manager@demo.com','staff@demo.com')
ORDER BY email;
"