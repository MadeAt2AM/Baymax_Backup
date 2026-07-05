# Payntra Project Index — Reference Example

**Created:** 2026-07-05  
**Location:** `/root/projects/payntra/PROJECT_INDEX.md`  
**Project:** Monthly Expense Ledger & Financial Dashboard  
**Stack:** React (Vite) + TypeScript + Tailwind + PostgreSQL + Fastify (Node.js)

---

## Structure Summary

```
/root/projects/payntra/
├── .env                      # Runtime secrets (SMTP, JWT, DB) — NOT in git
├── .gitignore
├── docker-compose.yml        # dev VPS stack: app + db + Caddy reverse proxy
├── Dockerfile                # Multi-stage build with typecheck/test gates
├── README.md                 # Full project documentation
├── PROJECT_INDEX.md          # ← THIS FILE
│
├── client/                   # React + Vite + TypeScript + Tailwind
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── tsconfig.test.json
│   ├── vitest.config.ts
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── lib/              # API client, hooks, types, utilities
│       ├── context/          # AuthContext.tsx
│       ├── components/
│       │   ├── ui/           # Primitives: Button, Input, Card, Modal, Toast, Badge, ThemeToggle, Spinner
│       │   ├── layout/       # AppShell, RequireAuth, RedirectIfAuthed
│       │   └── ledger/       # LedgerTable, StatusToggle, KpiCard, MonthNav, AddItemModal, DeleteCell
│       ├── pages/
│       │   ├── auth/         # Login, Signup, ForgotPassword, ResetPassword
│       │   ├── DashboardPage.tsx   # /ledger/:monthYear — KPIs, table, month nav, add/delete
│       │   ├── TemplatesPage.tsx   # /templates — lifetime baseline CRUD + [+ Add] to ledger
│       │   └── ProfilePage.tsx     # /profile — email/password change (requires current pwd)
│       └── test/             # Vitest + Testing Library (Button, Input, Card, Modal, ThemeToggle, monthMath)
│
├── server/                   # Fastify + TypeScript + Zod + pg
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.test.json
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── index.ts          # Fastify boot, route wiring, route wiring, /api/health
│   │   ├── config.ts         # Zod-validated env schema (Env, cookieOptions)
│   │   ├── db.ts             # pg.Pool singleton, query(), withTransaction()
│   │   ├── mailer.ts         # nodemailer transporter (lazy), sendResetEmail()
│   │   ├── auth.ts           # bcryptjs (10 rounds), JWT sign/verify, cookie helpers
│   │   ├── middleware/
│   │   │   └── requireAuth.ts # JWT verification → req.userId
│   │   ├── routes/
│   │   │   ├── auth.ts       # POST /signup, /login, /logout, /forgot-password, /reset-password
│   │   │   ├── ledger.ts     # GET /:monthYear (rollover), POST /:monthYear/items, PATCH /items/:id, DELETE /items/:id
│   │   │   ├── templates.ts  # GET/POST/PATCH/DELETE /templates, POST /:id/toggle
│   │   │   └── profile.ts    # PUT /profile/email, PUT /profile/password
│   │   ├── schemas/
│   │   │   ├── auth.ts       # Signup/Login/Forgot/Reset Zod schemas
│   │   │   ├── ledger.ts     # LedgerItemPatch, CreateLedgerItem (superRefine either/or), LedgerItem, LedgerResponse, MonthYearParam
│   │   │   └── templates.ts  # TemplateCreate, TemplatePatch, AmountSchema
│   │   └── services/
│   │       ├── monthMath.ts  # addMonths/subMonths/format (year-boundary safe)
│   │       ├── rollover.ts   # getOrCreateLedger — transactional clone from prior month OR active templates
│   │       ├── ledgerItems.ts # updateLedgerItem (JOIN ownership, atomic UPDATE…RETURNING)
│   │       ├── createLedgerItem.ts # create from templateId OR name/amount, optional template promotion
│   │       ├── deleteLedgerItem.ts # DELETE … USING monthly_ledgers (ownership JOIN)
│   │       └── templates.ts  # CRUD for expense_templates
│   └── test/                 # Vitest stubs pg.Pool — 45/45 passing
│       ├── monthMath.test.ts
│       ├── ledgerItems.test.ts
│       ├── templates.test.ts
│       ├── createLedgerItem.test.ts
│       └── deleteLedgerItem.test.ts
│
├── db/
│   └── init.sql              # PRD schema: users, expense_templates, monthly_ledgers, ledger_items
│
└── e2e/
    ├── playwright.config.ts  # Targets https://payntra.terrybot.top
    └── authFlow.spec.ts      # signup → login → dashboard → toggle → month nav → templates CRUD → profile → logout
```

---

## Key Concepts & Invariants

| Concept | Rule | Enforced Where |
|---------|------|----------------|
| **Lifetime baseline vs monthly snapshot** | `expense_templates` = source of truth. `monthly_ledgers` + `ledger_items` = static historical copies per month. Templates NEVER mutated by ledger ops. | `rollover.ts`, `createLedgerItem.ts` (templateId-only path), `templates.ts` |
| **Rollover engine** | On first access to `/api/ledger/:monthYear`: if no ledger exists, clone from prior month's `ledger_items` (status→PENDING). If no prior month, clone from active `expense_templates`. Single transaction, `SELECT FOR UPDATE`. | `rollover.ts:getOrCreateLedger()` |
| **Ownership** | Every mutation joins through `monthly_ledgers.user_id` in the SAME SQL statement. No SELECT-then-UPDATE window. Missing + not-yours both → 404 (no enumeration). | `ledgerItems.ts`, `deleteLedgerItem.ts`, `createLedgerItem.ts`, `templates.ts` |
| **Optimistic UI** | Client applies change locally, fires network request in background, reconciles on success, rolls back on failure. All three mutations (toggle, edit, create, delete) follow identical pattern. | `useLedger.ts`, `useTemplates.ts` |
| **DELETE = 204 No Content** | `apiFetch` already handles empty body. Server returns 204, client treats as success. | `ledgerApi.ts`, `useLedger.ts`, `mailer.ts` |
| **Auth** | JWT in HTTPOnly cookie (SameSite=Lax, Secure, 30d TTL, domain=payntra.terrybot.top). bcryptjs 10 rounds. Reset token = 64-char hex, 5-min TTL, 410 Gone on expiry. | `auth.ts`, `config.ts:cookieOptions` |
| **SMTP** | `mail.cyberslide.net:587`, STARTTLS (`secure=false`), user=`support@madeat2am.in`, pass=`Cris0037.`, from=`"Support <support@madeat2am.in>"`. Known issue: dev VPS outbound blocked → emails may not arrive. Reset secrets still written to `users.reset_secret` for manual testing. | `.env`, `mailer.ts` |

---

## Deployment (GitHub Method)

| Step | Command | What Happens |
|------|---------|--------------|
| 1. Build gates | `cd server && npm run typecheck && npm test` | 45/45 tests must pass |
| | `cd client && tsc -b && npm run build` | Production bundle emitted |
| 2. Commit & push | `git add ... && git commit -m "..." && git push origin main` | Triggers GitHub webhook |
| 3. Webhook fires | `POST /hooks/github-push` on dev VPS (147.79.18.32:9000) | Runs `project_dev.sh redeploy` |
| 4. Deploy | `docker compose build && docker compose up -d` | New container + Caddy reload |
| 5. Live | `https://payntra.terrybot.top` | New bundle served |

**Webhook secret:** `/root/.hermes/.dev-vps-webhook.secret` (control VPS) ↔ `/etc/webhook/hooks` (dev VPS)

**Container names:** `payntra-app` (API + static), `payntra-db` (Postgres 16)

**Networks:** `payntra-net` (internal, MTU 1400), `web` (external — Caddy on `web` reverse proxies to `payntra-app:3000`)

---

## Testing Commands

```bash
# Server (run from /root/projects/payntra/server)
npm run typecheck          # tsc -p tsconfig.test.json
npm test                   # vitest run — 45 tests

# Client (run from /root/projects/payntra/client)
tsc -b                     # TypeScript build
npm run build              # tsc -b && vite build
npm test                   # vitest run (1 known flaky Input test)

# E2E (run from /root/projects/payntra)
npx playwright test e2e/authFlow.spec.ts
```

---

## API Quick Reference

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| POST | `/api/auth/signup` | ❌ | `{email, password}` | 201 `{ok:true}` / 409 |
| POST | `/api/auth/login` | ❌ | `{email, password}` | 200 `{ok:true}` + cookie / 401 |
| POST | `/api/auth/logout` | ✅ | — | 200 `{ok:true}` |
| POST | `/api/auth/forgot-password` | ❌ | `{email}` | 200 `{ok:true}` (always) |
| POST | `/api/auth/reset-password` | ❌ | `{secret, newPassword}` | 200 / 410 / 400 |
| GET | `/api/ledger/:monthYear` | ✅ | — | 200/201 `{monthYear, created, items[]}` |
| POST | `/api/ledger/:monthYear/items` | ✅ | `{templateId}` OR `{name, amount, notes?, createTemplate?}` | 201 `{item}` / 400 / 403 |
| PATCH | `/api/ledger/items/:id` | ✅ | `{status?, amount?, notes?}` | 200 `{item}` / 404 |
| DELETE | `/api/ledger/items/:id` | ✅ | — | **204** / 404 |
| GET | `/api/templates` | ✅ | — | 200 `{templates[]}` |
| POST | `/api/templates` | ✅ | `{name, defaultAmount}` | 201 `{template}` |
| PATCH | `/api/templates/:id` | ✅ | `{name?, defaultAmount?, isActive?}` | 200 `{template}` |
| DELETE | `/api/templates/:id` | ✅ | — | 200 `{ok:true}` |
| POST | `/api/templates/:id/toggle` | ✅ | — | 200 `{template}` |
| PUT | `/api/profile/email` | ✅ | `{email, currentPassword}` | 200 / 401 |
| PUT | `/api/profile/password` | ✅ | `{currentPassword, newPassword}` | 200 / 401 |

---

## Design System (Tailwind + CSS Variables)

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--color-surface` | `#ffffff` | `#111827` | Page background |
| `--color-surface-raised` | `#f9fafb` | `#1f2937` | Cards, modals |
| `--color-surface-border` | `#e5e7eb` | `#374151` | Borders |
| `--color-ink` | `#111827` | `#f9fafb` | Primary text |
| `--color-ink-muted` | `#6b7280` | `#9ca3af` | Secondary text |
| `--color-crimson-500` | `#D32F2F` | `#D32F2F` | Brand accent (MadeAt2AM) |
| `--color-success` | `#16a34a` | `#22c55e` | PAID status, positive KPIs |
| `--color-warning` | `#f59e0b` | `#fbbf24` | PENDING status |
| `--color-danger` | `#dc2626` | `#ef4444` | Destructive actions |

**Tailwind rule:** 95% utilities. `custom.css` reserved for:
- `dense-table` (tight `td`/`th` padding)
- Custom scrollbar (`scroll-thin`)
- Animations (`animate-fade-in`, `animate-slide-up`, `animate-modal`, `animate-overlay`)

**Fonts:** SF Pro Display (headings), JetBrains Mono (code/monospace)

---

## Known Issues / Technical Debt

1. **SMTP outbound blocked on dev VPS** — `mail.cyberslide.net:587` (and 465) times out from 147.79.18.32. Workaround: reset secrets written to `users.reset_secret`; test via direct DB read + `/reset?secret=...`. Future: swap to Resend/Postmark/SES (HTTPS, never blocked).

2. **Input.test.tsx flaky** — `userEvent.type` timing issue; passes on retry. Pre-existing, unrelated to recent changes.

3. **Playwright e2e expects live URL** — tests hit `https://payntra.terrybot.top` directly. Need a running deploy to run.

4. **Dockerfile build cache** — `npm test` runs in build; if tests flake, deploy fails. Current suite is stable.

5. **Docker MTU mismatch** — Fixed by adding `driver_opts: com.docker.network.driver.mtu: "1400"` to `payntra-net` (host eth0 MTU is 1400).

---

## How to Use This Index

- **Need to find where X lives?** Search this file for the keyword (e.g. "rollover", "optimistic", "DELETE", "cookie").
- **Adding a new feature?** Check "Key Concepts" for invariants you must preserve.
- **Deploying?** Follow "Deployment" table — the push is the trigger, webhook does the rest.
- **Debugging a bug?** Trace from route → service → DB. The service layer is where ownership + atomicity live.
- **Deploying?** Follow "Deployment" table — the push is the trigger, webhook does the rest.

---

> **Maintained by:** Baymax (IT Infrastructure Agent)  
> **Last updated:** 2026-07-05 — after per-row delete feature + SMTP config fix + MTU fix  
> **Project:** Payntra — Monthly Expense Ledger & Financial Dashboard  
> **Live:** https://payntra.terrybot.top  
> **Repo:** MadeAt2AM/payntra (private)