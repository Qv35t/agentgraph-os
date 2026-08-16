# Lexi: Current MVP and Target Orchestrator

Status: Phase 6 is complete. Workflow, services, browser workspace, local
Ollama smoke, and owner manual acceptance passed on 2026-08-15.

```text
Versioned API
    |
AgentManager -> WorkflowRuntime (allowlisted graph runtime)
    |                 |
    |                 +-> model-v1 -> ModelRouter
    |                 |
    |                 +-> lexi-v1 LangGraph
    |                        |- MemoryService (SQLite, project + agent scoped)
    |                        |- ModelRouter
    |                        `- ToolService -> ApprovalService -> controlled adapter
    |
RuntimeEventBus <- normalized lifecycle, approval, and tool events
    ^
    |
Browser `/lexi` uses normal versioned API commands and event observation
```

Lexi is installed by `LexiTemplateService` as a normal agent whose persisted
graph metadata declares `runtime: "lexi-v1"`. All conversation execution uses
the normal `AgentManager` run lifecycle; there is no Lexi chat endpoint.

The Lexi LangGraph loads scoped memory, asks the `ModelRouter` for a strict JSON
response-or-tool decision, validates any tool request, then performs at most the
configured number of tool steps before producing a final response. Malformed
model text is treated as a non-actionable response.

Memory and tool data stay local. Memory is lexical SQLite retrieval with bounded
context, not vector search. Tools are disabled by default; no shell capability
exists. The only desktop capability accepts a configured alias and requires a
process-local approval. Restart recovery fails active runs, so waiting approvals
and in-flight tools never resume automatically. The browser workspace can
bootstrap Lexi, start and cancel normal runs, manage scoped memories, inspect
run memory/tool activity, and link to the shared approvals workflow.

## Approved Target: Main Agent

The future Lexi is the Main Agent: a persistent personal work partner that
coordinates specialized agents, models, devices, applications, and long-running
work. It may recommend proactively after significant events, but recommendation
does not authorize execution. It must not invent a new user goal, expand scope,
or continue an unapproved development phase.

For a scoped goal, Lexi may show a brief plan (goal, stages, expected result,
approval points) or detailed plan (interpretation, subtasks, agents, devices,
risks, permissions, checkpoints, acceptance, blockers). Its target hierarchy is
`Goal -> Project -> Phase -> Task -> Run`. Derived project state must retain
source provenance rather than appear as a confirmed fact without evidence.

The future orchestrator may construct bounded temporary graphs and propose
saving a successful graph as a reusable workflow. It must observe graph nodes
with state, assigned agent/device/model, timing, progress, logs, errors, retry,
approval state, and outputs. Dynamic planning and reusable workflows are not
implemented by the current static `team-v1` DAG runtime.

## Target Long-Running Work

Pause/resume requires persisted goal, plan, graph, completed/pending nodes,
agent state, decisions, approvals, checkpoints, errors, attempted solutions,
changed files, and test results. If an agent is stuck, it may use bounded
alternative approaches or permitted research, then stops and reports a clear
blocker when its retry budget is exhausted. No infinite autonomous retry loop is
permitted.

The target daily brief may aggregate active goals, projects, tasks, run state,
calendar, device/system state, updates, notifications, OpenCode status, and
other registered sources. Each source remains optional, attributable, and
policy-governed. See [`../FUTURE_VISION.md`](../FUTURE_VISION.md),
[`OPENCODE_INTEGRATION.md`](OPENCODE_INTEGRATION.md), and
[`RESILIENCE_AND_RECOVERY.md`](RESILIENCE_AND_RECOVERY.md).
