---
description: Start or continue Phase 9 distributed Core foundation
agent: build
---

Implement or continue **Phase 9 - Distributed Core Foundation**.

Read:

@docs/PROJECT_STATUS.md
@docs/phases/PHASE_09_DISTRIBUTED_CORE_FOUNDATION.md
@docs/architecture/DISTRIBUTED_RUNTIME.md
@docs/architecture/REMOTE_INTERFACES.md
@docs/architecture/SECURITY_AND_TRUST.md
@docs/agent-rules/GENERAL.md
@docs/agent-rules/BACKEND.md
@docs/agent-rules/REMOTE_INTERFACES.md
@docs/agent-rules/FRONTEND.md
@docs/SECURITY.md

Core owns coordination and persistent global state. Workers provide only bounded
execution through authenticated typed contracts; never introduce a second
orchestration implementation, arbitrary remote shell, or bypass of Core policy.
