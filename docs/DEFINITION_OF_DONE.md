# AgentGraph OS — Definition of Done

A feature/slice is done only when all applicable items are true.

## Implementation

- behavior is implemented, not only scaffolded;
- no competing duplicate architecture was introduced;
- error paths are handled intentionally;
- public contracts are typed/validated;
- local-first startup remains viable unless the active phase explicitly says otherwise.

## Verification

- focused tests pass;
- required broader tests/lint/type checks pass;
- migrations are exercised when schema changed;
- required manual smoke test is actually run;
- skipped environmental checks are explicitly marked `NOT RUN`.

## Security

- no secret material added;
- no implicit model-to-tool execution path;
- network exposure did not expand unintentionally;
- logs/errors do not leak credentials.

## Documentation

Update only applicable documents:

- architecture when boundaries changed;
- ADR when a durable architectural decision was made;
- phase status when a gate changed;
- setup/README when commands/config changed.

## Completion report

OpenCode reports exact files changed, exact verification commands/results, remaining limitations, and whether the phase gate is satisfied.
