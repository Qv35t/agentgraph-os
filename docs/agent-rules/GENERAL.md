# General Agent Rules

Load for any non-trivial implementation task.

1. Inspect before editing. Do not infer an empty repository from a short phase brief.
2. Preserve user changes and unrelated worktree modifications.
3. Prefer adapting an existing module over adding a parallel framework/layer.
4. Keep implementation inside the active phase scope.
5. Do not create mocks where the phase explicitly requires real internal behavior.
6. External integrations may be mocked for automated tests, but live checks remain separate and truthful.
7. Use project-owned contracts at boundaries.
8. Normalize errors at boundary layers; do not leak vendor exceptions through the entire stack.
9. Avoid speculative abstractions with no current caller/test.
10. Update status/docs only after observed results justify the update.
11. Never claim commands were run unless they were actually run.
12. Do not commit/push unless explicitly requested by the user.
13. Treat `PROJECT_STATUS.md` and current architecture sections as implementation
    truth. Future vision, roadmap, and target ADRs describe approved intent, not
    existing capability.
14. A recommendation, plan, model output, or inferred status is never user
    authorization for a new user-impacting action or scope expansion.
