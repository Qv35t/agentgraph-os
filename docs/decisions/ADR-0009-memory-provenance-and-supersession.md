# ADR-0009 - Memory Provenance and Supersession
Status: Accepted target architecture
Date: 2026-08-16

## Context

Long-lived personal and project memory can become ambiguous, stale, or contradictory and must not masquerade as authority.

## Decision

Significant target memory records require provenance: source and reference, creation and update time, type, confidence, related project/entities, and active, superseded, or revoked state. Supersession preserves audit history.

## Consequences

Future memory retrieval and UI must expose provenance and allow user correction, forgetting, archival, and supersession. Current SQLite Memory MVP remains scoped and deletable but does not implement this target entity graph.

## Alternatives considered

Replacing records in place was rejected because it loses the basis for planning and audit decisions.
