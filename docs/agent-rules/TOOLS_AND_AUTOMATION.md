# Tools & Linux Automation Rules

Applies to controlled tools and Phase 6 Lexi integration.

## Model/action separation

A language model may propose structured intent. The runtime decides whether a declared tool is available and validates typed arguments before invocation.

Never interpret free-form assistant text or code fences as executable commands.

## Tool requirements

Every tool needs:

- stable ID/name;
- typed input schema;
- bounded typed/normalized result;
- timeout;
- cancellation behavior;
- explicit error mapping;
- security classification/policy;
- tests.

## Linux automation

Prefer narrow operations such as an allowlisted "open application" capability over a generic unrestricted shell tool.

If shell execution is ever introduced, it requires a dedicated ADR and threat model. It is not an implicit part of Lexi integration.

## Observability

Record enough metadata to understand which tool ran and whether it succeeded, without logging secrets or unnecessarily sensitive payloads.
