# AgentGraph OS — Memory Design

Status: design target for Phase 5; no Phase 2/3 code should depend on this document as implemented behavior.

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

## Scope rules

Memory must be namespaced to prevent accidental cross-agent/workspace leakage. Retrieval must be deliberate and observable enough to understand what context was injected into a run.

## Data lifecycle

The design must cover creation, retrieval, retention, deletion/forget, unavailable storage, and migration/version behavior. Local memory must not be silently synchronized to cloud services.

## Security

Do not store provider credentials in memory. Treat retrieved memory as untrusted user/application data when it can influence model prompts or tool decisions.
