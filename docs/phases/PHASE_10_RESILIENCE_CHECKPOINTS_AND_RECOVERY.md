# Phase 10 - Resilience, Checkpoints, and Recovery

Status: DONE. Automated verification, migration upgrade/downgrade validation,
production frontend build, and the manual same-machine fault-injection drill
passed on 2026-08-17.

## Implemented Scope

- Local SQLite runs receive a versioned initial checkpoint atomically with run
  creation, plus durable running and terminal lifecycle checkpoints.
- An action ledger records controlled-tool intent before its effect boundary,
  then records started, confirmed, failed, or uncertain state.
- Core startup assesses interrupted runs from their latest checkpoint and action
  ledger, persists a recovery decision, and marks the run failed without replay.
- Recovery history is visible through a read-only run API and browser Run page.

## Recovery Semantics

Recovery is deliberately conservative. A valid checkpoint without an uncertain
action produces `stopped_no_replay`; missing/corrupt checkpoints and started or
uncertain actions produce explicit blocker outcomes. No recovery path invokes a
provider, tool, runtime, worker, retry, resume, rollback, or approval flow.

## Boundaries

Phase 10 does not implement Core failover or promotion, remote scheduling or
execution, distributed recovery, checkpoint resume, automatic retry/replay,
backup/restore, or general rollback. Fenced failover remains a later design and
implementation concern under ADR-0006.

## Gate

Backend/frontend tests, lint, type checking, migration upgrade/downgrade
verification, production frontend build, documentation links, and the manual
fault-injection recovery drill passed on 2026-08-17. See
[`../PHASE_10_MANUAL_ACCEPTANCE.md`](../PHASE_10_MANUAL_ACCEPTANCE.md).
