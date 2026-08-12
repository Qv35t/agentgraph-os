import asyncio
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from agentgraph.domain.entities import (
    ACTIVE_RUN_STATUSES,
    TERMINAL_RUN_STATUSES,
    Agent,
    AgentRun,
    AgentStatus,
    RunStatus,
)
from agentgraph.domain.remote import RuntimeEvent, RuntimeEventType
from agentgraph.models.contracts import ModelResponse, ModelRouterError
from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import AgentRecord, AgentRunRecord
from agentgraph.repositories.agents import AgentRepository
from agentgraph.repositories.runs import RunRepository
from agentgraph.runtime.events import RuntimeEventBus
from agentgraph.runtime.registry import RunRegistry
from agentgraph.services.errors import AgentNotFoundError, LifecycleConflictError, RunNotFoundError


class AgentRuntime(Protocol):
    async def invoke(self, *, agent_id: UUID, run_id: UUID, input_text: str, model_ref: str) -> ModelResponse: ...


class AgentManager:
    """Coordinates durable lifecycle state with process-local run tasks."""

    def __init__(
        self,
        session_factory: SessionFactory,
        runtime: AgentRuntime,
        registry: RunRegistry,
        runtime_delay_seconds: float,
        cancellation_timeout_seconds: float,
        events: RuntimeEventBus | None = None,
        project_id: str = "project_local",
    ) -> None:
        self._session_factory = session_factory
        self._runtime = runtime
        self._registry = registry
        self._runtime_delay_seconds = runtime_delay_seconds
        self._cancellation_timeout_seconds = cancellation_timeout_seconds
        self._agent_repository = AgentRepository()
        self._run_repository = RunRepository()
        self._agent_locks: dict[UUID, asyncio.Lock] = {}
        self._events = events
        self._project_id = project_id

    async def create_agent(
        self,
        *,
        name: str,
        description: str | None,
        model_ref: str,
        graph_definition: dict[str, object],
    ) -> Agent:
        async with self._session_factory() as session:
            record = await self._agent_repository.create(
                session,
                name=name,
                description=description,
                model_ref=model_ref,
                graph_definition=graph_definition,
            )
            await session.commit()
            await session.refresh(record)
            return _agent_from_record(record)

    async def list_agents(self) -> list[Agent]:
        async with self._session_factory() as session:
            records = await self._agent_repository.list(session)
            return [_agent_from_record(record) for record in records]

    async def get_agent(self, agent_id: UUID) -> Agent:
        async with self._session_factory() as session:
            record = await self._agent_repository.get(session, agent_id)
            if record is None:
                raise AgentNotFoundError
            return _agent_from_record(record)

    async def update_agent_graph(self, agent_id: UUID, graph_definition: dict[str, object]) -> Agent:
        async with self._lock_for(agent_id):
            async with self._session_factory() as session:
                record = await self._agent_repository.get(session, agent_id)
                if record is None:
                    raise AgentNotFoundError
                await self._agent_repository.update_graph(session, record, graph_definition)
                await session.commit()
                await session.refresh(record)
                return _agent_from_record(record)

    async def delete_agent(self, agent_id: UUID) -> None:
        async with self._lock_for(agent_id):
            async with self._session_factory() as session:
                record = await self._agent_repository.get(session, agent_id)
                if record is None:
                    raise AgentNotFoundError
                if await self._run_repository.has_active_for_agent(session, agent_id):
                    raise LifecycleConflictError("An active run prevents deleting this agent")
                await self._agent_repository.delete(session, record)
                await session.commit()

    async def start_run(self, *, agent_id: UUID, input_text: str) -> AgentRun:
        async with self._lock_for(agent_id):
            async with self._session_factory() as session:
                # SQLite has no row-level locks. This serializes the durable active-run check.
                await session.execute(text("BEGIN IMMEDIATE"))
                agent = await self._agent_repository.get(session, agent_id)
                if agent is None:
                    raise AgentNotFoundError
                if await self._run_repository.has_active_for_agent(session, agent_id):
                    raise LifecycleConflictError("This agent already has an active run")
                try:
                    run = await self._run_repository.create(session, agent_id=agent_id, input_text=input_text)
                except IntegrityError as error:
                    await session.rollback()
                    raise LifecycleConflictError("This agent already has an active run") from error
                agent.status = AgentStatus.RUNNING
                await session.commit()
                await session.refresh(run)

            run_id = UUID(run.id)
            task = asyncio.create_task(self._execute_run(run_id), name=f"agent-run-{run_id}")
            self._registry.register(run_id, task)
            await self._publish(
                RuntimeEventType.RUN_CREATED, run_id=run.id, agent_id=agent.id, payload={"status": run.status}
            )
            return _run_from_record(run)

    async def get_run(self, run_id: UUID) -> AgentRun:
        async with self._session_factory() as session:
            record = await self._run_repository.get(session, run_id)
            if record is None:
                raise RunNotFoundError
            return _run_from_record(record)

    async def list_runs(self, agent_id: UUID) -> list[AgentRun]:
        await self.get_agent(agent_id)
        async with self._session_factory() as session:
            records = await self._run_repository.list_for_agent(session, agent_id)
            return [_run_from_record(record) for record in records]

    async def stop_run(self, run_id: UUID) -> AgentRun:
        run = await self.get_run(run_id)
        if run.status in TERMINAL_RUN_STATUSES:
            raise LifecycleConflictError("This run is already terminal")

        task = self._registry.get(run_id)
        if task is None:
            await self._finish_failed(run_id, "Live execution handle unavailable")
            raise LifecycleConflictError("This run has no live execution handle")

        if not await self._registry.cancel(run_id, self._cancellation_timeout_seconds):
            raise LifecycleConflictError("Run cancellation timed out")
        await self._finish_cancelled(run_id)
        return await self.get_run(run_id)

    async def recover_stale_runs(self) -> None:
        async with self._session_factory() as session:
            stale_runs = await self._run_repository.list_stale(session)
            if not stale_runs:
                return
            finished_at = _utc_now()
            for run in stale_runs:
                run.status = RunStatus.FAILED
                run.error = "Run interrupted by application restart"
                run.finished_at = finished_at
                agent = await self._agent_repository.get(session, UUID(run.agent_id))
                if agent is not None:
                    agent.status = AgentStatus.ERROR
            await session.commit()

    async def shutdown(self) -> bool:
        completed, timed_out = await self._registry.cancel_all(self._cancellation_timeout_seconds)
        for run_id in completed:
            await self._finish_cancelled(run_id)
        for run_id in timed_out:
            await self._finish_failed(run_id, "Run cancellation timed out during shutdown")
        return not timed_out

    async def _execute_run(self, run_id: UUID) -> None:
        try:
            run = await self._mark_running(run_id)
            if self._runtime_delay_seconds:
                await asyncio.sleep(self._runtime_delay_seconds)
            agent = await self.get_agent(run.agent_id)
            response = await self._runtime.invoke(
                agent_id=run.agent_id,
                run_id=run.id,
                input_text=run.input_text,
                model_ref=agent.model_ref,
            )
        except asyncio.CancelledError:
            await self._finish_cancelled(run_id)
            raise
        except ModelRouterError as error:
            await self._finish_failed(run_id, f"{error.code}: {error}")
        except Exception as error:
            await self._finish_failed(run_id, f"Run execution failed: {type(error).__name__}")
        else:
            await self._finish_succeeded(run_id, response)
        finally:
            self._registry.remove(run_id)

    async def _mark_running(self, run_id: UUID) -> AgentRun:
        async with self._session_factory() as session:
            record = await self._run_repository.get(session, run_id)
            if record is None:
                raise RunNotFoundError
            if record.status not in ACTIVE_RUN_STATUSES:
                raise LifecycleConflictError("Run is no longer active")
            record.status = RunStatus.RUNNING
            record.started_at = _utc_now()
            await session.commit()
            await self._publish(
                RuntimeEventType.RUN_STARTED,
                run_id=record.id,
                agent_id=record.agent_id,
                payload={"status": record.status},
            )
            return _run_from_record(record)

    async def _finish_succeeded(self, run_id: UUID, response: ModelResponse) -> None:
        async with self._session_factory() as session:
            record = await self._run_repository.get(session, run_id)
            if record is None or record.status in TERMINAL_RUN_STATUSES:
                return
            record.status = RunStatus.SUCCEEDED
            record.output_text = response.content
            record.provider_id = response.provider_id
            record.model_id = response.model_id
            record.finish_reason = response.finish_reason
            record.input_tokens = response.usage.input_tokens
            record.output_tokens = response.usage.output_tokens
            record.total_tokens = response.usage.total_tokens
            record.latency_ms = response.latency_ms
            record.finished_at = _utc_now()
            agent = await self._agent_repository.get(session, UUID(record.agent_id))
            if agent is not None:
                agent.status = AgentStatus.IDLE
            await session.commit()
            await self._publish(
                RuntimeEventType.RUN_COMPLETED,
                run_id=record.id,
                agent_id=record.agent_id,
                provider_id=response.provider_id,
                payload={"status": record.status, "model_id": response.model_id},
            )

    async def _finish_cancelled(self, run_id: UUID) -> None:
        async with self._session_factory() as session:
            record = await self._run_repository.get(session, run_id)
            if record is None or record.status in TERMINAL_RUN_STATUSES:
                return
            record.status = RunStatus.CANCELLED
            record.finished_at = _utc_now()
            agent = await self._agent_repository.get(session, UUID(record.agent_id))
            if agent is not None:
                agent.status = AgentStatus.IDLE
            await session.commit()
            await self._publish(
                RuntimeEventType.RUN_CANCELLED,
                run_id=record.id,
                agent_id=record.agent_id,
                payload={"status": record.status},
            )

    async def _finish_failed(self, run_id: UUID, error: str) -> None:
        async with self._session_factory() as session:
            record = await self._run_repository.get(session, run_id)
            if record is None or record.status in TERMINAL_RUN_STATUSES:
                return
            record.status = RunStatus.FAILED
            record.error = error
            record.finished_at = _utc_now()
            agent = await self._agent_repository.get(session, UUID(record.agent_id))
            if agent is not None:
                agent.status = AgentStatus.ERROR
            await session.commit()
            await self._publish(
                RuntimeEventType.RUN_FAILED,
                run_id=record.id,
                agent_id=record.agent_id,
                payload={"status": record.status, "error": error},
                severity="error",
            )

    def _lock_for(self, agent_id: UUID) -> asyncio.Lock:
        return self._agent_locks.setdefault(agent_id, asyncio.Lock())

    async def _publish(
        self,
        type: RuntimeEventType,
        *,
        run_id: str | None = None,
        agent_id: str | None = None,
        provider_id: str | None = None,
        payload: dict[str, object] | None = None,
        severity: str = "info",
    ) -> None:
        if self._events is None:
            return
        await self._events.publish(
            RuntimeEvent.create(
                type,
                self._project_id,
                run_id=run_id,
                task_id=f"task_{run_id}" if run_id else None,
                agent_id=agent_id,
                provider_id=provider_id,
                payload=payload or {},
                severity=severity,
            )
        )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _agent_from_record(record: AgentRecord) -> Agent:
    return Agent(
        id=UUID(record.id),
        name=record.name,
        description=record.description,
        status=record.status,
        model_ref=record.model_ref,
        graph_definition=record.graph_definition,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _run_from_record(record: AgentRunRecord) -> AgentRun:
    return AgentRun(
        id=UUID(record.id),
        agent_id=UUID(record.agent_id),
        status=record.status,
        input_text=record.input_text,
        output_text=record.output_text,
        error=record.error,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        provider_id=record.provider_id,
        model_id=record.model_id,
        finish_reason=record.finish_reason,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        total_tokens=record.total_tokens,
        latency_ms=record.latency_ms,
    )
