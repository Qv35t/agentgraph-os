# Resilience and Recovery Target

Status: Phase 10 local recovery foundation is DONE. Durable checkpoints,
controlled-action ledger records, and conservative restart assessment passed
automated and manual same-machine fault-injection acceptance on 2026-08-17.

## Current Phase 10 Foundation

The single local Core captures an immutable execution specification in an
initial checkpoint, records lifecycle checkpoints, and writes controlled-tool
intent before the external-effect boundary. On startup, it validates the latest
checkpoint checksum and action ledger, persists a recovery decision, and marks
interrupted runs failed. It never retries, resumes, rolls back, replays a tool,
or invokes a provider during recovery. Missing/corrupt checkpoints and uncertain
actions are visible blockers through the Run recovery API and browser panel.

## Checkpoints

Long-running target Runs require versioned checkpoints containing graph/task state, completed and pending nodes, agent/device assignments, outputs, decisions, approvals/grants, retry counters, changed resources, and external-action references. A checkpoint is valid only after durable commit; it is not proof that an external side effect completed.

## Recovery and Rollback

After restart or failover, the future Core must identify incomplete Runs, load the latest valid checkpoint, validate observable external effects, and resume only safe work. It must not repeat irreversible or uncertain side effects. Those cases require approval or a blocker report. Process restart must not silently discard target Run history.

The target task ledger relates a Run to files, Git state, configuration, memory, artifacts, and other changed resources. Rollback is explicit and only offered where an action is technically reversible. Irreversible external actions keep an audit record rather than a false rollback promise.

Recovery decisions, checkpoint versions, failed validation, retry budget use, and failover promotion must be visible in Run history. Automatic remediation comes only after observability and recovery correctness. See [`DISTRIBUTED_RUNTIME.md`](DISTRIBUTED_RUNTIME.md) and [`RISK_REGISTER.md`](../RISK_REGISTER.md).
