-----

## name: dokploy
description: >
Use this skill whenever you need to deploy, manage, or interact with applications
on a Dokploy instance. Triggers include: deploy a web app, create a new project,
set environment variables, check deployment status, start/stop/redeploy an app,
add a domain, manage databases (Postgres, MySQL, Redis, MongoDB, MariaDB),
configure build settings, view deployment logs, or any operation against a
self-hosted Dokploy panel. Always read this skill before touching the Dokploy API.

# Dokploy Skill for Hermes

This skill governs all interactions between Hermes and a Dokploy instance. It covers API patterns, safety guardrails, scope restrictions, and step-by-step workflows for common deployment operations.

-----

## 1. Environment Setup

All credentials come from the `.env` file. **Never hardcode credentials.**

```
DOKPLOY_URL=https://panel.cyberslide.net/api   # always the full /api base, no trailing slash
DOKPLOY_API_KEY=<your-api-key>                 # from Dokploy profile → API Tokens
DOKPLOY_ALLOWED_PROJECTS=project-a,project-b  # comma-separated project names you may touch
```

Read these at the start of every Dokploy task:

```python
import os
DOKPLOY_URL     = os.environ["DOKPLOY_URL"].rstrip("/")   # e.g. https://panel.cyberslide.net/api
DOKPLOY_API_KEY = os.environ["DOKPLOY_API_KEY"]
ALLOWED_PROJECTS = [p.strip() for p in os.environ.get("DOKPLOY_ALLOWED_PROJECTS", "").split(",") if p.strip()]
```

-----

## 2. ⚠️ STRICT SAFETY GUARDRAILS

These rules are **non-negotiable**. Violating them could destroy production apps.

### 2.1 Scope restriction — ALLOWED_PROJECTS whitelist

- **Before ANY write operation** (deploy, delete, stop, update env, update config, add domain, etc.) you MUST verify the target project name is in `ALLOWED_PROJECTS`.
- If `ALLOWED_PROJECTS` is empty, **abort with an error** — never operate with an unconstrained scope.
- Read operations (`project.all`, `application.one`, etc.) are permitted without whitelist check, but only to gather information needed for a whitelisted operation.

```python
def assert_project_allowed(project_name: str):
    if project_name not in ALLOWED_PROJECTS:
        raise PermissionError(
            f"GUARDRAIL: Project '{project_name}' is not in DOKPLOY_ALLOWED_PROJECTS. "
            f"Allowed: {ALLOWED_PROJECTS}. Aborting."
        )
```

### 2.2 No destructive ops without explicit confirmation

Operations that are **irreversible** require explicit user confirmation before execution:

- `application.delete`
- `project.delete` (never use unless user explicitly says “delete the project”)
- `application.clearDeployments`
- `compose.delete`
- Any database `.delete` endpoint

Destructive confirmation check:

```python
def confirm_destructive(action: str, target: str) -> bool:
    # In agent context: raise and ask user to confirm by re-running with confirm=True
    raise RuntimeError(
        f"DESTRUCTIVE ACTION BLOCKED: '{action}' on '{target}'. "
        "Re-invoke this task with explicit confirmation to proceed."
    )
```

### 2.3 Never touch infrastructure-level settings

- Do NOT call `server.*`, `settings.*`, `admin.*`, `swarm.*`, `cluster.*` endpoints unless a user explicitly asks and the operation is read-only.
- Do NOT modify Docker daemon settings, Traefik global config, or SSL certificate authorities.

### 2.4 Env var safety

- Never log or print the contents of `env` variables returned by the API. Mask secrets.
- When setting env vars via `application.saveEnvironment`, only append/update the keys the user specified — never overwrite the entire env block unless instructed.

-----

## 3. API Client

All requests use:

- Base URL: `{DOKPLOY_URL}/api`
- Auth header: `x-api-key: {DOKPLOY_API_KEY}`
- Content-Type: `application/json`

```python
import requests, json

def dokploy(method: str, endpoint: str, payload: dict = None, params: dict = None):
    """
    method   : "GET" or "POST"
    endpoint : e.g. "project.all" or "application.deploy"
    payload  : JSON body for POST requests
    params   : query params for GET requests
    """
    url = f"{DOKPLOY_URL}/{endpoint}"   # DOKPLOY_URL already ends at /api
    headers = {
        "x-api-key": DOKPLOY_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resp = requests.request(
        method,
        url,
        headers=headers,
        json=payload,
        params=params,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Dokploy API error {resp.status_code}: {resp.text}")
    return resp.json()
```

-----

## 4. Common Workflows

### 4.1 List all projects and find IDs

```python
projects = dokploy("GET", "project.all")
for p in projects:
    print(p["projectId"], p["name"])
```

### 4.2 Create a new project

```python
assert_project_allowed("my-new-project")  # must be in allowed list

result = dokploy("POST", "project.create", {
    "name": "my-new-project",
    "description": "Created by Hermes"
})
project_id = result["projectId"]
```

### 4.3 Create an application inside a project

You need the `environmentId` from the project object (Dokploy uses environments per project):

```python
# First fetch the project to get its environment ID
project_data = dokploy("GET", "project.one", params={"projectId": project_id})
# Each project has a default environment; find it:
env_id = project_data["environments"][0]["environmentId"]

app = dokploy("POST", "application.create", {
    "name": "my-app",
    "environmentId": env_id,
})
app_id = app["applicationId"]
```

### 4.4 Configure GitHub source

```python
dokploy("POST", "application.saveGithubProvider", {
    "applicationId": app_id,
    "repository": "my-repo",
    "owner": "my-org",
    "branch": "main",
    "buildPath": "/",
    "triggerType": "push",
})
```

### 4.5 Set build type (nixpacks recommended for Node/Python/etc.)

```python
dokploy("POST", "application.saveBuildType", {
    "applicationId": app_id,
    "buildType": "nixpacks",      # or "dockerfile", "heroku_buildpacks"
    "dockerfile": None,
    "dockerContextPath": None,
    "dockerBuildStage": None,
    "herokuVersion": None,
    "railpackVersion": None,
})
```

### 4.6 Set environment variables

**Never replace all env vars unless the user asked.** Fetch existing first, merge, then save:

```python
existing = dokploy("GET", "application.one", params={"applicationId": app_id})
existing_env = existing.get("env") or ""

# Merge new vars into existing
new_vars = {"PORT": "3000", "NODE_ENV": "production"}
env_lines = {k: v for k, v in (line.split("=", 1) for line in existing_env.splitlines() if "=" in line)}
env_lines.update(new_vars)
merged_env = "\n".join(f"{k}={v}" for k, v in env_lines.items())

dokploy("POST", "application.saveEnvironment", {
    "applicationId": app_id,
    "env": merged_env,
    "buildArgs": None,
    "buildSecrets": None,
    "createEnvFile": False,
})
```

### 4.7 Deploy an application

```python
dokploy("POST", "application.deploy", {"applicationId": app_id})
print("Deployment triggered. Check logs in Dokploy panel.")
```

### 4.8 Redeploy (force rebuild)

```python
dokploy("POST", "application.redeploy", {
    "applicationId": app_id,
    "title": "Manual redeploy by Hermes",
})
```

### 4.9 Start / Stop an application

```python
dokploy("POST", "application.stop",  {"applicationId": app_id})
dokploy("POST", "application.start", {"applicationId": app_id})
```

### 4.10 Add a domain to an application

```python
dokploy("POST", "domain.create", {
    "applicationId": app_id,
    "host": "myapp.cyberslide.net",
    "https": True,
    "port": 3000,
    "path": "/",
    "certificateType": "letsencrypt",
})
```

### 4.11 Check application status

```python
app = dokploy("GET", "application.one", params={"applicationId": app_id})
print("Status:", app["applicationStatus"])   # idle | running | done | error
print("App name:", app["appName"])
```

### 4.12 Get deployment logs

```python
deployments = dokploy("GET", "deployment.all", params={"applicationId": app_id})
latest = deployments[0] if deployments else None
if latest:
    print("Latest deployment status:", latest["status"])
    print("Log:", latest.get("log", "")[:2000])  # truncate for display
```

### 4.13 Create a database (Postgres example)

```python
assert_project_allowed(target_project_name)

db = dokploy("POST", "postgres.create", {
    "name": "myapp-db",
    "environmentId": env_id,
    "databaseName": "myapp",
    "databaseUser": "myapp_user",
})
```

### 4.14 Full end-to-end deploy flow (new app from GitHub)

```python
def deploy_new_app(project_name, app_name, github_owner, github_repo, branch="main",
                   build_type="nixpacks", env_vars: dict = None, domain: str = None):
    """
    Full flow: find project → create app → configure source → set env → deploy → add domain.
    """
    assert_project_allowed(project_name)

    # 1. Find project
    projects = dokploy("GET", "project.all")
    project = next((p for p in projects if p["name"] == project_name), None)
    if not project:
        raise ValueError(f"Project '{project_name}' not found in Dokploy.")
    project_id = project["projectId"]

    # 2. Get environment ID
    project_detail = dokploy("GET", "project.one", params={"projectId": project_id})
    env_id = project_detail["environments"][0]["environmentId"]

    # 3. Create application
    app = dokploy("POST", "application.create", {
        "name": app_name,
        "environmentId": env_id,
    })
    app_id = app["applicationId"]

    # 4. Configure GitHub source
    dokploy("POST", "application.saveGithubProvider", {
        "applicationId": app_id,
        "repository": github_repo,
        "owner": github_owner,
        "branch": branch,
        "buildPath": "/",
        "triggerType": "push",
    })

    # 5. Set build type
    dokploy("POST", "application.saveBuildType", {
        "applicationId": app_id,
        "buildType": build_type,
        "dockerfile": None,
        "dockerContextPath": None,
        "dockerBuildStage": None,
        "herokuVersion": None,
        "railpackVersion": None,
    })

    # 6. Set env vars if provided
    if env_vars:
        env_str = "\n".join(f"{k}={v}" for k, v in env_vars.items())
        dokploy("POST", "application.saveEnvironment", {
            "applicationId": app_id,
            "env": env_str,
            "buildArgs": None,
            "buildSecrets": None,
            "createEnvFile": False,
        })

    # 7. Add domain if provided
    if domain:
        dokploy("POST", "domain.create", {
            "applicationId": app_id,
            "host": domain,
            "https": True,
            "port": 3000,
            "path": "/",
            "certificateType": "letsencrypt",
        })

    # 8. Trigger deployment
    dokploy("POST", "application.deploy", {"applicationId": app_id})

    return {"applicationId": app_id, "appName": app["appName"], "status": "deploying"}
```

-----

## 5. Docker Compose Deployments

For multi-service apps (e.g. app + db + redis in one compose file):

```python
assert_project_allowed(project_name)

compose = dokploy("POST", "compose.create", {
    "name": "mystack",
    "environmentId": env_id,
})
compose_id = compose["composeId"]

# Upload compose file content
dokploy("POST", "compose.update", {
    "composeId": compose_id,
    "composeFile": open("docker-compose.yml").read(),
    "sourceType": "raw",
})

# Deploy
dokploy("POST", "compose.deploy", {"composeId": compose_id})
```

-----

## 6. Rollback

```python
# List recent deployments
deployments = dokploy("GET", "deployment.all", params={"applicationId": app_id})
# Pick a deployment ID to roll back to
rollback_dep_id = deployments[1]["deploymentId"]   # second most recent

dokploy("POST", "rollback.redeploy", {
    "applicationId": app_id,
    "deploymentId": rollback_dep_id,
})
```

-----

## 7. Error Handling

Always wrap API calls and provide actionable errors:

```python
try:
    result = dokploy("POST", "application.deploy", {"applicationId": app_id})
except RuntimeError as e:
    msg = str(e)
    if "401" in msg:
        raise RuntimeError("Dokploy auth failed — check DOKPLOY_API_KEY in .env")
    elif "403" in msg:
        raise RuntimeError("Dokploy access denied — your API key may lack permissions")
    elif "404" in msg:
        raise RuntimeError("Application not found — double-check applicationId")
    else:
        raise
```

-----

## 8. Decision Guide

|User asks to…                |API call(s) to use                                       |
|-----------------------------|---------------------------------------------------------|
|Deploy an existing app       |`application.deploy`                                     |
|Rebuild from scratch         |`application.redeploy`                                   |
|Create new app from GitHub   |Full flow: §4.14                                         |
|Update env vars              |Fetch → merge → `application.saveEnvironment`            |
|Add a custom domain          |`domain.create`                                          |
|Stop an app                  |`application.stop`                                       |
|Start a stopped app          |`application.start`                                      |
|Check why deploy failed      |`deployment.all` → inspect latest log                    |
|Roll back                    |`deployment.all` → `rollback.redeploy`                   |
|Create a Postgres database   |`postgres.create`                                        |
|Deploy a docker-compose stack|`compose.create` → `compose.update` → `compose.deploy`   |
|List all apps in a project   |`project.one` → inspect `applications` array             |
|Delete an app (confirmed)    |`application.delete` (destructive — require confirmation)|

-----

## 9. Quick Reference — Key Endpoints

```
GET  project.all                         # list all projects
GET  project.one?projectId=              # single project with apps + dbs
POST project.create                      # {name, description}
POST application.create                  # {name, environmentId}
GET  application.one?applicationId=      # full app details
POST application.deploy                  # {applicationId}
POST application.redeploy               # {applicationId, title?, description?}
POST application.start                   # {applicationId}
POST application.stop                    # {applicationId}
POST application.delete                  # {applicationId} ⚠️ destructive
POST application.saveGithubProvider      # {applicationId, repository, owner, branch, ...}
POST application.saveBuildType           # {applicationId, buildType, ...}
POST application.saveEnvironment         # {applicationId, env, buildArgs, ...}
POST domain.create                       # {applicationId, host, https, port, ...}
GET  deployment.all?applicationId=       # deployment history + logs
POST rollback.redeploy                   # {applicationId, deploymentId}
POST compose.create                      # {name, environmentId}
POST compose.deploy                      # {composeId}
POST postgres.create                     # {name, environmentId, databaseName, ...}
POST redis.create                        # {name, environmentId}
POST mysql.create                        # {name, environmentId, databaseName, ...}
```

-----

## 10. Checklist Before Every Operation

- [ ] `DOKPLOY_URL` and `DOKPLOY_API_KEY` loaded from env
- [ ] `ALLOWED_PROJECTS` is non-empty
- [ ] Target project name verified against `ALLOWED_PROJECTS`
- [ ] Destructive operations confirmed by user
- [ ] Env vars merged, not overwritten
- [ ] Error handling in place