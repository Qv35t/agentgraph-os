# ADR-0002 — Local-First Is the Default Operating Mode

Status: Accepted  
Date: 2026-08-11

## Context

The project is intended to combine local models, agent workflows, memory, and Linux tooling without making cloud services the default dependency.

## Decision

Core startup and basic workflows must work with local resources. Cloud/provider features are optional and explicitly configured.

## Consequences

- Loopback network defaults.
- Local persistence and local model path first.
- Automated tests cannot depend on cloud credentials.
- Cloud fallback must be explicit rather than silent.
