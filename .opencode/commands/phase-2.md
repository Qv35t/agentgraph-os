---
description: Start or continue Phase 2 Backend Core
agent: build
---

Implement or continue **AgentGraph OS Phase 2 — Backend Core**.

Mandatory context for this command:

@docs/PROJECT_STATUS.md
@docs/phases/PHASE_02_BACKEND_CORE.md
@docs/agent-rules/GENERAL.md
@docs/agent-rules/BACKEND.md
@docs/TESTING.md
@docs/SECURITY.md

First inspect the actual repository, `git status`, backend tree, dependency manifests, configs, migrations, tests, and existing docs. Do not create a parallel architecture when a reasonable implementation already exists.

Work incrementally. Run focused tests after each coherent slice. Do not implement Phase 3 providers, frontend, memory, arbitrary tools, or future infrastructure.

At the end, report exact verification executed and evaluate the Phase 2 gate. Update `docs/PROJECT_STATUS.md` only if the gate actually passed.
