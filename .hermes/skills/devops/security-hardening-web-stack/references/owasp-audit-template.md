# OWASP Top 10 (2021) Audit Template

A reusable audit template based on the SYNTRA v2 audit (2026-07-14).
Copy this template, fill in the findings, and ship as `docs/SECURITY_AUDIT.md`
in the project repo.

## Severity scale

| Severity | Meaning | Response time |
|---|---|---|
| CRITICAL | Active exploit path, immediate data exposure | Hours |
| HIGH | Likely exploitation vector, large blast radius | Days |
| MEDIUM | Real vulnerability, requires preconditions | Weeks |
| LOW | Hardening gap, defence-in-depth improvement | Quarters |
| INFO | Documented choice, no action required | — |

## Executive summary

```
| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0     | —      |
| HIGH     | 3     | Fixed  |
| MEDIUM   | 5     | Fixed  |
| LOW      | 4     | Documented |
| INFO     | 6     | Documented |
```

## A01 — Broken Access Control

| # | Severity | Finding | Status |
|---|---|---|---|
| 1.1 | HIGH | Wildcard `cors()` allows any origin to call API from a browser | **Fixed** — explicit allowlist via `ALLOWED_ORIGINS` env |
| 1.2 | MEDIUM | `companies/:id` PATCH uses `requireRole("admin")` but no `companyId` scoping in the query | **Fixed** — verified via RBAC test |
| 1.3 | INFO | Invitation tokens returned in GET response body | Documented — frontend should redact |
| 1.4 | LOW | `users.companyId` filter correctly applied everywhere | Keep enforcing |

## A02 — Cryptographic Failures

| # | Severity | Finding | Status |
|---|---|---|---|
| 2.1 | LOW | bcryptjs cost 12, JWT HS256, 64+ byte secret | No change |
| 2.2 | INFO | Tokens in `localStorage` (not httpOnly cookies) | Mitigated via CSP |
| 2.3 | MEDIUM | `SESSION_SECRET` rotates on redeploy only | Documented rotation procedure |
| 2.4 | INFO | TLS 1.3 via Caddy + LE | No change |

## A03 — Injection

| # | Severity | Finding | Status |
|---|---|---|---|
| 3.1 | INFO | All SQL via Drizzle parameterised queries | No change |
| 3.2 | INFO | All input via Zod schemas | No change |

## A04 — Insecure Design

| # | Severity | Finding | Status |
|---|---|---|---|
| 4.1 | HIGH | **No rate-limit on /auth/login, /forgot-password, /reset-password** | **Fixed** — dual limiter |
| 4.2 | MEDIUM | `/forgot-password` side-effect reveals account existence | Documented (intentional) |
| 4.3 | LOW | No max attempts on forgot-password (could spam email gateway) | **Fixed** — global apiLimiter applies |

## A05 — Security Misconfiguration

| # | Severity | Finding | Status |
|---|---|---|---|
| 5.1 | HIGH | **No security headers** | **Fixed** — three-layer |
| 5.2 | HIGH | **Wildcard `cors()`** | **Fixed** — allowlist |
| 5.3 | MEDIUM | No `express.json({ limit })` | **Fixed** — 256kb cap |
| 5.4 | MEDIUM | Global error handler leaks `err.message` | **Fixed** — generic 500 |
| 5.5 | LOW | `X-Powered-By: Express` leaks framework | **Fixed** — `app.disable` |
| 5.6 | INFO | Container exposes no host ports; Caddy is the only external entry | No change |

## A06 — Vulnerable & Outdated Components

| # | Severity | Finding | Status |
|---|---|---|---|
| 6.1 | LOW | All deps current at audit time | Run `pnpm audit` quarterly |
| 6.2 | INFO | Debian-slim has wider CVE surface than Alpine | Trade-off accepted |

## A07 — Identification & Authentication Failures

| # | Severity | Finding | Status |
|---|---|---|---|
| 7.1 | HIGH | No rate-limit on login | **Fixed** |
| 7.2 | LOW | JWT expiry? (verify `signToken()` `expiresIn`) | Audit manually |
| 7.3 | LOW | No MFA/2FA | Documented — feature not in scope |
| 7.4 | INFO | Password min 8 chars (NIST baseline) | No change |

## A08 — Software & Data Integrity Failures

| # | Severity | Finding | Status |
|---|---|---|---|
| 8.1 | INFO | Webhook HMAC verified | No change |
| 8.2 | LOW | No image-signing on Docker images | Documented |

## A09 — Logging & Monitoring Failures

| # | Severity | Finding | Status |
|---|---|---|---|
| 9.1 | INFO | Pino strips body/headers/query — creds never logged | No change |
| 9.2 | MEDIUM | No SIEM/alerting integration | Documented |
| 9.3 | LOW | No admin audit log | Documented |

## A10 — Server-Side Request Forgery (SSRF)

| # | Severity | Finding | Status |
|---|---|---|---|
| 10.1 | INFO | Domain verify uses `dns.resolve*` only (no HTTP fetch) | No change |

## Cross-cutting

### Credential / secret leakage

| # | Severity | Finding | Status |
|---|---|---|---|
| L1 | INFO | No API keys in frontend source | No change |
| L2 | INFO | Auth tokens in localStorage by design | No change |
| L3 | INFO | Test-user PII only | No change |
| L4 | MEDIUM | `pnpm audit` not in CI | Documented |

### TLS / HTTPS

| # | Severity | Finding | Status |
|---|---|---|---|
| T1 | INFO | TLS 1.3 via Caddy + LE | No change |
| T2 | LOW | HSTS not set | **Fixed** — `max-age=31536000; includeSubDomains` |

## Recommendations

1. Add JWT expiry check
2. Add MFA for admin/manager
3. Add audit log for mutating platform-admin actions
4. Move auth tokens to httpOnly Secure cookies
5. Add `pnpm audit` to CI
6. Enable Docker Content Trust for production
7. Add SIEM integration (Logtail / Datadog / Sentry)
8. Quarterly review of this document