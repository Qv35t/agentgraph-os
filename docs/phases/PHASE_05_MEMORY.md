# Phase 5 — Memory

## Mission

Add explicit local-first memory and retrieval to AgentGraph OS without coupling the runtime to a single storage vendor.

## Required scope direction

- project-owned memory contracts;
- agent/workspace namespaces;
- write/retrieve/delete lifecycle;
- local vector store integration (Qdrant direction);
- optional Mem0 integration only behind project-owned boundary;
- deterministic retrieval injection into runtime state;
- observability of what memory was used;
- retention/deletion behavior;
- unavailable/corrupt store handling;
- automated tests without cloud dependency;
- minimal UI exposure required to understand/control memory.

## Security/privacy

Memory content remains local by default. Do not silently sync it to cloud providers. Deletion must be real and testable at the abstraction level.

## Gate

An agent can write scoped local memory, retrieve relevant scoped entries on a later run, use them through the explicit runtime contract, and delete them without cross-agent leakage.

Refine exact storage/schema choices from the implemented Phase 4/runtime state before coding.
