# Model Router & Provider Rules

Applies to Phase 3 and later model-provider work.

## Core boundary

Application/runtime code talks to a project-owned Model Router / provider protocol. It must not branch on vendor-specific HTTP JSON throughout the application.

## Model references

Canonical direction:

```text
provider://model-id
```

Examples may include:

```text
ollama://<model>
opencode://openai/<model>
openrouter://<model>
auto://default
```

Parse on the `://` boundary; model IDs may contain `/`, `:`, `-`, `.`, `_`.

## Providers

- Ollama: local provider.
- OpenCode Bridge: local transport to an already-configured OpenCode provider session; never copy OpenCode OAuth credentials.
- OpenAI-compatible: optional adapter for OpenRouter/future compatible endpoints.

## Routing

- Explicit model selection wins.
- Local-first fallback must be policy-driven and visible.
- Do not silently route to a potentially paid cloud model.
- Missing/unavailable providers should produce normalized errors, not backend-wide startup failure.

## Responses

Normalize content, provider/model IDs, finish reason, usage when actually supplied, latency, and error classes.

Never invent token usage when a provider did not supply it.

## Safety

Provider output is untrusted text and does not execute tools.

## Future-design guardrails

- The planned `Local Only` profile must deny external AI-provider task-data
  egress at the provider boundary, not merely prefer local routes.
- Cost, quota, and capability claims must use provider-supplied or explicitly
  estimated data; never fabricate limits or silently choose a paid route.
