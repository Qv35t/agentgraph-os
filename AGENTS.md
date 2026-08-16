# AgentGraph OS — OpenCode Project Rules

AgentGraph OS is a **local-first visual operating environment for AI agents**.
This file is the small, always-loaded control plane for OpenCode. Detailed rules are intentionally split into focused files and must be loaded **lazily** only when relevant.

## 1. Non-negotiable project principles

1. **Local-first by default.** The project must remain useful without a cloud provider.
2. **Modular monolith first.** Do not introduce distributed infrastructure unless a later approved phase explicitly requires it.
3. **Provider-agnostic AI layer.** Agent/runtime code must not depend directly on Ollama, OpenAI, OpenRouter, or OpenCode-specific HTTP details.
4. **Explicit execution.** Model output is data. Never execute model text, code blocks, shell commands, tools, or filesystem actions implicitly.
5. **No secret leakage.** Never commit, print, persist, copy, or expose API keys, OAuth tokens, passwords, Authorization headers, or provider credential files.
6. **Preserve working code.** Extend existing reasonable modules instead of creating competing parallel implementations.
7. **No fake completion.** Do not claim a test, migration, smoke test, provider call, or acceptance criterion passed unless it was actually run and observed.
8. **Keep scope phase-bound.** Do not implement future-phase features merely because they are adjacent or convenient.
9. **Authorization before autonomy.** Planning, recommendation, model output,
   inferred project state, or a prior grant outside its scope never authorizes a
   new user-impacting action.

## 2. Current source of truth

Read `@docs/PROJECT_STATUS.md` at the start of any non-trivial task.

Instruction precedence for implementation decisions:

1. this `AGENTS.md`;
2. the active file in `docs/phases/`;
3. applicable file in `docs/agent-rules/`;
4. accepted ADRs in `docs/decisions/`;
5. `docs/ARCHITECTURE.md` and `docs/DEVELOPMENT.md`;
6. existing code and tests;
7. roadmap / vision documents.

If two sources conflict, do not silently choose. Preserve existing working behavior where safe, report the conflict, and update documentation when the decision becomes clear.

`PROJECT_STATUS.md` and the **Current State** sections of architecture records
describe what exists. `FUTURE_VISION.md`, target architecture sections, the
future roadmap, and target ADRs describe approved intent only. Never implement
or report a target capability as current behavior without an approved phase and
observed verification.

## 3. Lazy context loading — CRITICAL

OpenCode does not need every project document in every task.

When a referenced file is relevant, use the Read tool to load it. Do **not** pre-load every reference in this file.

### Always for non-trivial implementation

- `@docs/PROJECT_STATUS.md`
- `@docs/agent-rules/GENERAL.md`

### Load by work area

| Work area | Read these files |
|---|---|
| Backend/API/runtime/persistence | `@docs/agent-rules/BACKEND.md`, `@docs/TESTING.md` |
| Remote API/WebSocket/interfaces | `@docs/agent-rules/REMOTE_INTERFACES.md`, `@docs/architecture/REMOTE_INTERFACES.md`, `@docs/architecture/SECURITY_AND_TRUST.md`, `@docs/SECURITY.md` |
| Model router/providers/LLM | `@docs/agent-rules/MODELS.md`, `@docs/MODEL_ROUTER.md`, `@docs/SECURITY.md` |
| Vision/multimodal/assets/folders | `@docs/agent-rules/VISION.md`, `@docs/architecture/VISION.md`, `@docs/SECURITY.md`, `@docs/TESTING.md` |
| Frontend/React Flow/UI | `@docs/agent-rules/FRONTEND.md` |
| Frontend/browser/visual interface | `@docs/agent-rules/VISUAL_INTERFACE.md`, `@docs/architecture/VISUAL_INTERFACE.md`, `@docs/agent-rules/REMOTE_INTERFACES.md` |
| Memory/RAG/vector storage | `@docs/agent-rules/MEMORY.md`, `@docs/MEMORY.md`, `@docs/SECURITY.md` |
| Tools/Linux automation/Lexi integration | `@docs/agent-rules/TOOLS_AND_AUTOMATION.md`, `@docs/TOOLS.md`, `@docs/architecture/LEXI.md`, `@docs/SECURITY.md` |
| Distributed Core/recovery/storage | `@docs/architecture/DISTRIBUTED_RUNTIME.md`, `@docs/architecture/RESILIENCE_AND_RECOVERY.md`, `@docs/architecture/STORAGE_SEARCH_BACKUP.md`, `@docs/architecture/SECURITY_AND_TRUST.md` |
| OpenCode Coder Agent | `@docs/architecture/OPENCODE_INTEGRATION.md`, `@docs/agent-rules/TOOLS_AND_AUTOMATION.md`, `@docs/SECURITY.md` |
| Voice/proactive interaction | `@docs/architecture/VOICE_INTERACTION.md`, `@docs/architecture/LEXI.md`, `@docs/architecture/REMOTE_INTERFACES.md` |
| Architecture changes | `@docs/FUTURE_VISION.md`, `@docs/ARCHITECTURE.md`, `@docs/GLOSSARY.md`, `@docs/RISK_REGISTER.md`, `@docs/decisions/README.md` |
| Repo conventions / developer workflow | `@docs/DEVELOPMENT.md`, `@docs/REPOSITORY_STRUCTURE.md` |

### Load by active phase

- Phase 2 → `@docs/phases/PHASE_02_BACKEND_CORE.md`
- Phase 3 → `@docs/phases/PHASE_03_MODEL_ROUTER_REAL_LLM_PROVIDERS.md`
- Phase 4 → `@docs/phases/PHASE_04_VISUAL_INTERFACE.md`
- Phase 5 → `@docs/phases/PHASE_05_MEMORY.md`
- Phase 6 → `@docs/phases/PHASE_06_LEXI_INTEGRATION.md`
- Phase 7 → `@docs/phases/PHASE_07_MULTI_AGENT_ORCHESTRATION.md`
- Phase 8 → `@docs/phases/PHASE_08_FUTURE_ARCHITECTURE_BASELINE.md`

Prefer the matching `/phase-N` OpenCode command because it injects the correct phase context automatically.

## 4. Required workflow before editing

For any task larger than a trivial typo:

1. inspect `git status` and do not overwrite unrelated user changes;
2. read `docs/PROJECT_STATUS.md`;
3. identify the active phase and load only its phase file plus relevant domain rules;
4. inspect the existing implementation, dependency manifests, tests, config, and migrations before designing changes;
5. state assumptions internally and prefer surgical changes;
6. implement the smallest coherent slice;
7. run focused verification first, then broader checks when the slice is stable;
8. update docs only when behavior, contracts, architecture, setup, or status actually changed.

## 5. Repository boundaries

Canonical top-level areas established by the Foundation phase:

- `backend/` — FastAPI, runtime, persistence, providers, backend tests.
- `frontend/` — React + React Flow visual workspace.
- `agents/` — project-level agent definitions/templates if not better located inside backend domain code.
- `tools/` — controlled tool definitions/adapters; no arbitrary shell by default.
- `memory/` — memory-related configuration or service integration where appropriate.
- `models/` — metadata/configuration only; do not commit model weights.
- `plugins/` — future extension surface; not an excuse to build plugin runtime early.
- `configs/` — non-secret project configuration.
- `docs/` — architecture, phases, ADRs, security, status.
- `tests/` — cross-cutting tests if they do not belong under a component.
- `scripts/` — deterministic developer scripts.
- `docker/` — optional/container support only; local native development must not require Docker unless explicitly changed by an ADR.

Do not create a second structure simply because a phase specification uses example paths. Adapt examples to the real tree.

## 6. Technology direction

Foundation-level direction:

- Backend: Python 3.12+, FastAPI, Pydantic v2, LangGraph.
- Persistence for the early backend: SQLite + SQLAlchemy 2.x + Alembic.
- Frontend: React + TypeScript + React Flow.
- Local AI: Ollama.
- Subscription/provider bridge: local OpenCode Server where explicitly designed.
- OpenAI-compatible cloud path: optional, explicit, never required for local startup.
- Memory direction: future Qdrant / Mem0 adapters remain behind project-owned abstractions.

Do not pin new major frameworks or replace this stack without an ADR.

## 7. Quality requirements

- New public Python APIs require type hints.
- Validate external HTTP input using typed schemas.
- Keep API handlers thin; business/runtime logic belongs in services/runtime layers.
- Keep provider-native JSON and exceptions out of domain/service APIs.
- Automatic tests must not require real cloud credentials or mutate user data.
- Tests must use temporary/isolated databases and storage.
- Do not disable TLS verification, lint rules, type checks, or tests just to make a build green.
- Do not use `eval`, unsafe deserialization, arbitrary pickle loading, or implicit shell execution.
- Default network listeners must bind to `127.0.0.1` unless an explicit security-reviewed change says otherwise.

## 8. Documentation discipline

Keep these synchronized with real behavior:

- `docs/PROJECT_STATUS.md` — what is done / active / blocked.
- `docs/ROADMAP.md` — phase-level plan, not a daily task log.
- `docs/FUTURE_VISION.md` — stable approved product north star, not current behavior.
- `docs/ARCHITECTURE.md` — current architecture plus the linked target map.
- `docs/GLOSSARY.md` and `docs/RISK_REGISTER.md` — target terminology and major risks.
- `docs/decisions/` — decisions that would otherwise be repeatedly reconsidered.
- active phase file — acceptance gate and scope.

Do not mark a phase complete until its acceptance gate has actually passed.

## Remote interface architecture

All Web, TUI, messaging, native, and API clients MUST use shared AgentGraph OS
application/API contracts. They must not own or duplicate runtime orchestration,
provider routing, run state, approval semantics, or authorization. Runtime and
providers remain independent of UI and messaging SDKs; remote commands require
server-side authorization; client connections must not determine run lifetime.

## 9. Git behavior

- Never discard or reset user changes without an explicit request.
- Do not rewrite history.
- Do not commit secrets or generated local data.
- Do not create a commit/push/PR unless the user explicitly asks.
- Keep implementation changes phase-focused and reviewable.

## 10. Completion response expected from OpenCode

At the end of an implementation task, report succinctly:

1. what changed;
2. files changed;
3. verification actually run and exact result;
4. acceptance criteria satisfied / still open;
5. known limitations or next step.

Never represent unrun manual checks as completed.
