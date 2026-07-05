# GitHub 100 MB Blob Rejection — Recovery Playbook

Session-captured knowledge from the 2026-07-04 backup run that broke with `GH001: Large files detected`. This doc captures the *why* behind the recovery steps in SKILL.md, so the next session can debug similar failures without re-deriving the workflow.

## What GitHub actually checks

GitHub's pre-receive hook validates **every blob in the pushed pack**, not just blobs in the new commits. So when you `git rm --cached` a 180 MB file and recommit, the pack still contains the blob from the *parent* commit. A plain `git push` will be rejected even though `HEAD`'s tree no longer references the path.

The only ways to get a clean push are:

1. **Re-bake the new tip so it doesn't reach into the offending commit.** If the offending blobs live in un-pushed local commits, soft-reset to `origin/main` (which doesn't have them) and recommit from the working tree. Fast-forward push — no force needed.
2. **`git filter-repo` (or `git filter-branch`)** to rewrite history and drop the blob from every commit. Required when the remote already has a commit containing the blob. Slow, dangerous if the repo has many commits.
3. **Git LFS** — install the lfs client, track the file types, and migrate the blobs to LFS storage. Best for binaries you actually want versioned.

For the baymax-backup repo, option 1 is almost always the right call because:
- The repo is single-user and personal.
- Force-pushes are not a concern (no collaborators).
- New large files appear at most once a day as new tooling installs land.

## Why `.gitignore` patterns can silently fail to match

The `.gitignore` patterns `.agent-reach-venv/**` and `.agent-reach-venv/` look equivalent but aren't:

- `.agent-reach-venv/**` — matches files *under* the directory, but **not the directory itself** in some git versions.
- `.agent-reach-venv/` — matches the directory and (recursively via git's directory matching) all files under it.

Always include **both** lines for top-level directories that are pure artefact trees. Same goes for `.kokoro/models/`, `.linkedin-mcp/patchright-browsers/`.

Verify with `git check-ignore -v <path>` — exit 1 means the pattern isn't matching and the file is still tracked-eligible.

## The reset-and-recommit trick

```bash
# Identify the offending blobs (one-shot)
git rev-list --objects origin/main..HEAD | awk '{print $1}' \
  | git cat-file --batch-check='%(objectname) %(objecttype) %(objectsize)' \
  | awk '$2 == "blob" && $3 > 100*1024*1024 { print $1 }'

# Update .gitignore, then:
git add .gitignore
git commit -m "chore: gitignore oversized directories"

# Soft-reset to origin (this drops any un-pushed local commits but keeps
# the working tree and the newly-staged .gitignore change in the index).
git reset --soft origin/main

# Re-stage everything (the .gitignore will now exclude the large dirs).
git add -A
git commit -m "Backup YYYY-MM-DD HH:MM — exclude oversized blobs"
git push origin main   # fast-forward, no force
```

If the **remote** already has a commit referencing the large blob, this won't work — you'll need `git filter-repo` or to live with the rejection until that commit ages out via clone/GC. Check with:

```bash
git ls-remote origin main   # capture remote SHA
git rev-list --objects <REMOTE_SHA> | grep -E "\.(onnx|node)$|chrome-headless-shell"
```

If those return hits, the offending blob is already on the remote and option 2 or 3 above is required.

## Class of problem

The pattern "tooling Python venv bundles a 100+ MB native driver" will recur. Watch for:

- `**/patchright/driver/node` — Playwright-derived chromium driver
- `**/playwright/driver/**` — same family
- `**/onnx/*.onnx` — Kokoro, whisper.cpp, llama.cpp weights
- `**/chrome-headless-shell*` — bundled chrome for MCP browsers
- `**/voices-*.bin` — Kokoro voice packs (smaller but trending up)

When you see a new tool installed in `/root`, glance at its directory size:

```bash
du -sh /root/.cache/ms-playwright /root/.linkedin-mcp /root/<new-tool> 2>/dev/null | sort -h
```

Anything over 100 MB should be gitignored preemptively, not after it bites.

## Recovery is automated

The script `scripts/fix-large-blob-push.sh` (bundled with this skill) implements the full diagnostic + recovery flow described above. Run it manually if the cron job fails; the next backup commit will be clean.