# Phase 10 Manual Acceptance

Status: PASSED on 2026-08-17. The owner completed and confirmed this
same-machine fault-injection drill.

## Same-Machine Recovery Drill

1. Start the Core with a migrated local SQLite database and the browser UI.
2. Start a local run and verify its Run page shows durable recovery history.
3. For a controlled-tool drill, use a harmless allowlisted test application and
   approve the action. Stop the Core after the action is recorded as started but
   before terminal completion.
4. Restart the Core against the same database. Verify the interrupted run is
   `failed`, recovery history contains `blocked_uncertain_action`, and no tool,
   provider, run, or worker work is replayed automatically.
5. Repeat with a run that has no action in flight. Verify recovery records
   `stopped_no_replay` and still does not resume the run.
6. Corrupt a copied test database checkpoint only, restart against that copy,
   and verify `blocked_corrupt_checkpoint` is visible while the Core remains
   available.

## Expected Limits

- Recovery assesses and stops interrupted work; it does not resume or retry it.
- Rollback is not offered for current actions.
- Fenced failover, backup restore, distributed execution, and scheduling are
  not implemented in Phase 10.
