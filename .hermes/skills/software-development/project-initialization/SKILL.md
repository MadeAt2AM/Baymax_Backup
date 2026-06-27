---
name: project-initialization
description: "Use when starting a new project or dedicated procedure. Creates a standardized folder structure under projects/ with all files contained in one dedicated subfolder."
version: 1.0.0
author: Baymax (Hermes Agent)
license: MIT
metadata:
  hermes:
    tags: [projects, initialization, organization, workflow]
    related_skills: [writing-plans, subagent-driven-development, spike]
---

# Project Initialization Procedure

## Overview

This skill codifies the standard procedure for starting a new project or dedicated procedure. It enforces the organizational principle: **One project = one folder**, with all project-related files contained exclusively within that single folder under the projects directory.

The procedure creates a consistent folder structure, initializes essential files, and establishes clear boundaries to prevent cross-contamination between projects. This eliminates clutter and maintains isolation between separate workstreams.

**Project Root:** `/root/.hermes/projects/<project-name>/`

## When to Use

- Starting a completely new project, product, or dedicated procedure
- Creating a new brand or content channel infrastructure
- Beginning development of a custom solution or web app
- Setting up a dedicated automation or integration workflow
- When user says "start a new project" or "create a project for X"

**Don't use for:**
- Adding files to an existing project (navigate to that project folder directly)
- Temporary experiments (use the `spike` skill instead for throwaway validation)
- Documents that don't belong to any specific project (use appropriate folders like notes, archives)

## Required Information

Before running this procedure, you MUST obtain:

1. **Project Name** (mandatory) - The identifier for the new project. Use lowercase, hyphens for spaces. Examples: `social-media-bot`, `inventory-tracker`, `brand-analytics-dashboard`
2. **Project Type** (optional but recommended) - e.g., `web-app`, `automation`, `data-pipeline`, `content-channel`, `utility-script`
3. **Initial Description** (optional) - One-line summary of what the project does

## Procedure

### Step 1: Determine Project Location

The projects root is: `/root/.hermes/projects/`

This is the standard location for Hermes-managed project folders.

```bash
# Verify the projects directory exists
PROJECTS_ROOT="/root/.hermes/projects"
if [[ ! -d "$PROJECTS_ROOT" ]]; then
    echo "Creating projects root at $PROJECTS_ROOT"
    mkdir -p "$PROJECTS_ROOT"
fi
```

### Step 2: Create Project Folder Structure

Create the main project folder with standardized subdirectories:

```bash
PROJECT_NAME="$1"  # Passed from user input
PROJECT_PATH="${PROJECTS_ROOT}/${PROJECT_NAME}"

# Create the main project directory
mkdir -p "$PROJECT_PATH"

# Create standard subdirectories
mkdir -p "$PROJECT_PATH/src"          # Source code
mkdir -p "$PROJECT_PATH/tests"        # Test files
mkdir -p "$PROJECT_PATH/docs"         # Documentation
mkdir -p "$PROJECT_PATH/config"       # Configuration files
mkdir -p "$PROJECT_PATH/data"         # Data files (if needed)
mkdir -p "$PROJECT_PATH/scripts"      # Utility scripts
mkdir -p "$PROJECT_PATH/assets"       # Static assets (images, templates)
mkdir -p "$PROJECT_PATH/logs"         # Log output (gitignored)
mkdir -p "$PROJECT_PATH/.hermes"      # Hermes-specific project config
```

**Note:** Not all subdirectories need to be used. Empty folders are fine; they establish the convention.

### Step 3: Initialize Project Metadata

Create `PROJECT_PATH/README.md` with project information:

```markdown
# ${PROJECT_NAME}

**Type:** ${PROJECT_TYPE:-unspecified}
**Description:** ${PROJECT_DESCRIPTION:-No description provided}
**Created:** $(date +%Y-%m-%d)
**Owner:** CYBERSLIDE Technologies

## Purpose

[Add project purpose and goals here]

## Structure

- `src/` - Source code and core logic
- `tests/` - Automated tests and test data
- `docs/` - Documentation and notes
- `config/` - Configuration files and environment templates
- `data/` - Data files, datasets, or sample data
- `scripts/` - Utility and deployment scripts
- `assets/` - Static files (images, templates, etc.)
- `logs/` - Runtime logs (gitignored)
- `.hermes/` - Hermes Agent project integration

## Setup

[Add setup instructions]

```

Also create `.hermes/` config if needed:

```bash
# Create Hermes project config (empty placeholder)
touch "$PROJECT_PATH/.hermes/config.yaml"
```

### Step 4: Initialize Git Repository (Optional but Recommended)

If the project will be version-controlled:

```bash
cd "$PROJECT_PATH"
git init

# Create a .gitignore that excludes logs, cache, temp files
cat > "$PROJECT_PATH/.gitignore" << 'EOF'
# Logs
logs/
*.log

# Hermes caches
.hermes/cache/
.hermes/tmp/

# OS/IDE
.DS_Store
.vscode/
.idea/
*.swp

# Python (if applicable)
__pycache__/
*.pyc
venv/
.env

# Node.js (if applicable)
node_modules/
npm-debug.log

# Temporary files
tmp/
temp/
EOF

git add .
git commit -m "Initial project setup: $PROJECT_NAME"
```

**Confirmation Required:** Ask the user before initializing git, or follow their stated preference.

### Step 5: Save Project Record

For cross-session awareness, optionally save a project registry entry:

```bash
# Create a projects index in ~/.hermes/memories/
PROJECTS_INDEX="${HOME}/.hermes/memories/projects_index.json"
if [[ ! -f "$PROJECTS_INDEX" ]]; then
    echo "[]" > "$PROJECTS_INDEX"
fi

# Append project metadata (can be updated by user later)
python3 -c "
import json, datetime, os
path = os.path.expanduser('~/.hermes/memories/projects_index.json')
with open(path, 'r') as f:
    projects = json.load(f)
projects.append({
    'name': '$PROJECT_NAME',
    'path': '$PROJECT_PATH',
    'type': '$PROJECT_TYPE',
    'description': '$PROJECT_DESCRIPTION',
    'created': datetime.datetime.now().isoformat(),
    'git_initialized': $([[ -d "$PROJECT_PATH/.git" ]] && echo true || echo false)
})
with open(path, 'w') as f:
    json.dump(projects, f, indent=2)
print(f'Project registered in {path}')
"
```

### Step 6: Report Success

Provide a clear summary:

```
Project initialized successfully at: /root/.hermes/projects/<project-name>/

Structure created:
  src/      - Source code
  tests/    - Tests
  docs/     - Documentation
  config/   - Configuration
  data/     - Data files
  scripts/  - Utilities
  assets/   - Static assets
  logs/     - Log output (gitignored)
  .hermes/  - Hermes config

Next steps:
  1. Navigate to the project folder: cd /root/.hermes/projects/<project-name>/
  2. Add project-specific files to the appropriate subdirectories
  3. Keep all project work contained within this folder
  4. Use README.md to document setup, usage, and purpose
```

## Common Pitfalls

1. **Placing project files outside the project folder.**  
   **Fix:** Always work from within the project root. Use relative paths to reference files within the project structure.

2. **Creating project folders in the wrong location.**  
   **Fix:** The standard location is `~/projects/`. Double-check the path before creating files.

3. **Working directly in the projects root instead of a project subfolder.**  
   **Fix:** Every project must have its own subfolder. Never store files in `~/projects/` directly.

4. **Sharing folders between multiple projects.**  
   **Fix:** If two projects need the same code, extract the shared component into its own separate project and reference it as a dependency/submodule.

5. **Neglecting to commit to git early.**  
   **Fix:** Initialize git immediately and make the first commit with the structure. This provides history and safety.

6. **Forgetting the .hermes folder for project-specific agent config.**  
   **Fix:** Keep Hermes integrations, custom scripts, and agent memory within `.hermes/` inside the project.

## Verification Checklist

After completing the procedure, verify:

- [ ] Project folder exists at `/root/.hermes/projects/<project-name>/`
- [ ] All standard subdirectories are present (`src/`, `tests/`, `docs/`, `config/`, `data/`, `scripts/`, `assets/`, `logs/`, `.hermes/`)
- [ ] README.md exists and contains project metadata
- [ ] .gitignore exists (if git was initialized)
- [ ] .git exists (if git was initialized) and first commit completed
- [ ] No project files exist outside the project folder
- [ ] Projects index updated (if used)
- [ ] User can `cd /root/.hermes/projects/<project-name>/` without errors

## One-Shot Recipes

**Recipe: Quick standalone script project**
```
Skill: project-initialization
Project name: data-processor
Project type: utility-script
Description: CSV data transformation utility
Git: Yes
```
Result: Creates `/root/.hermes/projects/data-processor/` with `src/`, `scripts/`, `docs/`, and a clean git repo.

**Recipe: Web application with backend API**
```
Skill: project-initialization
Project name: brand-api-backend
Project type: web-app
Description: REST API for brand analytics
Git: Yes
```
Result: Creates `~/projects/brand-api-backend/` with full structure, ready for FastAPI/Django or similar framework setup.

---

**Dad would've loved this one.** Proper organization from the start saves so many headaches later. Right then, let's keep those projects tidy!

</content>