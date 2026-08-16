# AgentGraph OS — Model Router Design

Status: implemented and verified in Phase 3.

## Purpose

The Model Router is the single application boundary for selecting and invoking LLM providers. Agent code, API handlers, and general LangGraph nodes must not know how a specific provider authenticates or formats HTTP payloads.

## Target flow

```text
ModelRequest
    ↓
ModelRouter
    ├─ explicit model_ref resolution
    ├─ routing/fallback policy
    └─ ProviderRegistry
          ├─ OllamaProvider
          ├─ OpenCodeBridgeProvider
          └─ OpenAICompatibleProvider
    ↓
Normalized ModelResponse / normalized error
```

## Contracts

The project owns normalized message/request/response/usage/health/capability/error contracts. Provider-native JSON remains inside adapters.

Canonical model reference direction:

```text
provider://model-id
```

The router must not guess a paid cloud model. Explicit selection wins; automatic fallback follows explicit configuration policy.

## Provider health

Provider availability is separate from backend health. AgentGraph can start while Ollama, OpenCode Server, or an optional cloud provider is unavailable.

## OpenCode bridge

OpenCode is a separate local process and owns its own provider authentication. AgentGraph uses only the local server API and optional local Basic Auth supplied through environment configuration. AgentGraph never reads/copies OpenCode OAuth credential files.

## Persistence

Persist only normalized run metadata that is useful for history/observability. Never persist API keys, OAuth tokens, passwords, Authorization headers, or raw secret-bearing provider responses.

## Testing

Automated provider tests use mocked transport and deterministic responses. Live Ollama/OpenCode checks are separate smoke tests and may be `NOT RUN` when prerequisites are absent.

## Implemented policy

- `auto://default` resolves to `ollama://qwen3-4b-nothink:latest`.
- Explicit Ollama, OpenCode, and OpenRouter-compatible references never fall
  back silently.
- `GET /api/providers` exposes safe availability and discovered model IDs.
- OpenCode uses `/global/health`, `/config/providers`, and temporary sessions
  with wildcard-deny permissions. Basic Auth is environment-only.
- OpenAI-compatible credentials remain environment-only and the adapter is
  disabled until its API base URL ending in `/v1` is configured. Credentialed
  non-loopback endpoints require HTTPS.

## Approved Target: Routing Profiles

The target router adds explicit user policies: `Local Only`, `Balanced`, `Best
Quality`, and `Cheapest`. `Local Only` is an enforced security boundary, not a
routing hint: it prohibits cloud inference and transmission of prompts, files,
images, embeddings, or context to external AI providers. Enforcement belongs at
the provider boundary and must be observable and tested.

`Balanced`, `Best Quality`, and `Cheapest` choose only among policy-permitted
models and providers. The router may evaluate estimated cost, documented provider
limits, context limits, latency, model capabilities, local availability, and
device capabilities, but must not invent unavailable provider billing or quota
APIs. Explicit model selection and denial policy still win over convenience.

These profiles and cost controls are target work, not current ModelRouter
behavior. See ADR-0010 and [`RISK_REGISTER.md`](RISK_REGISTER.md).
