# AgentGraph OS — Tools & Automation Design

Status: controlled Tool Runtime MVP implemented in Phase 6. Broad automation is
still out of scope.

## Principle

A model response is **not an operating-system command**. Tools are explicit typed capabilities invoked by runtime policy.

```text
Model / graph proposes structured intent
              ↓
Tool policy + validation
              ↓
Declared tool adapter
              ↓
Bounded result / normalized error
```

## Tool contract direction

Every tool requires:

- stable identifier;
- typed input;
- bounded/normalized output;
- permission/policy classification;
- timeout;
- cancellation;
- error mapping;
- tests;
- observable invocation metadata that avoids secrets.

## Linux automation

Prefer narrow capabilities (for example, open an allowlisted application) over a generic unrestricted terminal executor.

A general shell tool is **not** approved by this design. Adding one requires a separate ADR/threat model and explicit owner decision.

## Current implementation

- `ToolService` registers only `system.current_time` and
  `desktop.open_application`.
- Tools are disabled by default. `desktop.open_application` accepts only an
  application alias resolved by the user-configured JSON argument-vector
  allowlist; model text never supplies executables, flags, environment, or a
  working directory.
- The desktop action always requires a process-local `ApprovalService` decision.
  Waiting is timeout and cancellation aware; a cancelled or expired request does
  not launch an application.
- The implementation uses `asyncio.create_subprocess_exec` with fixed
  allowlisted arguments and no shell.
- Normalized invocation metadata and runtime events are persisted/available by
  run. Output is bounded and no raw subprocess streams are stored.

## Future adapters

Filesystem, GitHub, browser, Telegram, MCP, and other integrations may become adapters behind this boundary in later work. Their appearance in a roadmap or README does not make them implicitly available to models.
