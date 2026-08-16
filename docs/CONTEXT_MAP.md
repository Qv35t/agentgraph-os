# AgentGraph OS — Context Map for OpenCode

This file explains what to load, not what to load all at once.

| Task | Minimum extra context |
|---|---|
| Phase 2 backend implementation | `PHASE_02...`, `BACKEND.md`, `TESTING.md` |
| Phase 3 provider/model work | `PHASE_03...`, `MODELS.md`, `SECURITY.md`, `TESTING.md` |
| Phase 4 UI | `PHASE_04...`, `FRONTEND.md`, relevant backend API contracts |
| Phase 5 vision | `PHASE_05...`, `VISION.md`, `SECURITY.md` |
| Phase 6 Lexi/tools/memory | `PHASE_06...`, `TOOLS_AND_AUTOMATION.md`, `MEMORY.md`, `SECURITY.md` |
| Phase 7 multi-agent orchestration | `PHASE_07...`, `MULTI_AGENT_ORCHESTRATION.md`, `BACKEND.md`, `REMOTE_INTERFACES.md` |
| Phase 8 documentation baseline | `PHASE_08...`, `FUTURE_VISION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `PROJECT_STATUS.md`, relevant target record |
| Architecture refactor | `ARCHITECTURE.md`, relevant ADRs, active phase |
| Test-only change | `TESTING.md`, relevant domain rule |
| Documentation-only status update | `PROJECT_STATUS.md`, active phase gate |

Use `.opencode/commands/phase-N.md` to inject the proper phase files into a new OpenCode task without permanently increasing every session's context.
