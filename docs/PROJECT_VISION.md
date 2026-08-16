# AgentGraph OS — Original MVP Vision

Status: historical MVP framing. The approved Post-Phase-7 target north star is
[`FUTURE_VISION.md`](FUTURE_VISION.md); current implementation facts are in
[`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## Purpose

AgentGraph OS is a local-first environment for building, running, observing, and composing AI agents through a visual workflow rather than a collection of disconnected scripts.

The project should make it practical to combine:

- local LLMs;
- optional cloud/subscription-backed models;
- LangGraph-based agent execution;
- visual graphs;
- persistent state and memory;
- controlled tools and Linux automation;
- Lexi as a completed Phase 6 workflow, with broader orchestration planned.

## Product principles

### Local-first
A useful core must work on a Linux machine with local storage and local models. Cloud services are optional capabilities, not mandatory infrastructure.

### Visible orchestration
The user should be able to understand which agent exists, what model it uses, what graph it runs, what state a run is in, and what failed.

### Explicit capabilities
A model response never automatically becomes an action. Tools, automation, filesystem access, network access, and OS control require explicit typed boundaries and policy.

### Replaceable providers
Ollama, OpenCode, OpenRouter, or another provider must be adapters behind an internal model contract rather than dependencies embedded throughout the application.

### Incremental architecture
Start as a modular monolith. Introduce external services only when the product needs them and the trade-off is recorded.

## MVP direction

The original MVP direction is preserved:

- visual graph workspace;
- multiple agent types/workflows;
- local Ollama execution;
- GPT-capable path through an explicit provider boundary;
- memory;
- controlled tools;
- observable workflow execution.

The numbered roadmap remains the canonical order. Future capabilities must not bypass current phase gates.
