---
name: project-index-authoring
description: |
  Create and maintain a PROJECT_INDEX.md file for every web project.
  This is a living map of the codebase — structure, key invariants, API,
  deployment, testing, and design tokens — so you never need to grep
  the whole tree to find something.
category: software-development
tags: [documentation, navigation, project-management, web-development]
---

# Project Index Authoring Skill

## When to Use

**Always** when starting a new web project (React/Vue/Svelte + any backend),
or when taking over an existing project that lacks a navigational index.

The index should be created at `/root/projects/<name>/PROJECT_INDEX.md`
and committed to git alongside the codebase.

---

## What Goes In a PROJECT_INDEX.md

### 1. Repository Structure (Tree)
A collapsed tree showing every non-trivial file and directory,
grouped by layer (client/server/db/infra/tests). One-line annotations
for each file explaining its responsibility.

### 2. Key Concepts & Invariants Table
| Concept | Rule | Enforced Where |
|---------|------|----------------|
| e.g. "Optimistic UI" | "Client applies locally, reconciles on success, rolls back on failure" | `useLedger.ts`, `useTemplates.ts` |
| e.g. "Ownership" | "Every mutation joins through user_id in same SQL statement" | `ledgerItems.ts`, `deleteLedgerItem.ts` |

This is the **most valuable section** — it captures the architectural
decisions that would otherwise live only in your head.

### 3. Deployment Workflow
Step-by-step from code change → live URL. Include:
- Build gate commands
- Git/webhook trigger
- What the deploy script does
- Container names, networks, ports

### 4. Testing Commands
Copy-pasteable commands for:
- Server typecheck + unit tests
- Client typecheck + build + unit tests
- E2E tests

### 5. API Quick Reference
Table: Method | Path | Auth | Body | Response
Enough to write a frontend call without opening the route file.

### 6. Design System Tokens
If using Tailwind + CSS variables: table of tokens with light/dark values
and usage notes. Include the "95% utilities / 5% custom.css" rule.

### 7. Known Issues / Technical Debt
Honest list of things that are broken, flaky, or deferred.
Prevents the next person from wasting time on known problems.

### 8. How to Use This Index
A short "user guide" for the index itself — search tips, where to look
for common tasks.

---

## Maintenance Rules

1. **Update on every structural change** — new route, new service,
   new component category, new invariant. If you'd grep for it later,
   it belongs in the index.

2. **Keep it concise** — the index is a map, not the territory.
   Link to files, don't duplicate their content.

3. **Commit it** — `PROJECT_INDEX.md` lives in the repo root,
   tracked by git. Review it in PRs like any other file.

4. **One per project** — `/root/projects/<name>/PROJECT_INDEX.md`.
   Never a global index; every project has its own architecture.

---

## Template (Minimal Viable Index)

```markdown
# <Project Name> — Project Index

## Repository Structure
```
<tree with annotations>
```

## Key Concepts & Invariants
| Concept | Rule | Enforced Where |
|---------|------|----------------|

## Deployment
| Step | Command | What Happens |

## Testing Commands
```bash
# server
# client
# e2e
```

## API Quick Reference
| Method | Path | Auth | Body | Response |

## Design System
| Token | Light | Dark | Usage |

## Known Issues
1. ...

## How to Use This Index
...
```

---

## Example: Payntra's Index

See `/root/projects/payntra/PROJECT_INDEX.md` — created 2026-07-05.
Covers: React+Fastify stack, rollover engine, optimistic mutations,
JWT auth, SMTP config, GitHub webhook deploy, 45 server tests,
Tailwind + CSS variables design tokens, known SMTP block on VPS.

---

## Anti-Patterns to Avoid

- ❌ **Putting it in a wiki/Notion** — it must live in the repo,
  versioned with the code it describes.
- ❌ **Writing it once and forgetting** — stale index is worse than none.
- ❌ **Duplicating README.md** — README is for humans landing on the
  repo; INDEX is for developers navigating the code.
- ❌ **Over-documenting** — if a file is self-explanatory (e.g.
  `Button.tsx`), a one-line annotation in the tree is enough.

---

## Quick Start (New Project)

```bash
# 1. Scaffold the project structure
mkdir -p /root/projects/myapp/{client,server,db,e2e}

# 2. Create the index from the template above
cat > /root/projects/myapp/PROJECT_INDEX.md << 'EOF'
# myapp — Project Index
... (fill in as you build)
EOF

# 3. Commit immediately
cd /root/projects/myapp && git add PROJECT_INDEX.md && git commit -m "docs: add project index"
```

Then update it every time you add a route, service, component,
or architectural decision.