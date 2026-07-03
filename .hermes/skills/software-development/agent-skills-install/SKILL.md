---
name: agent-skills-install
description: "Install third-party agent-skill bundles from GitHub (Vercel Labs `npx skills add` ecosystem — skills.sh format) and wire them into Hermes. Use when the user asks to install a skill pack from a GitHub repo, references skills.sh / Leonxlnx / vercel-labs/agent-skills style skill bundles, or wants to grab a curated multi-skill library from GitHub and make it usable inside Hermes. Do NOT use for installing a single Hermes-format skill (use `hermes skills install <url>` from the bundled `hermes-agent` skill instead). Verify the install by loading each skill with `skill_view` before reporting success."
version: 1.0.0
metadata:
  hermes:
    tags: [skills, agent-skills, npx, vercel-labs, installation, workflows]
    related_skills: [hermes-agent, karpathy-guidelines]
---

# Installing Third-Party Agent-Skill Bundles into Hermes

The Vercel Labs **agent-skills** ecosystem (`https://github.com/vercel-labs/agent-skills`) defines a portable SKILL.md format used by many GitHub repos (Leonxlnx/taste-skill, emilkowalski/animations skills, etc.). The official installer is `npx skills add` from the [`skills`](https://www.npmjs.com/package/skills) npm package. This is **separate** from Hermes's native `hermes skills install` — they target different ecosystems and different on-disk locations.

This skill covers the **Vercel ecosystem** path. For Hermes's own hub / direct SKILL.md install, see the bundled `hermes-agent` skill (`hermes skills install <url-or-id>`).

## When to Use

- User says "install the skills from this repo" + a GitHub URL like `Leonxlnx/taste-skill`, `vercel-labs/agent-skills`, etc.
- Repo has a `skills/` folder with `SKILL.md` files inside per-skill subdirectories (the canonical layout)
- User references `npx skills add`, `skills.sh`, or the Agent Skills spec
- The skill pack contains MULTIPLE skills and you want all of them wired into Hermes at once

## The Canonical Workflow

### 1. Clone the source repo (read-only inspection)

```bash
mkdir -p /tmp/skill-pack-temp && cd /tmp/skill-pack-temp
git clone https://github.com/<owner>/<repo>.git
ls <repo>/skills/
```

This lets you (a) confirm there IS a `skills/` folder, (b) count skills, (c) read each `SKILL.md` frontmatter to know what you're getting, (d) check the README for any custom install commands.

**Do not skip this.** The README often has install-name quirks (e.g. taste-skill's `design-taste-frontend` is the install name even though the folder is `taste-skill/`). Reading the README first prevents silent surprises.

### 2. Run the official installer non-interactively

The `npx skills add` CLI prompts for skill selection by default. In a non-TTY shell (which Hermes's terminal tool provides) this **hangs forever** waiting for input. Always pass both flags:

```bash
cd /tmp && npx skills add https://github.com/<owner>/<repo> --yes --global
```

- `--yes` (`-y`) — skip the skill selection picker, install all discovered skills
- `--global` (`-g`) — install to `~/.agents/skills/` (not a project-local `skills/`)

### 3. Verify on disk AND inside Hermes

The installer writes to `~/.agents/skills/<install-name>/SKILL.md`. Hermes auto-symlinks that into `~/.hermes/skills/<install-name>` so the skill loader finds it on next session.

```bash
ls ~/.agents/skills/<install-name>/                # physical files
ls -la ~/.hermes/skills/<install-name>              # Hermes symlink should resolve
```

If `~/.hermes/skills/<install-name>` doesn't exist after install, create the symlink manually:

```bash
ln -s ../../.agents/skills/<install-name> ~/.hermes/skills/<install-name>
```

### 4. MANDATORY: load each skill with skill_view before reporting success

This is the gate that turns "tests green" into "actually works." The installer can complete without any of the skills being parseable — broken YAML frontmatter, missing `name:` field, encoding issues. Before telling the user "installed successfully," call:

```text
skill_view(name="<install-name>")  # for every skill in the pack
```

If any load fails or returns a description that doesn't match the frontmatter, the install is broken — debug that one skill before declaring done. Do not batch the success report before doing this step.

### 5. Report findings honestly

The installer may print a "Failed to install N skills" block listing each skill with a note like `PromptScript: PromptScript does not support global skill installation`. **Read this carefully before assuming failure.** Different installer adapters target different downstream tools (Codex, Cursor, PromptScript, etc.). A PromptScript failure when you only care about Hermes is NOT a real failure — Hermes's symlink is what matters.

Correct report shape:
- Number of skills discovered
- Number successfully symlinked into `~/.agents/skills/` and `~/.hermes/skills/`
- Number of failures + which adapters they affect (not whether Hermes can use them)
- Which skills you verified with `skill_view`
- Any skills that looked broken and need manual fixes

## Pitfalls

### The interactive picker hangs in non-TTY terminals

Symptom: `npx skills add <url>` shows the spinner, prints "Select skills to install (space to toggle)", then never exits.

Cause: the CLI uses Ink (React for CLIs) which expects a real TTY for keyboard input.

Fix: always use `--yes --global` together. `-y` answers "install all"; `-g` answers "install location". Both required.

### The "Failed to install N skills" block is mostly noise

The installer prints a per-adapter failure summary at the end. For each skill it tries to install into Codex, Cursor, Claude Code, Amp, Antigravity, **PromptScript**, etc. — that's ~15 adapters. Hermes is one of them, and if Hermes succeeded it shows as a green checkmark in the success block above the failure summary. PromptScript's "does not support global installation" is its known limitation and does NOT mean the skill failed for Hermes.

Lesson: count `✓ ~/.agents/skills/...` lines in the success block, not `✗` lines in the failure block.

### Hermes symlinks from `~/.agents/skills/`, not from the repo

The installer does NOT copy skill files into `~/.hermes/skills/`. It creates symlinks. If you later `rm -rf ~/.agents/skills/<name>`, the Hermes symlink dangles. Always edit/delete at the `~/.agents/skills/` source.

### Skill install names ≠ folder names

Per the agent-skills spec, the install name is the `name:` field in SKILL.md frontmatter, not the directory name. Example: taste-skill's folder is `skills/taste-skill/` but the install name (and Hermes skill key) is `design-taste-frontend`. The CLI uses both interchangeably but the symlink always uses the install name.

### Reading SKILL.md can be expensive on large packs

Some packs (Vercel Labs starter bundle) have 50+ skills with multi-MB SKILL.md files. Don't dump all of them — `head -10` of each is enough to confirm frontmatter + a description. Save full reads for the ones you'll actually use.

## Verification Checklist

Before reporting "installed":

- [ ] `~/.agents/skills/<name>/SKILL.md` exists
- [ ] `~/.hermes/skills/<name>` is a valid symlink to the same path
- [ ] `skill_view(name="<name>")` returns a parsed SKILL with frontmatter + body
- [ ] The description returned by `skill_view` matches what the README/frontmatter promises
- [ ] Cleaned up the temp clone directory

## Updating an Existing Pack

The Vercel skills CLI installs each skill as a fresh file in `~/.agents/skills/`. Re-running the same `npx skills add <url>` command is the official upgrade path; it overwrites in place by install name. From the taste-skill README: "If you already have v1 installed, just re-run the install command and you will be upgraded." Verify the same way after upgrade (reload via `skill_view` and confirm the version-related description has changed).

## Related Workflows

- **Single Hermes-format skill from GitHub** — use `hermes skills install https://raw.githubusercontent.com/<owner>/<repo>/<branch>/path/to/SKILL.md` (per the bundled `hermes-agent` skill). Different ecosystem, different storage path (`~/.hermes/skills/` directly, no `~/.agents/`).
- **Skill authoring (writing your own SKILL.md)** — use the `hermes-agent-skill-authoring` skill.
- **Removing a pack** — `rm -rf ~/.agents/skills/<name>` AND `rm ~/.hermes/skills/<name>` (unlink the symlink).