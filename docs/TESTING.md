# AgentGraph OS — Testing Strategy

## Goal

Tests must prove lifecycle and contracts without requiring the owner's real credentials, cloud quota, user database, or local model collection.

## Test layers

### Unit

Use for parsers, state transitions, routing policy, normalized errors, repositories with isolated fixtures, and pure graph nodes.

### Integration

Use for FastAPI + service + persistence + runtime interactions using temporary resources.

### Provider contract tests

Mock transport/protocol responses. Test timeouts, malformed responses, authentication/rate-limit mapping, model-not-found, and cancellation without real cloud calls.

### Live smoke tests

Separate from automated CI. Examples: local Ollama call or already-configured OpenCode Server. Never make them mandatory for normal unit/integration tests.

## Isolation rules

Automated tests must:

- use temporary DB/storage;
- never touch the user's `data/agentgraph.db` or equivalent;
- not require OpenCode OAuth state;
- not require real OpenRouter/OpenAI credentials;
- not pull models;
- not depend on test order;
- clean up async tasks/clients.

## Truthful reporting

Allowed:

```text
pytest tests/test_runtime.py -q -> 12 passed
```

Not allowed:

```text
Tests should pass.
All tests pass.   # when not executed
```

If an environmental live smoke test cannot run, report it as `NOT RUN` with the exact reason.
