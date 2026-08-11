# Phase 3 — Model Router & Real LLM Providers

Status: **DONE** on 2026-08-11. Automated checks and live Ollama checks passed.
OpenCode and cloud live checks were `NOT RUN` because no endpoint/secret was
configured; their mocked contract tests passed. The final isolated suite
contains 34 tests.

## Mission

Replace the deterministic Phase 2 model execution path with real provider-agnostic LLM execution while preserving stable agent/run lifecycle and local-first startup.

## Preconditions

Phase 2 gate is complete. Extend its actual service/runtime/persistence layout; do not build a second backend architecture.

## Architecture target

```text
AgentManager
    ↓
LangGraph Runtime
    ↓
ModelRouter
    ├─ OllamaProvider ─────────────► local Ollama
    ├─ OpenCodeBridgeProvider ─────► local OpenCode Server
    └─ OpenAICompatibleProvider ───► optional OpenRouter/compatible API
```

AgentManager, API handlers, and general LangGraph code do not know provider HTTP details.

## Required scope

1. strict `ModelRef` parser;
2. provider-agnostic request/response/usage/capability DTOs;
3. normalized provider errors;
4. ProviderRegistry;
5. ModelRouter + explicit routing/fallback policy;
6. reusable async HTTP client lifecycle;
7. Ollama provider health, discovery, real completion;
8. OpenCode local bridge health/discovery/completion;
9. generic OpenAI-compatible provider with optional OpenRouter config;
10. timeouts and cancellation propagation;
11. provider visibility API;
12. real LLM node inside LangGraph;
13. normalized LLM metadata persisted on runs where available;
14. transport-mocked automated tests;
15. separate live smoke procedures.

## Out of scope

- RAG/long-term memory;
- arbitrary tools/shell/browser/MCP;
- multi-agent orchestration;
- frontend;
- scheduler/background jobs;
- provider billing dashboard;
- distributed workers.

## Model reference direction

Canonical:

```text
provider://model-id
```

Examples:

```text
ollama://qwen3:4b
opencode://openai/<discovered-model-id>
openrouter://<provider/model-id>
auto://default
```

Preserve real Phase 2 placeholder values with an explicit compatibility mapping rather than breaking existing data.

## Local-first routing

- Explicit `model_ref` wins.
- `auto://default` resolves via documented policy.
- Never select a random paid cloud model.
- Cloud fallback is disabled unless explicitly enabled.
- Provider failure does not make the backend health endpoint fail globally.

## OpenCode bridge security boundary

AgentGraph may call a local OpenCode Server. It must not read or copy OpenCode's OAuth credential store.

The user configures provider authentication in OpenCode separately. AgentGraph knows only the local server address and optional local server Basic Auth credentials supplied through environment variables.

Do not implement a reverse-engineered ChatGPT web client.

Bridge mode is LLM transport only:

```text
prompt/messages in → model response out
```

Disable OpenCode tools/file writes/shell/MCP/browser capabilities as far as the current server contract allows for this transport path.

## Secrets

- `.env.example` contains empty placeholders.
- API keys/passwords never enter DB/logs/API responses.
- Provider raw errors are sanitized.
- TLS verification remains enabled for HTTPS providers.

## Ollama

- default loopback URL direction: `http://127.0.0.1:11434`;
- health/model discovery;
- model-not-found normalization;
- real chat/completion;
- timeout/connection/malformed-response/cancellation handling;
- do not pull models automatically on startup.

## OpenAI-compatible provider

Optional and disabled unless configured. Credentials come only from runtime environment/local secret config. Use a project-owned adapter rather than leaking vendor SDK objects through the domain.

## Verification gate

Automated tests must not require internet or real OAuth/API keys. Mock HTTP transport and cover routing/error/cancellation behavior.

Live smoke checks are separate:

1. Ollama reachable and a user-existing local model completes through AgentGraph, if available;
2. OpenCode Server reachable and an already-configured model completes through the bridge, if available;
3. cloud/OpenRouter live smoke only when owner explicitly provides/configures credentials and wants it run.

Unavailable live prerequisites are reported `NOT RUN`, never faked.

## Completion

After passing required gate:

- update architecture with actual ModelRouter/provider modules;
- update model configuration docs/README;
- update PROJECT_STATUS: Phase 3 DONE, Phase 4 NEXT;
- preserve Phase 2 API compatibility unless a documented migration is necessary.
