# Visual Interface Rules

Load for browser, React, TypeScript, Vite, React Flow, or visual interface work.

1. The frontend MUST use `/api/v1` and `/ws/events`; do not call runtime, provider, or persistence internals.
2. The backend is the authorization and run-state authority. UI permissions only guide affordances and cannot bypass a server denial.
3. Do not store, render, log, or expose provider credentials, authorization headers, or secrets in client code, build output, URLs, or browser storage.
4. Validate backend responses and WebSocket events at the client boundary. Treat event payloads as text/JSON, never HTML.
5. Use normalized backend events and preserve a bounded client event history.
6. Do not invent lifecycle, approval, graph, model, or provider capabilities that the backend does not expose.
7. Keep graph semantics typed and persist them through the supported API, never through browser-local canonical state.
8. Keep desktop, tablet, and mobile workflows functional, with semantic controls and visible focus states.
