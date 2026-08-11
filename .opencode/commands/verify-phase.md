---
description: Verify the active phase without adding new scope
agent: build
---

Read:

@docs/PROJECT_STATUS.md
@docs/DEFINITION_OF_DONE.md
@docs/TESTING.md

Determine the active phase from PROJECT_STATUS and read only that phase specification plus relevant domain rules.

Run the repository's actual configured verification commands. Do not invent missing tools and do not modify product behavior merely to hide a failing test. Fix only clear defects within current phase scope.

Return an acceptance matrix: PASS / FAIL / NOT RUN with exact evidence. Update PROJECT_STATUS only if all mandatory phase gates are satisfied.
