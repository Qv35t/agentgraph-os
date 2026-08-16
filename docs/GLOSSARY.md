# AgentGraph OS Glossary

Terms describe the target architecture unless explicitly labeled current.

| Term | Meaning |
|---|---|
| Agent | A configured specialized runtime participant with its own model, memory, and tool policy. |
| Main Agent | The user-facing coordinator role. Lexi is the planned Main Agent. |
| Lexi | The current Phase 6 assistant workflow and target Main Agent role; target orchestration is not implemented. |
| Core | The target authoritative coordination service for policy, durable state, scheduling, and run history. |
| Primary Core | The normal active Core, planned for the NAS. |
| Backup Core | An eligible node that may take over after fenced failover and recovery from committed state. |
| Node | A registered machine participating in the target topology. |
| Worker Node | A Node with bounded advertised capabilities; it is not a Core authority. |
| Device | A physical or virtual machine represented as a Node when registered. |
| Graph | A declarative execution topology. The current `team-v1` graph is a validated static DAG. |
| Run | One durable execution attempt with state, outputs, events, approvals, and target checkpoint history. |
| Workflow | A saved, versioned reusable graph/template. It is distinct from a Run and does not grant authority. |
| Goal | A long-lived user outcome that groups Projects. |
| Project | A bounded body of work that groups Phases, Tasks, context, and related Runs. |
| Phase | A planned, reviewable implementation increment or project stage. |
| Task | A scoped unit of work within a Project that can produce one or more Runs. |
| Approval | A user decision for a proposed action. Current approvals are process-local; durable approval is planned. |
| Grant | A revocable, auditable, time- and scope-bounded permission derived from an approval. |
| Checkpoint | A versioned durable snapshot used to evaluate safe recovery of a Run. |
| Memory | User-owned durable context. Retrieved memory is untrusted input, never authority. |
| Provenance | Source, timing, confidence, scope, and supersession history attached to a memory or derived project status. |
| Secret | A sensitive value such as a key, token, password, or private key. |
| Credential Broker | A planned service that performs scoped credential operations without normally revealing raw secrets to agents. |
| Remote View | A planned read-oriented view of a registered device, application, terminal, or files. |
| Local Only | A planned enforced routing policy that prohibits task-data egress to external AI providers. |
