# <PROJECT_NAME>

> Replace this block with a one-paragraph summary of what this app/site does, who it's for, and what tech stack it uses.

---

## ⚡ Deploy

This folder is the **single source of truth** for this project. The deploy pipeline pulls it from GitHub on push and redeploys automatically on the dev VPS.

**Local development:** edit files here, commit, push. Pipeline runs in <2 minutes.
**Live URL:** `https://<PROJECT_NAME>.terrybot.top` (created automatically on first deploy).

### Quick commands (run from project root)

| Command | What it does |
|---|---|
| `/root/.hermes/bin/project.sh status` | Show project state, last deploy, GitHub status |
| `/root/.hermes/bin/project.sh push "msg"` | Stage all + commit + push to GitHub |
| `/root/.hermes/bin/project.sh deploy` | Force a redeploy without pushing |
| `/root/.hermes/bin/project.sh logs` | Tail logs from the dev VPS containers |

### Push → redeploy flow

```
[You commit here]
       │
       ▼
  git push origin main
       │
       ▼
  GitHub webhook hits dev-vps:9000
       │
       ▼
  webhook → /srv/projects/<PROJECT_NAME>/git pull + docker compose up --build
       │
       ▼
  Caddy reloads, HTTPS stays live, new version is the URL
```

---

## 🗂 What's in here

```
.
├── README.md              ← you are here
├── Dockerfile             ← how to containerise this thing
├── docker-compose.yml     ← dev-VPS deployment definition
├── app/                   ← your actual code
├── .env.example           ← template; .env is gitignored
└── .git/                  ← GitHub mirror under MadeAt2AM/<PROJECT_NAME>
```

---

## 📋 Project metadata

| | |
|---|---|
| **Repo** | `MadeAt2AM/<PROJECT_NAME>` (private) |
| **Domain** | `<PROJECT_NAME>.terrybot.top` |
| **Dev VPS path** | `/srv/projects/<PROJECT_NAME>/` |
| **Container name** | `<PROJECT_NAME>-app` |
| **Internal port** | _set in docker-compose.yml_ |
| **Created** | YYYY-MM-DD |
| **Last deploy** | _updated automatically by `project.sh`_ |

---

## 🔧 Operational notes

_Document anything non-obvious here: env vars that must be present, scheduled jobs, external services it depends on, known gotchas, etc._
