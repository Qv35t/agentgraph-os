# Memory Rules

Applies to Phase 6 and later memory work.

## Principles

- Memory is an explicit runtime capability, not hidden global prompt accumulation.
- Keep memory scoped by agent/workspace/user-owned namespace.
- Separate storage/indexing adapters from project-owned memory contracts.
- Local storage is the default path.
- Retrieval must be observable/testable enough to explain what was injected into a run.

## Qdrant / Mem0

They are integration directions, not domain models. Do not spread their native types across the runtime.

## Data lifecycle

Design for:

- create/write;
- retrieve;
- update where meaningful;
- delete/forget;
- retention boundaries;
- corruption/unavailable-store behavior.

Do not silently upload memory content to cloud providers.

## Future-design guardrails

- Significant target memory must carry provenance and supersession/revocation
  state; do not overwrite history to hide a correction.
- Retrieved memory is context, never authority to execute tools, expand scope,
  or bypass approval.
