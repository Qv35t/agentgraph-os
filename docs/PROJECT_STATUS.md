# AgentGraph OS — Project Status

Last updated: **2026-08-11**

## Current phase

**Phase 3 - Model Router and Providers is complete. Phase 4 - Visual Interface
is next, but has not started.**

The Foundation gate was independently verified on 2026-08-11 through the
offline repository check and a manual repository audit. No backend, provider,
frontend, memory, tool, or Lexi implementation was introduced as part of this
verification.

| Phase | State | Gate |
|---|---|---|
| 1 — Foundation | DONE | Structure, documentation, security baseline, model metadata, and `pnpm check` verified |
| 2 — Backend Core | DONE | FastAPI lifecycle API, SQLite/Alembic, LangGraph, cancellation, recovery, tests, and `pnpm check` verified |
| 3 — Model Router & Providers | DONE | Router, three adapters, LLM graph, metadata, provider API, tests, and live Ollama verified |
| 4 — Visual Interface | NEXT | Requires explicit owner instruction |
| 5 — Memory | PLANNED | Requires stable runtime/UI contracts |
| 6 — Lexi Integration | PLANNED | Requires preceding relevant gates |

## Verified repository facts before this documentation pack

At documentation preparation time, the public repository already contained:

- a README describing React + React Flow, Python + FastAPI + LangGraph, Ollama/OpenAI/OpenRouter, Qdrant/Mem0;
- a local-first architecture stub;
- a six-phase roadmap;
- a `.gitignore` covering environment files, Python/Node outputs, databases, model weights, logs, Qdrant storage, credentials, and key files.

## Next action

Phase 4 may begin only after an explicit owner instruction. Its OpenCode command
is:

```text
/phase-4
```

Before writing code, OpenCode must inspect the actual repository tree and dependency manifests. The phase file contains architecture targets, not permission to duplicate already-correct modules.

## Status update rule

Only move a phase to `DONE` after:

1. automated checks required by the phase pass;
2. required migrations/startup checks pass;
3. manual smoke checks explicitly required by the phase are actually executed;
4. architecture/docs reflect implemented behavior;
5. known deviations are documented.
