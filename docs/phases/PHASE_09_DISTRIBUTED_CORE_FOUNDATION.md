# Phase 9 - Distributed Core Foundation

Status: DONE. Automated verification, same-machine backend transport acceptance,
and owner-confirmed browser Nodes acceptance passed on 2026-08-17. Physical
two-machine validation remains recommended real-hardware follow-up, not a
completion blocker.

## Implemented Scope

- A single authoritative Core persists registered Worker nodes in SQLite.
- Workers use stable local opaque node IDs and initiate the internal WebSocket
  connection to `/ws/internal/workers`.
- Protocol v1 is typed and bounded. Only `system.probe` can execute remotely.
- Enrollment requires an HMAC proof derived from an explicit secret. The secret
  itself is not sent, logged, evented, or stored; only the derived hash is stored.
- Core exposes authorized node list/read, enable/disable, and probe APIs.

## Boundaries

Workers own local identity, safe capability discovery, and temporary probe
execution. Core owns node registration, node enablement, task dispatch, events,
authorization, and all existing AgentGraph state. Workers do not run arbitrary
shell commands or AgentGraph graph/runtime work.

The implementation does not add Core failover, distributed database state,
durable distributed task recovery, scheduling, or remote access for browser
clients.

## Gate

Required automated checks include backend lint/type/tests/migrations, frontend
checks/build/tests, link validation, and diff validation. See
[`../PHASE_09_MANUAL_ACCEPTANCE.md`](../PHASE_09_MANUAL_ACCEPTANCE.md) for the
recorded same-machine acceptance and optional two-machine procedure.
