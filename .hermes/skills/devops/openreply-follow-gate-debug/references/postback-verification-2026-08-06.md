# Follow-Gate Postback Verification Notes — 2026-08-06

Use this reference when a local OpenReply follow-gate patch has been sitting
uncommitted or when `processPostback` was changed.

## Static findings that triggered the gate

An uncommitted worker diff was found with these hazards:

- `processPostback` destructured `{ instagramAccountId, userId, payload,
  fallback }`, but the non-follower re-prompt called the API with `commentId`.
  `ProcessPostbackJob` had no `commentId`; this should be caught by typecheck.
- The follower/unverifiable branch sent a reward immediately with
  `sendDirectMessageWithLinkButton`, then execution continued into the shared
  quota/send block. That creates a duplicate-send risk and bypasses the shared
  accounting before the second path runs.
- The branch grouped `true` and `null` together. Fail-open may be intentional,
  but it must enter the same single canonical delivery path as a confirmed
  follower, not a separate send implementation.
- Existing tests covered comment-time prompting and read fallbacks, but did not
  visibly pin a real `followcheck:` button tap for all three follow states.

## Required focused matrix

| Event | Follow status | Expected result |
|---|---:|---|
| `followcheck:` button | `false` | One re-prompt, no quota reservation, no reward |
| `followcheck:` button | `true` | One reward through canonical path; one quota/log update |
| `followcheck:` button | `null` | Documented fail-open through canonical path; one reward |
| read fallback | `false` | Silent return; no prompt, quota, or reward |
| read fallback | `true` | One canonical reward |
| read fallback | `null` | Documented fail-open through canonical path |

For tracked links, also pin button rejection → one inline-link fallback. Assert
that the direct and private-reply APIs are not both called for one reveal.

## Evidence record

Run:

```bash
npm test -- --run __tests__/dm-worker.test.ts
npm run typecheck
git diff --check
```

Write `VERIFICATION-YYYY-MM-DD.md` containing:

- SGT date/time
- `git rev-parse HEAD`
- `git status --short`
- exact commands
- literal stdout/stderr
- each exit code
- one-line PASS/FAIL verdict

Do not infer that a healthy production URL validates an uncommitted local diff.
Do not perform a live Instagram trigger, deployment, restart, or push merely to
obtain this local evidence.
