# ADR-0006 - NAS Primary Core and Fenced Failover
Status: Accepted target architecture
Date: 2026-08-16

## Context

The future system needs persistent availability without making every worker an authority or promising unsafe recovery after a Core outage.

## Decision

The NAS is the intended Primary Core for 24/7 operation. Explicitly eligible nodes may host a Backup Core only through a fenced failover design that restores committed state and prevents split-brain and duplicate execution.

## Consequences

The future Core/worker protocol, leader/fencing method, storage replication, and promotion tests must be designed before implementation. Current local single-process operation remains unchanged.

## Alternatives considered

Always-active multi-Core execution was rejected because it would add distributed coordination before single-writer recovery and authority boundaries are proven.
