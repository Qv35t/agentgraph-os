# Phase 4 Manual Acceptance

## Local startup

1. Run `uv run --directory backend alembic upgrade head`.
2. Start the backend with explicit local development policy, for example:
   `AGENTGRAPH_REMOTE_CONTROL_ENABLED=true AGENTGRAPH_REMOTE_CONTROL_POLICIES='{"local-user":["read","execute","control","approve"]}' uv run --directory backend uvicorn agentgraph.app:app --host 127.0.0.1 --port 8000`.
3. Run `pnpm dev` and open the Vite URL.

## Browser checks

- Dashboard reports API state, providers, agents, approvals, and connection state.
- Create an agent, select a discovered model route, arrange the graph, save it,
  refresh the agent detail page, and verify the graph persists.
- Start a run, open its workspace, observe its events/output, and stop an active
  run where timing permits.
- Create an approval through the API, verify it appears, then approve or reject
  it and verify the list updates without a page reload.
- Verify `/projects`, `/agents`, `/providers`, `/events`, and `/settings` after
  direct navigation and refresh.
- Verify a server with remote control disabled shows a clear denial/restricted
  state, and disconnecting the event stream does not end the backend run.
- Check desktop, tablet, and mobile-width layouts; navigation and approval/run
  actions must remain usable.

Do not place the example policy in committed environment files. It is a
non-secret, local development-only authorization configuration.
