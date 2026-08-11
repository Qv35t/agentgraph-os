# Phase Specifications

Each file is a task-scoped contract for one roadmap phase, including the
Foundation contract in `PHASE_01_FOUNDATION.md`.

Do not load all phase files into a single OpenCode task. Use the corresponding `.opencode/commands/phase-N.md` command.

A phase may only start after the previous required gate is complete. A phase file can be refined from the real repository state before implementation, but its scope must not be silently widened.
