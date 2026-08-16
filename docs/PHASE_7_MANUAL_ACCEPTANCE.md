# Phase 7 Manual Acceptance

Status: **PASS — OWNER CONFIRMED**. Automated verification and isolated local
Ollama parallel/sequential team smokes passed on 2026-08-16.

## Live Smoke

- Parallel: one `team-v1` parent and two `model-v1` workers using
  `ollama://qwen3:0.6B` all succeeded; persisted run-tree inspection returned
  both children.
- Sequential: the reviewer began after the researcher finished and the parent
  synthesis succeeded using the same local model.

1. Start the local backend with remote control enabled for a local identity.
2. Create two normal workers and a `team-v1` graph with two `agent-ref` nodes.
3. Save, reload, and confirm positions, selected workers, instructions, and
   edges persist.
4. Start the team, observe child runs and the hierarchy, then inspect child
   output/model metadata.
5. Stop a team while multiple workers are active and confirm no child remains
   running.
6. Repeat at mobile/tablet width and confirm hierarchy/status/stop controls are
   usable.
