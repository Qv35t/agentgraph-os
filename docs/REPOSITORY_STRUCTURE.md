# AgentGraph OS — Repository Structure

The Foundation phase established these top-level responsibility areas. Actual subpaths may evolve through ADR-backed changes.

```text
agentgraph-os/
├── AGENTS.md
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── backend/
├── frontend/
├── agents/
├── tools/
├── memory/
├── models/
├── plugins/
├── configs/
├── docs/
│   ├── agent-rules/
│   ├── decisions/
│   └── phases/
├── tests/
├── scripts/
├── docker/
└── .opencode/
    ├── agents/
    └── commands/
```

## Ownership

### `backend/`
Backend application, API, domain contracts, services, runtime, persistence, provider adapters, and backend-specific tests.

### `frontend/`
React/TypeScript/React Flow client. No direct provider credentials and no duplication of backend orchestration rules.

### `agents/`
Reusable agent definitions or templates only if they are not implementation-specific backend modules.

### `tools/`
Future controlled tool schemas/adapters. Never use this directory as a generic place for arbitrary shell snippets.

### `memory/`
Memory integration configuration/support where not naturally owned by backend packages.

### `models/`
Metadata/configuration/model references. Model binaries and caches are ignored and must not be committed.

### `plugins/`
Reserved extension surface. Plugin runtime is post-MVP unless a phase explicitly changes this.

### `configs/`
Non-secret committed configuration examples/defaults.

### `docs/`
Project truth: architecture, roadmap, status, security, ADRs, and phase specs.

### `.opencode/`
OpenCode-specific local project commands/subagent definitions committed for repeatable development workflow.
