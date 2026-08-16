# ADR-0010 - Local Only Is an Enforced Boundary
Status: Accepted target architecture
Date: 2026-08-16

## Context

A local-only preference is insufficient if a router can send prompts, files, images, embeddings, or context to an external AI provider.

## Decision

The future `Local Only` profile is an enforced provider-boundary policy. It forbids cloud inference and task-data egress to external AI providers. Balanced, Best Quality, and Cheapest remain explicit policy profiles, not silent fallback.

## Consequences

Future routing needs policy evaluation, observable route decisions, and tests for denied egress. The current local-first router remains unchanged and does not claim these profiles are implemented.

## Alternatives considered

An advisory local preference was rejected because it cannot provide a privacy boundary.
