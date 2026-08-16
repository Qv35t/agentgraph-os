# Lexi Integration Map

Status: verified during Phase 6 repository preflight on 2026-08-15.

No separate legacy Lexi project or source tree was present in this workspace at
preflight. The capability decisions below therefore describe AgentGraph OS
implementation, not an import of unverified legacy code.

| Capability | Current implementation | Interface | Input / output | Cancellation | Security | Phase 6 decision |
|---|---|---|---|---|---|---|
| Text assistant | `lexi-v1` LangGraph workflow | Normal AgentManager run API | Text request / model response | Agent run cancellation | Model output is validated JSON data | Implemented |
| Local model usage | ModelRouter with `auto://default` | Project-owned model contract | Model messages / normalized response | Router/run cancellation | No provider-native API leaks | Implemented |
| Memory | SQLite MemoryService | Versioned memory API | Explicit records / bounded lexical matches | N/A | Project and agent scope | Implemented |
| Desktop action | Controlled ToolService | Registered tool contract | Application alias / normalized result | Run/tool cancellation | Allowlist, approval, no shell | Implemented |
| ASR, VAD, TTS, hotword | No verified local implementation | N/A | N/A | N/A | Not assessed | Deferred |
| Remote messaging | No Lexi-specific integration | N/A | N/A | N/A | Not assessed | Deferred |

The browser workspace is `/lexi`. It uses normal AgentGraph run, approval,
