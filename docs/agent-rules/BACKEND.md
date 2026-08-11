# Backend Rules

Applies to FastAPI, domain, persistence, runtime, repositories, and services.

## Structure

- Keep HTTP routers thin.
- Business/runtime orchestration belongs in services such as `AgentManager`.
- Persistence access belongs in repositories/data layer.
- Runtime execution handles are process-local; durable state is persistent.
- Pydantic/API DTOs, domain concepts, and SQLAlchemy models may be distinct when that improves boundaries.

## Python

- Python 3.12+ direction.
- Type hints for new public functions/classes.
- Pydantic v2 for external input validation.
- SQLAlchemy 2 style once persistence is implemented.
- Async I/O must not be blocked by `time.sleep()` or sync HTTP calls in async request paths.

## Lifecycle

- One canonical app entrypoint/application factory.
- Startup prepares DB/runtime/services and recovery.
- Shutdown cancels active runs with bounded cleanup and closes resources.
- Backend health is not the same as provider health.

## API

- Predictable status codes and error shape.
- UUIDs for durable agent/run identities unless an ADR changes this.
- Do not expose stack traces or raw provider exception bodies.
- Do not add versioned `/v1` routes mid-phase unless the established API already requires it.

## Persistence

- Migrations are the durable schema lifecycle.
- Tests use isolated temporary DBs.
- Do not pickle arbitrary Python objects into persistence.
- Graph definitions stored persistently must remain JSON-compatible/validated.
