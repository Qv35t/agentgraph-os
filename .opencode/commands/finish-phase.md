---
description: Close a phase only after all required gates pass
agent: build
---

Use:

@docs/PROJECT_STATUS.md
@docs/ROADMAP.md
@docs/DEFINITION_OF_DONE.md
@docs/ARCHITECTURE.md

Read the active phase specification. Verify every mandatory automated and manual gate. Do not substitute "should work" for execution evidence.

If every required gate passes:

- update PROJECT_STATUS;
- update architecture/setup docs to reflect actual behavior;
- keep historical roadmap sequence intact;
- summarize evidence.

If any gate fails or was not run, do not mark the phase done. Return the exact remaining checklist.
