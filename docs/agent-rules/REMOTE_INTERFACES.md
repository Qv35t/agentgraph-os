# Remote Interface Rules

Load for REST/WebSocket remote control, Web UI, TUI, messaging, or client API work.

1. Interfaces are clients of the shared application/API boundary, never runtime owners.
2. Runtime, LangGraph, domain, and provider modules must not import UI or messaging SDKs.
3. Remote commands must use `RemoteCommandService` or the corresponding application service and must pass server-side authorization.
4. The backend remains the authoritative state; clients may cache but cannot define run or approval state.
5. A disconnected client must not cancel, pause, or otherwise determine runtime execution.
6. External event payloads and errors must be JSON-safe and must not expose credentials, tokens, headers, environment values, raw exceptions, or stack traces.
7. Remote exposure remains disabled by default and the backend binds to loopback unless an explicit security-reviewed change approves otherwise.
8. Extend the normalized event, command, approval, authorization, and API contracts instead of creating per-client copies.
