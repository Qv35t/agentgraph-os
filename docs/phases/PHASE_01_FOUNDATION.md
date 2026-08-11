# Phase 1 - Foundation

## Mission

Establish a secure, local-first repository foundation for AgentGraph OS. This
phase creates the project structure, governing documentation, non-secret
configuration, quality checks, and development workflow required by later
implementation phases.

Phase 1 is intentionally not a product implementation phase.

## Scope

### Required

1. Create the top-level responsibility areas: `backend/`, `frontend/`,
   `agents/`, `tools/`, `memory/`, `models/`, `plugins/`, `configs/`,
   `tests/`, `scripts/`, and `docker/`.
2. Document the local-first modular-monolith architecture and dependency
   direction.
3. Define the six-phase roadmap and phase-gated delivery process.
4. Add project instructions, domain rules, ADRs, and OpenCode commands for
   repeatable development.
5. Add Apache-2.0 licensing and a non-secret `.env.example`.
6. Add Git exclusions for secrets, runtime databases, caches, model artifacts,
   logs, and build outputs.
7. Record model metadata without calling providers:
   `qwen3-4b-nothink:latest`, `qwen3:4B`, and `qwen3:0.6B`.
8. Document GPT Plus as a future OpenCode local bridge integration, not as an
   OpenAI API credential.
9. Provide an offline `pnpm check` command that verifies the Foundation
   artifacts.

### Explicitly Out of Scope

- FastAPI, SQLAlchemy, Alembic, SQLite schema, or API handlers.
- LangGraph runtime or agent lifecycle execution.
- Real Ollama, OpenCode, OpenAI, or OpenRouter calls.
- Provider credential setup, provider health checks, or model discovery.
- React, TypeScript, React Flow, or a frontend application.
- Qdrant, Mem0, embeddings, retrieval, or persistent memory.
- Shell, browser, filesystem, MCP, or Linux automation tools.
- Lexi integration.
- Distributed infrastructure, cloud-required startup, or mandatory Docker.

## Architecture Rules

- Start as a local-first modular monolith.
- Bind application services to `127.0.0.1` by default.
- Keep cloud and subscription-backed models optional and explicitly selected.
- Keep provider-specific protocols behind project-owned contracts in Phase 3.
- Treat model output as untrusted text. It never implicitly executes actions.
- OpenCode owns any subscription authentication. AgentGraph must not read,
  copy, persist, or expose OpenCode credentials.

## Model Metadata

The expected future model references are:

```text
ollama://qwen3-4b-nothink:latest  default local model
ollama://qwen3:4B                 local quality model
ollama://qwen3:0.6B               local fast model
opencode://openai/<discovered-id> explicit GPT Plus bridge model
```

`auto://default` must resolve to the local default model. It must not silently
fall back to GPT Plus or another cloud-backed provider.

## Security Rules

- Do not commit API keys, OAuth tokens, passwords, Authorization headers,
  private keys, copied provider credentials, databases, logs, or model files.
- Keep real environment values outside the repository.
- Do not disable TLS verification.
- Do not use `eval`, `exec`, unsafe pickle deserialization, or arbitrary shell
  execution for user or model data.
- Do not expose application services to a network beyond loopback without a
  future security review and explicit design.

## Verification Gate

Phase 1 is complete only when all conditions below are observed:

1. The required top-level project structure exists.
2. The architecture, roadmap, status, security, testing, and development
   documents exist and agree on the phase order.
3. Accepted ADRs cover modular-monolith, local-first, provider-agnostic model
   routing, and the OpenCode authentication boundary.
4. Apache-2.0 and a secret-free `.env.example` exist.
5. `.gitignore` covers environment files, databases, model artifacts, caches,
   logs, build outputs, and credentials.
6. Local model metadata matches the user's available Ollama models.
7. GPT Plus is documented only as an explicit future OpenCode bridge path.
8. No backend, frontend, provider, memory, tool, or Lexi implementation was
   introduced.
9. `pnpm check` passes from the repository root.
10. The result is recorded truthfully in `docs/PROJECT_STATUS.md`.

## Completion

After this gate passes, mark Phase 1 as `DONE` and Phase 2 as `NEXT`. This
does not authorize implementation of Phase 2 until it is explicitly started.
