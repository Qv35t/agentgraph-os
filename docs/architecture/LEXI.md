# Lexi MVP

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
