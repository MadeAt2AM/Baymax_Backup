# Updating the checklist — when the `patch` tool misbehaves

The `patch` tool is the right way to edit a file most of the time, but it
can intermittently reject `mode="replace"` calls with a `path required`
error even when `path` is supplied. This happens with both short snippets
and large blocks. When it does:

1. **Do not retry the same call.** The error is tool-internal, not a
   validation failure.
2. **Do not switch to `write_file`.** That overwrites the whole file and
   loses sibling edits from parallel agents.
3. **Fall back to `terminal` + `python` heredoc.** This is reliable and
   preserves the rest of the file.

The pattern that works:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('/root/.hermes/projects/<project>/IMPLEMENTATION_CHECKLIST.md')
s = p.read_text()
old = '- [ ] **PHASE-NNN** Description.'
new = '- [x] **PHASE-NNN** Description.'
assert old in s, f"missing: {old[:80]}"
s = s.replace(old, new)
p.write_text(s)
print('updated')
PY
```

Why this pattern:

- The `<<'PY'` quoting disables shell expansion inside the heredoc, so
  `$` and backticks in the file content are not interpreted.
- `assert old in s` is a one-line guard against accidentally editing the
  wrong task ID.
- `p.write_text(s)` is idempotent — re-running with the same input does
  nothing harmful.
- The rest of the file is preserved exactly, including sibling edits
  from other agents.

For batch toggles (flipping many `[ ]` to `[x]` at once), use a loop:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('/root/.hermes/projects/<project>/IMPLEMENTATION_CHECKLIST.md')
s = p.read_text()
for sid in ("S-013", "S-014", "S-015"):
    s = s.replace(f"- [ ] **{sid}**", f"- [x] **{sid}**")
p.write_text(s)
PY
```

## Verifying the update

After any update, read the file back and grep for the tick:

```bash
grep -nE "^\- \[(x| )\] \*\*PHASE-NNN" \
  /root/.hermes/projects/<project>/IMPLEMENTATION_CHECKLIST.md
```

The expected output is one line per task ID, with `[x]` for completed and
`[ ]` for pending. If the line is missing, the substitution missed and
the task is still unchecked.

## When *not* to use this fallback

- If the file is brand new and `write_file` has not been called yet, use
  `write_file` directly. The fallback only matters when you want to
  preserve other content.
- If the file is large (say > 50 KB) and you only need to flip a single
  task, the python heredoc still wins because it reads the file once and
  writes it once, regardless of size.
- If the task is to delete a block, use `s = s.replace(old, "")` in the
  heredoc.

## Why this lives in the checklist skill

Editing the checklist is the highest-frequency write in any multi-session
project. When the tool fails, the recovery has to be quick and obvious,
otherwise the checklist drifts behind the actual state. Codifying the
fallback here means the next session knows it without rediscovering it.
