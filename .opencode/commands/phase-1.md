---
description: Audit or complete Phase 1 Foundation
agent: build
---

Implement or audit **AgentGraph OS Phase 1 - Foundation** only.

Mandatory context for this command:

@docs/PROJECT_STATUS.md
@docs/phases/PHASE_01_FOUNDATION.md
@docs/ARCHITECTURE.md
@docs/SECURITY.md
@docs/DEVELOPMENT.md
@docs/DEFINITION_OF_DONE.md

Inspect the real repository and `git status` before editing. Do not overwrite
unrelated user changes. Do not implement backend, frontend, provider, memory,
tool, or Lexi runtime code.

Run `pnpm check` from the repository root. Mark the phase complete only when
the Phase 1 verification gate has actually passed. Report exact files changed
and verification results.
