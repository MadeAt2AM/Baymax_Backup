# GitHub Auth — Critical Lessons for VPS Backup Scripts

This file captures non-obvious auth behaviour discovered while building the backup system. These are class-level patterns, not one-off notes.

---

## `gh auth login --with-token` alone is NOT sufficient

**Symptom:** `gh auth status` shows authenticated, but `git push` fails:
```
fatal: could not read Username for 'https://github.com': No such device or address
```

**Root cause:** `gh auth login --with-token` authenticates the `gh` CLI for API calls only. Git operations (push/pull/clone) use a separate credential system. On a fresh VPS, the default git credential helper is broken or empty.

**Fix — run both:**
```bash
echo "$TOKEN" | gh auth login --with-token
gh auth setup-git   # ← this is the step everyone forgets
```

`gh auth setup-git` installs a git credential helper that bridges `gh` authentication to git operations. Without it, git cannot obtain credentials even though `gh` is fully logged in.

---

## Credential helper `store` fails silently when the store file is missing

**Symptom:** `git config --global credential.helper store` is set, but `git push` still prompts and fails.

**Root cause:** The `store` helper reads from `~/.git-credentials`. If that file doesn't exist or has wrong format, git falls back to its broken default helper and prompts for "Username" (which maps to no actual prompt mechanism on a headless server).

**Diagnosis:**
```bash
git config --global credential.helper   # should return 'store'
cat ~/.git-credentials                 # should contain github.com credentials
```

**Fix:** Either:
1. Run `gh auth setup-git` (preferred — uses gh as credential helper)
2. Or manually create `~/.git-credentials` with correct format:
   ```
   https://chrisvincodes:<TOKEN>@github.com
   ```
   Note: username is your GitHub username, NOT the token itself.

---

## Token embedded in remote URL works when credential helpers fail

If all credential helpers fail, embed the token directly in the remote URL:
```bash
git remote set-url origin https://chrisvincodes:<TOKEN>@github.com/<owner>/<repo>.git
git push  # no prompts
```
**Caveat:** Token appears in process list and git config output. Only use this for automated scripts (cron, CI), never as a permanent setup.

---

## Fine-grained PATs fail at repo creation even with `repo` scope

**Symptom:**
```json
{ "message": "Resource not accessible by personal access token", "status": 403 }
```
on `POST /user/repos` even though the token has `Administration` and `Contents` permissions.

**Root cause:** Fine-grained Personal Access Tokens (PATs) have repo-level access restrictions that differ from classic PATs. GitHub's REST API for repository creation requires a **classic** PAT with `repo` scope. Fine-grained PATs cannot create repos via the API.

**Fix:** Use a **classic PAT** with `repo` scope for repo creation. Fine-grained PATs work fine for push/pull once the repo exists.

---

## PATs with org permissions need `admin:org` scope for org-level operations

**Symptom:** Token has `Administration` + `Contents` on an org, but `gh repo create org/repo` fails.

**Root cause:** Creating a repo *inside an organization* requires `admin:org` scope in addition to repo scopes. This is a separate permission from individual repo administration.

---

## Python heredoc trick for extracting tokens cleanly

Extracting a token from `.env` in a bash script without yaml/pyyaml is fragile with inline Python. Use a separate Python script file approach:

```bash
# Instead of fragile inline heredoc with backtick subshells:
GH_TOKEN=$(python3 -c "..." | ...)   # BROKEN — nested quoting issues

# Write to a file, then source it:
python3 /tmp/get_token.py            # writes token to stdout
GH_TOKEN=$(python3 /tmp/get_token.py)  # WORKS
```

Or use Python directly in the credential setup:
```python
import subprocess
subprocess.run(['gh', 'auth', 'setup-git'])
```

---

## Summary: Correct auth sequence for a backup script on VPS

```bash
# 1. Check if already authenticated
if ! gh auth status &>/dev/null; then
    # 2. Read token from hermes .env via Python
    TOKEN=$(python3 -c "
with open('/root/.hermes/.env') as f:
    for line in f:
        if line.startswith('GITHUB_TOKEN=') and not line.strip().startswith('#'):
            print(line.split('=',1)[1].strip()); break
")
    # 3. Login + setup git credentials
    echo "$TOKEN" | gh auth login --with-token
    gh auth setup-git
fi
# 4. Push (gh is authenticated, git can get credentials)
git push https://github.com/<owner>/<repo>.git main
```

If `gh auth setup-git` cannot be run, fall back to URL-embedded token:
```bash
git remote set-url origin https://chrisvincodes:${TOKEN}@github.com/<owner>/<repo>.git
```
