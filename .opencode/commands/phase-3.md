---
description: Start or continue Phase 3 Model Router and providers
agent: build
---

Implement or continue **AgentGraph OS Phase 3 — Model Router & Real LLM Providers**.

Mandatory context:

@docs/PROJECT_STATUS.md
@docs/phases/PHASE_03_MODEL_ROUTER_REAL_LLM_PROVIDERS.md
@docs/agent-rules/GENERAL.md
@docs/agent-rules/BACKEND.md
@docs/agent-rules/MODELS.md
@docs/MODEL_ROUTER.md
@docs/TESTING.md
@docs/SECURITY.md
@docs/decisions/ADR-0003-provider-agnostic-model-router.md
@docs/decisions/ADR-0004-opencode-auth-boundary.md

Before editing, verify that Phase 2 is actually complete and inspect its real architecture/contracts. Extend it rather than rebuilding it.

Never read/copy OpenCode OAuth credential files. Automated tests must not use real cloud auth. Keep provider output as data; no implicit tools.

At the end, report exact tests/live checks actually run and update project status only if the phase gate passed.
