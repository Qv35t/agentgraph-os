# AgentGraph OS — Tools & Automation Design

Status: controlled-capability design direction; broad tool runtime is not part of Phase 2 or Phase 3.

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

## Future adapters

Filesystem, GitHub, browser, Telegram, MCP, and other integrations may become adapters behind this boundary in later work. Their appearance in a roadmap or README does not make them implicitly available to models.
