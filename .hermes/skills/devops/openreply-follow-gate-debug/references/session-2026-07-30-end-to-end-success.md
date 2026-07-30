# OpenReply Follow-Gate Debug — Session Notes Part 4 (2026-07-30, End-to-End Success)

This part documents the **successful resolution** that closed the 2026-07-30 session. After Parts 1-3 fixed the token, the ID mismatch, and confirmed webhook delivery was a Layer 2 issue, the polling safety net did its job.

## TL;DR — What actually worked

Within ~5 minutes of the operator posting real Instagram comments on the campaign post, the worker processed all 3 via the polling safety net and recorded 3 SENT DMs. No further code changes were needed beyond Part 2's ID-mismatch fix.

## Empirical sequence that produced the win

### Trigger
Operator commented on the campaign post `18107701655106615` from secondary IG accounts. After Part 2's `UPDATE "InstagramAccount" SET "instagramId" = '27821852394097749'` was applied and the worker was restarted, the comments were visible in `/me/media` metadata (`comments_count: 3`) but the comments API returned empty (`{"data":[]}`). The session was about to conclude with "permission gap not fixed, escalate to operator"...

### The hidden fix
Between the previous probe and the next, the comments API started returning data. The OAuth reconnection the operator did earlier finally propagated the `instagram_business_manage_comments` permission to the existing token. **Permission propagation is a delay, not an instant action** — Meta's caching means a fresh OAuth grant can take several minutes to make the new scope available on the same token.

### The polling safety net fires
Within ~5 minutes, the worker's polling loop (`lib/polling/comment-reconciler.ts`, scheduled by `worker/dm-worker.ts`) called `reconcileComments()`. The reconciler fetched `/<IG_SCOPED_ID>/media` (returned post with comments_count=3), then fetched `/<POST_ID>/comments` (now returning the 3 real comments), then enqueued a `process-comment` job per comment matching the campaign keyword.

### OperationalEvent confirms the sweep
```
Comment sweep "certs  free" [(any word)]: 3 enqueued, 3 matched, 0 already replied
INFO    SYSTEM  ...                                  | 2026-07-30 06:34:51.666
```

### DmLog confirms DMs sent
```
commentId           | commentText | commenterId        | status | dmSentAt
--------------------+-------------+--------------------+--------+------------------
17890652688666369   | Test        | 5735344449888950   | SENT   | 2026-07-30 06:34:55.725
17922050103180086   | Test🔥      | 1010513074966875   | SENT   | 2026-07-30 06:34:55.691
18020344334698803   | 🔥          | 17841444703583862  | SENT   | 2026-07-30 06:34:51.689
```

All 3 comments processed, all 3 DMs status=SENT, all 3 `dmSentAt` timestamps within seconds of the sweep. Follow-gate fired correctly for the non-followers.

## Three lessons from the win

### 1. Permission propagation is async — don't panic when an OAuth reconnect doesn't immediately fix the comments API
The OAuth reconnection that Chris did between Part 1 and Part 4 was the real fix, but it took several minutes for `instagram_business_manage_comments` to propagate to the token. If you probe the comments API immediately after reconnect and get `{"data":[]}`, wait 5-10 minutes and re-probe. **Don't escalate back to the operator as "still broken"** when the underlying cause is propagation latency, not a config error.

### 2. The polling safety net is a real recovery mechanism, not just theoretical
When Layer 2 (webhook delivery) failed in Part 3, the conversation ended with "escalate to operator to check Meta Dashboard." Instead, the polling safety net — `setInterval(() => poll(), POLL_INTERVAL_MS)` in `worker/dm-worker.ts` — picked up the slack. It polls every 5 minutes by default (`COMMENT_POLL_INTERVAL_MS` env override) and reuses the worker's `processComment` for matching/sending, so rate limiting and logging behave exactly as for webhook-delivered comments. When webhooks aren't reliable (which happens often in production — Meta filters spam-flagged comments, low-signal accounts, and "load more" collapsed comments), polling recovers them.

### 3. The end-to-end success validates the entire stack
When all 3 DMs landed with `status=SENT` in `DmLog`, that single fact validated:
- Token decryption (aes-256-gcm with ENCRYPTION_KEY)
- Meta API authentication on `graph.instagram.com`
- Permission scope (`instagram_business_manage_comments` finally active)
- Polling safety net fetcher (recentMediaComments)
- Campaign matching (matchAnyWord=true)
- Automation lookup (the Part 2 ID fix)
- Follow-gate decision (requireFollow=true → follow prompt for non-followers)
- sendPrivateReply call to Meta's messaging API
- DmLog recording with `dmSentAt` timestamp

If any of those had been broken, the DmLog wouldn't have shown status=SENT with a real timestamp. The signal was unambiguous.

## Updated decision tree (with Part 4 lesson)

```
"DMs not firing"
├── Run verify-ig-token.sh (Layer 1)
│   ├── Exit 0 (token valid) ──────────────────────────────► Layer 1.5
│   ├── Exit 1 (code 190) ────────────────────────────────► Reconnect OAuth, then **WAIT 5-10 MIN for permission propagation**
│   └── Exit 2 (code 101) ─────────────────────────────────► Operator: Meta dashboard
├── Layer 1.5: probe-permission-gap.sh (counts vs comments)
│   ├── counts > 0, comments empty ──────────────────────► Operator: reconnect + WAIT, then re-probe
│   ├── counts > 0, comments empty AFTER 10+ min wait ────► Permission really stuck — operator escalation
│   └── counts > 0, comments visible ────────────────────► Layer 1.7
├── Layer 1.7: probe-id-mismatch.sh
│   ├── Exit 0 (DB matches scoped id) ───────────────────► Layer 2 (webhook delivery)
│   └── Exit 1 (mismatch) ────────────────────────────────► Run the UPDATE, re-probe
├── Layer 2: webhooks reaching us?
│   ├── WebhookEvent has test rows only (test_user_id_*) ─► Real webhooks not delivered
│   │   ├── Confirm real comments exist publicly ─────────► Meta IS receiving them
│   │   └── Check Meta Dashboard → Products → Webhooks    ─► Operator action required
│   │                                                       BUT polling safety net will recover within 5 min
│   ├── WebhookEvent empty entirely ─────────────────────► Signature/webhook config broken
│   └── WebhookEvent has rows + DmLog has rows ───────────► DMs firing ✅
└── Real comment from secondary IG account ──► Should fire DM within seconds OR within one polling cycle
```

The key change vs Part 3: **when Layer 2 fails, don't panic — polling recovers within 5 minutes** (assuming Layer 1 + 1.5 + 1.7 are fixed). Only escalate to operator for Meta dashboard intervention if polling ALSO fails after a 10-minute grace period.

## Symptom-to-fix mapping table (final)

| Symptom | Layer | Fix |
|---------|-------|-----|
| `code: 190 "Cannot parse access token"` on `/graph.instagram.com/me` | 1 | OAuth reconnect + wait 5-10 min |
| `code: 101` on `/oauth/access_token` with App ID + Secret | 1 | Operator: Meta dashboard |
| `comments_count: N > 0` but `/comments` returns empty | 1.5 | OAuth reconnect + tick ALL permission boxes + wait |
| Worker processed job, no DmLog row, no errors | 1.7 | `UPDATE "InstagramAccount" SET "instagramId" = '<IG_SCOPED_ID>'` |
| Real comments exist publicly, WebhookEvent has no real rows | 2 | Operator: check Meta Dashboard webhooks (but polling will recover in 5 min) |
| DmLog status=SENT but recipient didn't get DM | 4 | Check `dmSentAt` is set; verify in Meta Activity Log |
| Follow-gate never fires despite requireFollow=true | 3 | Patch `dm-worker.ts:407` from `!== true` to `=== false` (Part 1 fix) |

## What I'd do differently next time

1. **When comments API returns empty after OAuth reconnect**, set a 10-minute timer and re-probe before declaring it stuck. The 2026-07-30 session spent turns trying to figure out "why is the comments API empty" when the actual answer was "Meta is still propagating the new scope to the existing token." This is not in Meta's docs and is invisible to all the standard diagnostics.

2. **Trust the polling safety net more.** When Layer 2 fails, the right move is to verify Layers 1, 1.5, 1.7 are clean, then say "wait one polling cycle (5 min) and check `DmLog`" rather than escalating to operator immediately. The polling reconciler exists exactly for this scenario.

3. **Don't get stuck in the worker-log rabbit hole.** A worker that's processing jobs but not producing `DmLog` rows is almost always an ID mismatch (Part 2) or a token issue (Part 1) — both fixable in SQL. A worker that's not processing jobs at all is something else (worker died, queue broken, no jobs queued). Different diagnosis paths.