# Phase 9 Manual Acceptance

Status: PASS. Phase 9 same-machine acceptance is complete.

## Observed 2026-08-17

The same-machine backend transport lifecycle was observed against a migrated,
isolated SQLite database with separate loopback Core and Worker processes:

- the Worker enrolled with a stable opaque node ID and reported the bounded
  platform, CPU, and RAM snapshot;
- `system.probe` completed successfully;
- stopping the Worker transitioned the node to `offline` after the heartbeat
  timeout, and restarting it reused the same node record without a duplicate;
- disabling the Worker rejected probe with `409 NODE_DISABLED`; enabling and
  reconnecting it allowed probe again;
- restarting the Core retained the registered node, after which the Worker
  reconnected under the same identity and completed a probe.

Interactive browser acceptance was owner-confirmed on 2026-08-17:

- Nodes loads, displays the enrolled Worker and its online/offline/disabled
  state, and shows its bounded capabilities;
- the Worker returns offline after the heartbeat timeout and reconnects under
  the same persistent identity without a duplicate after restart;
- disabling and re-enabling the Worker is reflected after browser refresh, and
  re-enabled Workers reconnect successfully;
- no blocking browser console or runtime errors were observed.

## Same-Machine Procedure

1. From the repository root (the directory containing `backend/` and
   `frontend/`), start the Core with a migrated SQLite database, a private
   listener, remote control policies for the browser identity, and a non-empty
   `AGENTGRAPH_WORKER_ENROLLMENT_SECRET`.
2. Start a separate Worker process with the same enrollment secret,
   `AGENTGRAPH_NODE_ROLE=worker`, `AGENTGRAPH_CORE_URL` pointing to the Core,
   `AGENTGRAPH_WORKER_ENABLED=true`, and an isolated `AGENTGRAPH_NODE_ID_PATH`:
   `python -m agentgraph.worker`.
3. Start the frontend and open **Nodes**. Verify the worker is online, its safe
   platform/CPU/RAM snapshot is visible, and no enrollment secret is displayed.
4. Select **Probe**. Verify a successful `system.probe` result returns from the
   same node ID.
5. Stop the Worker. After the configured heartbeat timeout, refresh Nodes and
   verify it is offline.
6. Restart the Worker using the same ID path. Verify the same node becomes
   online and no duplicate node exists.
7. Disable the worker from Nodes. Verify probe is rejected. Enable it, restart
   or reconnect it, and verify probe succeeds again.

## Two-Machine Procedure

Repeat the same lifecycle over a trusted private network or a TLS-terminating
private reverse proxy. This v1 transport does not provide TLS itself: use
`wss://` when the Core is not isolated to a trusted local network. Do not expose
the internal worker endpoint to the public internet.

Physical two-machine validation is recommended real-hardware follow-up, not a
Phase 9 completion blocker.

## Expected Limits

Only `system.probe` is executable. No arbitrary shell, filesystem browsing,
model routing, agent graph execution, failover, or task recovery is part of
this phase.
