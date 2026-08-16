# Resilience and Recovery Target

Status: approved target architecture. Current restart recovery marks active runs failed; checkpoint/resume is not implemented.

## Checkpoints

Long-running target Runs require versioned checkpoints containing graph/task state, completed and pending nodes, agent/device assignments, outputs, decisions, approvals/grants, retry counters, changed resources, and external-action references. A checkpoint is valid only after durable commit; it is not proof that an external side effect completed.

## Recovery and Rollback

After restart or failover, the future Core must identify incomplete Runs, load the latest valid checkpoint, validate observable external effects, and resume only safe work. It must not repeat irreversible or uncertain side effects. Those cases require approval or a blocker report. Process restart must not silently discard target Run history.

The target task ledger relates a Run to files, Git state, configuration, memory, artifacts, and other changed resources. Rollback is explicit and only offered where an action is technically reversible. Irreversible external actions keep an audit record rather than a false rollback promise.

Recovery decisions, checkpoint versions, failed validation, retry budget use, and failover promotion must be visible in Run history. Automatic remediation comes only after observability and recovery correctness. See [`DISTRIBUTED_RUNTIME.md`](DISTRIBUTED_RUNTIME.md) and [`RISK_REGISTER.md`](../RISK_REGISTER.md).
