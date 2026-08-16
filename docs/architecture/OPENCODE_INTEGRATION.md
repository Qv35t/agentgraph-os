# OpenCode Integration Target

Status: approved target architecture. The current OpenCode bridge is model transport only; it is not a Coder Agent or session orchestrator.

## Role

The future OpenCode Agent is a specialized Coder Agent coordinated by Lexi for an approved development goal or phase. It receives bounded project context, reports session state, diffs, test results, blockers, and artifacts through project-owned contracts. Lexi may answer from known project context and escalates user decisions that change scope, policy, or phase.

```text
Lexi -> approved development task -> OpenCode Agent -> repository
     <- progress, diff, tests, review, blocker <-
```

OpenCode retains ownership of its provider authentication as specified by ADR-0004. A coding-agent integration must not read, copy, or expose OpenCode credentials. It must not turn arbitrary model text into filesystem or shell authority.

## Concurrent Sessions

Multiple future Coder Agents require explicit repository ownership boundaries, conflict detection, isolation/worktree strategy, dependency ordering, merge coordination, cancellation, and per-session resource limits. Concurrent sessions are not authorized merely because a coordinator can observe them. See [`LEXI.md`](LEXI.md), [`SECURITY_AND_TRUST.md`](SECURITY_AND_TRUST.md), and ADR-0008.
