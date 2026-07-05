# SMTP Config Debugging — Missing env_file and Placeholder Values

**Date:** 2026-07-05  
**Project:** Payntra  
**Environment:** Dev VPS (147.79.18.32) — two separate issues found

---

## Issue 1: docker-compose.yml Missing `env_file` Directive

### Symptom
```bash
docker exec payntra-app env | grep SMTP
# (empty output - SMTP variables not set)
```

### Root Cause
The `docker-compose.yml` on the dev VPS was missing `env_file: .env` on the `app` service. Docker Compose does NOT automatically load `.env` into container environment — it only uses `.env` for variable substitution within the compose file itself.

### Fix
```yaml
services:
  app:
    env_file: .env    # <-- REQUIRED
    # ... rest
```

### Verification
```bash
docker exec payntra-app env | grep SMTP
# SMTP_HOST=mail.cyberslide.net
# SMTP_PORT=587
# SMTP_SECURE=false
# SMTP_USER=support@madeat2am.in
# SMTP_PASS=Cris0037.
# SMTP_FROM="Support <support@madeat2am.in>"
```

---

## Issue 2: `.env` Had Placeholder Values Instead of Actual Secrets

### Symptom
```bash
docker exec payntra-app env | grep DATABASE
# DATABASE_URL=postgresql://payntra:***@db:5432/payntra
# (literal "***" instead of password)
```

### Root Cause
The `.env` file on the dev VPS was created during initial scaffold with masked/placeholder values for security, but was never updated with actual credentials.

### Fix
```env
# WRONG (placeholder):
DATABASE_URL=postgresql://payntra:***@db:5432/payntra
SMTP_PORT=465
SMTP_SECURE=true

# RIGHT (actual values):
DATABASE_URL=postgresql://payntra:payntra@db:5432/payntra
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=support@madeat2am.in
SMTP_PASS=Cris0037.
SMTP_FROM="Support <support@madeat2am.in>"
```

---

## Complete Verification Checklist After Deploy

```bash
# 1. Check container env vars
docker exec <container> env | grep -E 'SMTP|DATABASE'

# 2. Test SMTP connectivity from inside container
docker exec <container> node -e "
const nodemailer = require('nodemailer');
const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST,
  port: parseInt(process.env.SMTP_PORT),
  secure: process.env.SMTP_SECURE === 'true',
  auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
  tls: { minVersion: 'TLSv1.2', rejectUnauthorized: false }
});
transporter.verify((err, success) => {
  if (err) console.error('Error:', err.code, err.message);
  else console.log('Success:', success);
});
"

# 3. Test DB connectivity
docker exec <container> node -e "
const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 1 });
pool.query('SELECT 1 as test', (err, res) => {
  if (err) console.error('Error:', err.code, err.message);
  else console.log('DB Success:', res.rows);
  pool.end();
});
"

# 4. Full API test
curl -X POST https://payntra.terrybot.top/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"chris@madeat2am.in"}'
# Should return {"ok":true}
```

---

## Why This Happened

1. **Control VPS vs Dev VPS sync drift:** The `docker-compose.yml` and `.env` files on the dev VPS were from an older scaffold state, not the current control VPS version.

2. **`.env` scaffold template uses placeholders:** The initial scaffold created `.env` with masked passwords for safety, expecting the operator to update them. This step was skipped.

3. **`env_file` was in the template but lost during manual edits:** The original template had it, but manual edits to the dev VPS copy removed it.

---

## Prevention Checklist

- [ ] Every `docker-compose.yml` service that needs env vars MUST have `env_file: .env`
- [ ] `.env` on dev VPS MUST contain actual values, not placeholders
- [ ] After any deploy, run the verification checklist above
- [ ] Consider using a secret management approach (1Password CLI, Doppler, etc.) for production
- [ ] When updating `.env` locally, also update the dev VPS copy via `project.sh deploy` or manual sync