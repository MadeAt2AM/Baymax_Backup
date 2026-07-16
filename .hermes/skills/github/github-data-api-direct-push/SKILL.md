---
name: github-data-api-direct-push
description: Push commits to a GitHub branch entirely via the REST Data API (blobs → tree → commit → ref), bypassing local `git`. Use when the local `git` binary is wedged or unavailable but HTTPS to api.github.com still works. Triggers on `git push` timing out, `git rev-parse HEAD` hanging, "kernel scheduler overload", or "I need to push from a sandboxed environment with no git". Includes the fast-forward retry pattern, the 504-webhook-is-not-failure pitfall, and a working Python template.
version: 1.0.0
author: Baymax
license: MIT
metadata:
  hermes:
    tags: [GitHub, API, Git, Push, Fallback, Recovery, Data-API]
    related_skills: [github-auth, github-pr-workflow, deploy-app-to-dev-vps]
---

# GitHub Data API Direct Push

Push commits to a GitHub branch via the REST Data API, **without using the local `git` binary**. The local git workflow fails when the kernel scheduler is jammed, the credential helper blocks on stdin, or the working tree contains untracked files that git refuses to walk. The Data API path works as long as HTTPS to `api.github.com` responds.

This is a **direct push to an existing branch** (typically `main`). It does **not** create a PR, does **not** run branch protection checks, and does **not** require a PR review. Use it only when:
- The repo allows direct push to the target branch, OR
- The operator has explicitly authorised a hot-fix push.

## When to use this

**Trigger on any of:**
- `git rev-parse HEAD` times out at 30s+, `git add <file>` times out, `git status` hangs
- `git push` returns network errors even when `curl https://api.github.com` works fine
- You're in a minimal sandbox / fresh container with no `git` installed
- Working tree has so many untracked files that git walking it is impossibly slow
- The local `git` works but you've discovered a parallel commit already landed on the remote and you need a fast-forward retry without `git pull --rebase`

**Don't use this when:**
- Local git works normally. Use the regular PR workflow.
- The repo requires PR review. This bypasses it.
- You're not sure your on-disk content is what you want to ship. The local workflow lets you `git diff --staged` before committing; the API path commits whatever bytes are at the paths you specify.

## Prerequisites

1. **Token with `repo` scope.** Easiest source: `~/.config/gh/hosts.yml` (the `oauth_token:` line).
2. **The commit message** — write it before you start, because the script is going to ask for it.
3. **The list of files** — paths relative to the repo root, with content already on disk and correct.

## The four-step pattern

```
HEAD (read) → blobs (POST per file) → tree (POST with base_tree + blob SHAs)
            → commit (POST with tree + parent) → ref (PATCH main to new commit)
```

### Step 1 — Read the current HEAD directly from disk

Bypass `git` by reading `.git/refs/heads/main`:

```bash
HEAD=$(cat .git/refs/heads/main)
```

If the file doesn't exist (fresh clone, or packed-refs only), try:

```bash
HEAD=$(grep -E '^([0-9a-f]+) refs/heads/main$' .git/packed-refs | awk '{print $1}')
```

### Step 2 — Compute blob SHAs locally

Git blob SHAs are content-addressable: `sha1("blob <len>\0" + content)`. Compute them in Python without spawning git:

```python
import hashlib
def blob_sha(content: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(content))
    h.update(content)
    return h.hexdigest()
```

This is faster than `POST /git/blobs` for each file because you avoid the round-trip. POST blobs anyway if you want to be safe (the API will dedupe by content, so identical content uploaded twice returns the same SHA).

### Step 3 — POST the tree, then the commit, then update the ref

Use the GitHub Data API. Full working Python below.

### Step 4 — Verify

After pushing:
- The webhook on the receiver (e.g. port 9000 on the VPS) usually returns **504** to GitHub because the build script takes >10s. **That is normal.** See "Pitfall: webhook 504 is not failure" below.
- Verify the change is live by probing the **served bundle or API behaviour**, not the webhook delivery status.
- For SPA bundles: check the bundle's content hash (`/assets/index-<hash>.js` filename) for new code, or grep the bundle for strings you know only exist in the new version.
- For API endpoints: hit the new endpoint with a token. Compare against the old behaviour.

## Working Python template

```python
import urllib.request, json, hashlib, os, time

TOKEN = "<oauth token>"           # from ~/.config/gh/hosts.yml
REPO  = "owner/repo"              # e.g. "MadeAt2AM/SYNTRA_VPS"
DEST = "."                        # working tree root (default)
HEAD = open(f"{DEST}/.git/refs/heads/main").read().strip()

def gh(method, path, body=None):
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agent-direct-push",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        print(f"  {method} {path} → {e.code}  {body}")
        raise

def blob_sha(content: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(content))
    h.update(content)
    return h.hexdigest()

# 1. Get HEAD commit metadata (parent SHA + base tree)
head = gh("GET", f"/repos/{REPO}/git/commits/{HEAD}")
BASE_TREE = head["tree"]["sha"]

# 2. Build the list of file blobs (compute SHA locally, no need to POST)
files = [
    "path/to/file1.ts",
    "path/to/file2.tsx",
    "docs/X.md",
]
blobs = []
for rel in files:
    abs_path = os.path.join(DEST, rel)
    if not os.path.exists(abs_path):
        raise SystemExit(f"missing on disk: {rel}")
    content = open(abs_path, "rb").read()
    blobs.append({
        "path": rel,
        "mode": "100644",
        "type": "blob",
        "sha": blob_sha(content),
    })

# 3. POST the new tree on top of the base tree
new_tree = gh("POST", f"/repos/{REPO}/git/trees",
              {"base_tree": BASE_TREE, "tree": blobs})["sha"]

# 4. POST the commit on top of HEAD
new_commit = gh("POST", f"/repos/{REPO}/git/commits", {
    "message": "fix(scope): description\n\n- bullet one\n- bullet two",
    "tree": new_tree,
    "parents": [HEAD],
})["sha"]

# 5. PATCH the main ref to point at the new commit
gh("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": new_commit})

print(f"PUSHED  {new_commit}")
```

## Pitfalls

### "Update is not a fast forward" (422)

Someone else advanced `main` between your HEAD read and your ref-update. Typical cause: the receiver's webhook daemon ran a deploy that committed a `webhook verify` line, OR a parallel agent/operator pushed.

**Fix:** re-read `HEAD` from GitHub (not from local `.git/refs/heads/main` — that may be stale), then re-POST the tree+commit on top of the new parent. Loop with a retry limit (3 attempts is usually enough). Don't try `git pull --rebase` — that's the exact operation that was wedged.

```python
for attempt in range(3):
    HEAD = gh("GET", f"/repos/{REPO}/git/ref/heads/main")["object"]["sha"]
    head = gh("GET", f"/repos/{REPO}/git/commits/{HEAD}")
    BASE_TREE = head["tree"]["sha"]
    new_tree = gh("POST", f"/repos/{REPO}/git/trees", {"base_tree": BASE_TREE, "tree": blobs})["sha"]
    new_commit = gh("POST", f"/repos/{REPO}/git/commits", {"tree": new_tree, "parents": [HEAD], "message": msg})["sha"]
    try:
        gh("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": new_commit})
        break
    except urllib.error.HTTPError as e:
        if e.code == 422:
            continue  # someone raced us, retry
        raise
```

### Tree SHA must be exactly 40 chars

If you accidentally log `tree["sha"][:12]` and re-submit, you'll get `422 tree parameter must be exactly 40 characters`. Always pass the full SHA. Validate by `len(new_tree) == 40` before submitting.

### Commit message escaping

JSON body uses `\n` (escaped), not literal newlines. Python's `json.dumps` handles this for you. Bash users need to be careful: `jq -nc --arg msg "line1\nline2"` or `python -c "import json; print(json.dumps({'message': 'line1\nline2'}))"`.

### Webhook 504 is not failure

After the ref PATCH succeeds, the receiver webhook (e.g. webhook daemon on port 9000) usually returns **504** to GitHub because the build script takes >10s and GitHub caps the response at 10s. The build usually still completes asynchronously in the background.

**Verify by probing the served bundle or API behaviour, not by webhook status:**
- SPA: `curl -sI https://site/` then look for a new `/assets/index-<hash>.js` filename, then `curl -s https://site/assets/index-<hash>.js | grep <new-symbol>` to confirm the new code is in the bundle.
- API: hit the new endpoint with an auth token. If the route shape changed (new query param, new field in response), the old and new behaviour are easy to distinguish.
- Wait at least 60–120s before declaring the build failed. A full Docker rebuild + Caddy reload typically takes 30–90s.

### No PR, no CI, no branch protection

This path skips:
- Pull request reviews
- Status checks (GitHub Actions, required CI)
- Branch protection rules (signed commits, linear history, "no direct push")
- CODEOWNERS review requests

**Only use it when:**
- The repo allows direct push to `main` (no protection rule against it).
- OR the operator has explicitly authorised a hot-fix bypass.

### Orphan commits

If you abandon a fast-forward retry, your earlier commit objects stay reachable from the abandoned SHA but unreachable from any branch ref. GitHub's GC will eventually prune them. To prune sooner: `git reflog expire --expire=now --all && git gc --prune=now` on a fresh clone.

### The local `git` is still wedged after the push

The push succeeds but you still can't run normal git commands locally. The next session will start with the same problem unless the host recovers. If you need to do follow-up edits, repeat the data-API flow for each commit — don't try to `git pull` or `git status`.

## Verification recipe

```python
import urllib.request, json, time
TOKEN = "<token>"
REPO  = "owner/repo"

# 1. Confirm the ref advanced
ref = json.loads(urllib.request.urlopen(
    urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/git/ref/heads/main",
        headers={"Authorization": f"token {TOKEN}",
                 "Accept": "application/vnd.github+json"}),
    timeout=30).read())
print("HEAD now:", ref["object"]["sha"])

# 2. Wait for the receiver webhook to build
time.sleep(90)

# 3. Probe the served bundle / API for the new feature
#    (example: search the SPA bundle for a string only present in the new code)
bundle = urllib.request.urlopen("https://site.example/").read().decode()
import re
m = re.search(r'src="(/assets/[A-Za-z0-9_./-]+\.js)"', bundle)
bundle_url = m.group(1)
body = urllib.request.urlopen(f"https://site.example{bundle_url}").read().decode()
assert "new-feature-name" in body, "new code not in bundle yet"
print("LIVE")
```

## See also

- `deploy-app-to-dev-vps` — full webhook-based deploy playbook on Hetzner VPS, includes the Caddy sidecar pattern and webhook-verification recipe.
- `github-pr-workflow` — the standard PR + branch + CI workflow when local git works.
- `karpathy-guidelines` — the "verify before reporting success" rule. The webhook 504 pitfall here is a concrete case of "don't trust the success signal without independent verification".
