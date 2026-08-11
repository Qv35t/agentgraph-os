# Frontend Rules

Applies to React/TypeScript/React Flow work from Phase 4 onward.

## Boundary

The frontend visualizes and edits user-facing graph/agent configuration and calls backend APIs. It must not reimplement provider routing, run-state authority, persistence rules, or secret handling.

## TypeScript

- Prefer strict TypeScript.
- Keep API client types explicit and aligned with backend contracts.
- Validate uncertain external/runtime data at boundaries where needed.
- Avoid `any` as a shortcut for core graph/runtime state.

## React Flow

- Keep node data schemas typed.
- Separate domain graph representation from transient visual state when appropriate.
- Persist graph semantics, not incidental pixel/UI state unless required.
- Handle missing nodes/edges and stale backend objects without crashing the whole workspace.

## UX baseline

- Visible loading/error/empty states.
- Keyboard/focus accessibility for core actions.
- No hidden destructive actions.
- Stop/cancel state must reflect backend truth rather than optimistic fiction.
- Provider/model lists come from backend discovery when available; do not hardcode a forever-current GPT model list.
