# AgentGraph OS — Memory Design

Status: SQLite Memory MVP implemented in Phase 6. Qdrant and Mem0 remain future adapters.

## Goal

Memory gives an agent explicit durable context across runs while keeping storage local-first, scoped, deletable, and replaceable.

## Boundary

```text
Runtime / Agent
      ↓
MemoryService / project-owned contracts
      ├─ write
      ├─ retrieve
      ├─ delete
      └─ lifecycle policy
      ↓
Memory adapter(s)
      ├─ Qdrant direction
      └─ optional Mem0 adapter
```

Qdrant and Mem0 are adapters, not application-wide domain types.

## Current implementation

- `MemoryService` persists records locally in SQLite through SQLAlchemy/Alembic.
- Every record is scoped by `project_id` and `agent_id`; retrieval never has an
  unscoped path.
- The initial retrieval adapter is deterministic bounded lexical matching, not
  semantic/vector search. It applies configured result and context-size limits.
- Lexi records the injected memory IDs, rank, and lexical score in a normalized
  run-memory link table. Prompts are not persisted for this purpose.
- Delete is a local soft-forget operation: deleted records cannot be listed or
  retrieved in later runs while existing run links remain inspectable.
- Retrieved records are wrapped as untrusted context and cannot grant tool or
  permission policy.

## Scope rules

Memory must be namespaced to prevent accidental cross-agent/workspace leakage. Retrieval must be deliberate and observable enough to understand what context was injected into a run.

## Data lifecycle

The design must cover creation, retrieval, retention, deletion/forget, unavailable storage, and migration/version behavior. Local memory must not be silently synchronized to cloud services.

## Security

Do not store provider credentials in memory. Treat retrieved memory as untrusted user/application data when it can influence model prompts or tool decisions.
