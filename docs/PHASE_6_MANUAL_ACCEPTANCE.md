# Phase 6 Manual Acceptance

Status: PASS. Owner confirmed the required manual acceptance on 2026-08-15.
Automated checks and a separate local-model smoke also passed.

## Setup

1. Start the backend with a permitted local identity and a configured local
   model route.
2. Start the frontend with `pnpm dev`.
3. Open the Vite URL and navigate to `/lexi`.

## Required checks

Owner-confirmed PASS:

- Bootstrap Lexi and confirm it creates a normal AgentGraph agent.
- Start a text run and confirm provider/model, lifecycle events, output, and
  normal run history are visible.
- Create an agent-scoped memory, ask a follow-up that retrieves it, inspect the
  run-memory record, restart the backend, then delete it and confirm it is no
  longer retrieved.
- With `AGENTGRAPH_TOOLS_ENABLED=true` and one safe user-owned application
  alias configured, request the controlled action. Confirm it waits for an
  approval, approve it, and observe the completed tool event/history.
- Repeat the action and reject approval. Confirm no application launches and
  Lexi reports the result truthfully.
- Cancel an active Lexi run, including an approval wait when practical. Confirm
  server-reported `cancelled` state and no later tool execution.
- Confirm Dashboard, Projects, Agents, Runs, Approvals, Providers, Vision,
  Events, and Settings still load.

## Live Model Smoke

Status: PASS. Isolated SQLite smoke used Ollama
`qwen3-4b-nothink:latest`; a normal Lexi run succeeded with `Hello!` in
15,920 ms. A missing local model is not an automated-test failure.
