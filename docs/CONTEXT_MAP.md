# AgentGraph OS — Context Map for OpenCode

This file explains what to load, not what to load all at once.

| Task | Minimum extra context |
|---|---|
| Phase 2 backend implementation | `PHASE_02...`, `BACKEND.md`, `TESTING.md` |
| Phase 3 provider/model work | `PHASE_03...`, `MODELS.md`, `SECURITY.md`, `TESTING.md` |
| Phase 4 UI | `PHASE_04...`, `FRONTEND.md`, relevant backend API contracts |
| Phase 5 memory | `PHASE_05...`, `MEMORY.md`, `SECURITY.md` |
| Phase 6 Lexi/tools | `PHASE_06...`, `TOOLS_AND_AUTOMATION.md`, `SECURITY.md` |
| Architecture refactor | `ARCHITECTURE.md`, relevant ADRs, active phase |
| Test-only change | `TESTING.md`, relevant domain rule |
| Documentation-only status update | `PROJECT_STATUS.md`, active phase gate |

Use `.opencode/commands/phase-N.md` to inject the proper phase files into a new OpenCode task without permanently increasing every session's context.
