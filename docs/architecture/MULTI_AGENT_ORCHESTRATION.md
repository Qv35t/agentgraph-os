# Multi-Agent Orchestration

Phase 7 implements graph-defined, static DAG orchestration. A `team-v1` graph
is version 2 data containing only `agent-ref` workers, bounded instructions,
and directed edges. It never stores executable code, credentials, or provider
configuration.

`AgentManager` remains the only lifecycle authority. `TeamGraphRuntime` uses
its narrow delegation port to create normal child `AgentRun` records, persist a
`run_delegations` link, await their registered tasks, and request truthful
cancellation. It does not write run rows or call providers for workers.

Ready workers run with a server-bounded semaphore. A child receives the root
task, optional node instructions, and delimited, size-bounded predecessor
output. Worker output is untrusted data: it is never interpreted as authority,
tool approval, configuration, or executable content. Each worker keeps its own
model route, memory scope, and tool/approval policy.

Any required child failure, cancellation, timeout, or invalid reference fails
the parent. Stopping a parent recursively requests stop for live descendants
before its own terminal transition. On restart active runs become failed under
the existing recovery policy while durable delegation links remain inspectable.
Nested teams are permitted only within configured depth and ancestry bounds.

The read-authorized run-tree API derives a bounded hierarchy from
`run_delegations`; browser hierarchy presentation is observational only.
