# Recurring-output delta check

Use this reference when a scheduled report consumes a previous report or artifact: Dreaming Sequence, Morning Brief, health summaries, inbox digests, deployment status reports, and similar routines.

## Evidence model

Treat these as separate evidence layers, not interchangeable truth:

1. **Current scheduler metadata** — current `last_status`, `last_run_at`, `next_run_at`, and current job definition.
2. **Latest execution artifact** — the actual run output, log, or saved report, with its timestamp.
3. **Fresh live probes** — service endpoints, process state, queue/database state, and user-visible side-effect checks.
4. **Previous report** — continuity context only; never proof of current state.

Reconcile contradictions by checking freshness, timestamp semantics, and what each signal actually measures. A prior report saying a routine failed must not survive unchanged after a later execution artifact proves success. Conversely, a current scheduler `ok` or HTTP 200 does not prove that the application workload completed correctly.

## Per-item delta procedure

For every prior recommendation or outstanding item, assign one status:

- **resolved** — fresh evidence demonstrates the condition is fixed; remove it from the next recommendations unless a follow-up remains.
- **unchanged** — the same condition is still evidenced; carry it forward with the new age and evidence, not yesterday's wording.
- **worsened** — new evidence increases impact, scope, or urgency; raise priority and state the delta.
- **unverified** — evidence is stale, contradictory, or only inferred; say what proof is missing instead of asserting a conclusion.

Do not generate a recommendation merely because it appeared in the previous JSON. Re-derive the day's list from the delta states.

## Liveness versus workload health

Separate **control-plane liveness** from **data-plane/workload health**:

- Liveness signals include HTTP 200, an active process, a healthy heartbeat, or a scheduler `ok`.
- Workload signals include queue waiting/active/delayed/failed counts, domain error records, successful external sends, and matching application logs.

A service can report `status=ok` with a healthy worker while a queue contains failed jobs. Record both facts and classify the failed item read-only before recommending retry, replay, deletion, or discard; external side effects may already have happened and blind retries can duplicate them.

Also record the **deployed revision/image** separately from the local worktree. A live endpoint validates the deployed revision only; it does not validate an uncommitted local diff.

## Time and output hygiene

- Convert displayed times to the operator's SGT (`Asia/Singapore`) first; retain source-native timestamps in parentheses where useful.
- Use the current SGT date in the saved artifact, not a stale date from the previous report or cron listing.
- Keep `non_negotiable` exactly as the consumer expects; validate top-level shape, recommendation count/order, and JSON parsing before finishing.

## Session-derived example

In one run, an old Hermes update error was superseded by a later execution artifact showing a successful update and passing dashboard/gateway/proxy checks, so the update repair recommendation had to be removed. At the same time, OpenReply's live HTTP 200 and healthy worker did not validate its uncommitted local follow-gate diff; a non-zero failed queue count remained a separate workload item. The correct report kept the unresolved code verification and queue classification, while dropping the resolved update alert.
