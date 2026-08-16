import asyncio
import inspect
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.domain.entities import (
    ACTIVE_RUN_STATUSES,
    TERMINAL_RUN_STATUSES,
    Agent,
    AgentRun,
    AgentStatus,
    RunStatus,
    RunTreeNode,
)
from agentgraph.domain.orchestration import TeamGraphError, parse_team_graph
from agentgraph.domain.remote import RuntimeEvent, RuntimeEventType
from agentgraph.models.contracts import ModelResponse, ModelRouterError
from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import AgentRecord, AgentRunRecord, RunDelegationRecord
from agentgraph.repositories.agents import AgentRepository
from agentgraph.repositories.delegations import RunDelegationRepository
from agentgraph.repositories.runs import RunRepository
from agentgraph.runtime.events import RuntimeEventBus
from agentgraph.runtime.execution import AgentExecutionRequest, DelegationContext
from agentgraph.runtime.registry import RunRegistry
from agentgraph.services.errors import AgentNotFoundError, LifecycleConflictError, OrchestrationError, RunNotFoundError
from agentgraph.settings import Settings


class AgentRuntime(Protocol):
    async def invoke(self, execution: AgentExecutionRequest) -> ModelResponse: ...


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
        settings: Settings | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._runtime = runtime
        self._registry = registry
        self._runtime_delay_seconds = runtime_delay_seconds
        self._cancellation_timeout_seconds = cancellation_timeout_seconds
        self._agent_repository = AgentRepository()
        self._run_repository = RunRepository()
        self._delegation_repository = RunDelegationRepository()
        self._agent_locks: dict[UUID, asyncio.Lock] = {}
        self._terminal_locks: dict[UUID, asyncio.Lock] = {}
        self._events = events
        self._project_id = project_id
        self._settings = settings or Settings()
        self._execution_contexts: dict[UUID, DelegationContext] = {}

    async def create_agent(
        self,
        *,
        name: str,
        description: str | None,
        model_ref: str,
        graph_definition: dict[str, object],
    ) -> Agent:
        async with self._session_factory() as session:
            await self._validate_team_graph(session, graph_definition, None)
            record = await self._agent_repository.create(
                session,
                name=name,
                description=description,
                model_ref=model_ref,
                graph_definition=graph_definition,
            )
            await self._validate_team_graph(session, graph_definition, UUID(record.id))
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
                await self._validate_team_graph(session, graph_definition, agent_id)
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
                for candidate in await self._agent_repository.list(session):
                    if candidate.id == record.id:
                        continue
                    try:
                        team = parse_team_graph(candidate.graph_definition, self._settings.orchestration_max_workers)
                    except TeamGraphError:
                        continue
                    if any(node.agent_id == agent_id for node in team.nodes):
                        raise LifecycleConflictError("A team graph references this agent")
                await self._agent_repository.delete(session, record)
                await session.commit()

    async def start_run(self, *, agent_id: UUID, input_text: str) -> AgentRun:
        return await self._start_run(
            agent_id=agent_id, input_text=input_text, context=None, parent_run_id=None, node_id=None
        )

    async def run_child(
        self,
        *,
        parent_run_id: UUID,
        node_id: str,
        agent_id: UUID,
        input_text: str,
        context: DelegationContext,
    ) -> AgentRun:
        if context.depth > self._settings.orchestration_max_depth:
            raise OrchestrationError("MAX_DEPTH_EXCEEDED", "Maximum delegation depth exceeded")
        if agent_id in context.ancestry:
            raise OrchestrationError("DELEGATION_CYCLE", "Team delegation references an ancestor")
        child = await self._start_run(
            agent_id=agent_id,
            input_text=input_text,
            context=context,
            parent_run_id=parent_run_id,
            node_id=node_id,
        )
        task = self._registry.get(child.id)
        if task is None:
            raise OrchestrationError("CHILD_START_FAILED", "Child execution handle unavailable")
        try:
            await asyncio.wait_for(asyncio.shield(task), self._settings.orchestration_child_timeout_seconds)
        except TimeoutError as error:
            await self._stop_descendants(child.id)
            try:
                await self.stop_run(child.id)
            except LifecycleConflictError:
                pass
            raise OrchestrationError("CHILD_TIMEOUT", "Child execution timed out") from error
        except asyncio.CancelledError:
            await self._stop_descendants(child.id)
            try:
                await self.stop_run(child.id)
            except LifecycleConflictError:
                pass
            raise
        return await self.get_run(child.id)

    async def _start_run(
        self,
        *,
        agent_id: UUID,
        input_text: str,
        context: DelegationContext | None,
        parent_run_id: UUID | None,
        node_id: str | None,
    ) -> AgentRun:
        async with self._lock_for(agent_id):
            async with self._session_factory() as session:
                # SQLite has no row-level locks. This serializes the durable active-run check.
                await session.execute(text("BEGIN IMMEDIATE"))
                agent = await self._agent_repository.get(session, agent_id)
                if agent is None:
                    raise AgentNotFoundError
                await self._validate_team_graph(session, agent.graph_definition, agent_id)
                if await self._run_repository.has_active_for_agent(session, agent_id):
                    raise LifecycleConflictError("This agent already has an active run")
                try:
                    run = await self._run_repository.create(session, agent_id=agent_id, input_text=input_text)
                except IntegrityError as error:
                    await session.rollback()
                    raise LifecycleConflictError("This agent already has an active run") from error
                agent.status = AgentStatus.RUNNING
                if parent_run_id is not None and node_id is not None and context is not None:
                    await self._delegation_repository.create(
                        session,
                        parent_run_id=parent_run_id,
                        child_run_id=UUID(run.id),
                        node_id=node_id,
                        depth=context.depth,
                    )
                await session.commit()
                await session.refresh(run)

            run_id = UUID(run.id)
            if context is not None:
                self._execution_contexts[run_id] = context
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

    async def get_run_tree(self, run_id: UUID) -> RunTreeNode:
        async with self._session_factory() as session:
            root_id = run_id
            while True:
                parents = await self._delegation_repository.list_for_child(session, root_id)
                if not parents:
                    break
                root_id = UUID(parents[0].parent_run_id)
            root = await self._run_repository.get(session, root_id)
            if root is None:
                raise RunNotFoundError
            records = {root_id: _run_from_record(root)}
            relations: list[RunDelegationRecord] = []
            frontier = [root_id]
            while frontier:
                batch = await self._delegation_repository.list_for_parents(session, frontier)
                relations.extend(batch)
                child_ids = [UUID(item.child_run_id) for item in batch]
                child_runs = await self._run_repository.list_by_ids(session, child_ids)
                records.update({UUID(record.id): _run_from_record(record) for record in child_runs})
                frontier = child_ids

        by_parent: dict[UUID, list[RunDelegationRecord]] = {}
        for relation in relations:
            parent_id = UUID(relation.parent_run_id)
            by_parent.setdefault(parent_id, []).append(relation)

        def build(current_id: UUID, node_id: str | None, depth: int) -> RunTreeNode:
            children = tuple(
                build(UUID(item.child_run_id), item.node_id, item.depth) for item in by_parent.get(current_id, [])
            )
            return RunTreeNode(node_id, depth, records[current_id], children)

        return build(root_id, None, 0)

    async def stop_run(self, run_id: UUID) -> AgentRun:
        run = await self.get_run(run_id)
        if run.status in TERMINAL_RUN_STATUSES:
            raise LifecycleConflictError("This run is already terminal")

        await self._stop_descendants(run_id)
        task = self._registry.get(run_id)
        if task is None:
            await self._finish_failed(run_id, "Live execution handle unavailable")
            raise LifecycleConflictError("This run has no live execution handle")

        if not await self._registry.cancel(run_id, self._cancellation_timeout_seconds):
            raise LifecycleConflictError("Run cancellation timed out")
        await self._finish_cancelled(run_id)
        return await self.get_run(run_id)

    async def _stop_descendants(self, run_id: UUID) -> None:
        async with self._session_factory() as session:
            children = await self._delegation_repository.list_for_parents(session, [run_id])
        for relation in children:
            child_id = UUID(relation.child_run_id)
            child = await self.get_run(child_id)
            if child.status in TERMINAL_RUN_STATUSES:
                continue
            await self._stop_descendants(child_id)
            try:
                await self.stop_run(child_id)
            except LifecycleConflictError:
                continue

    async def _validate_team_graph(
        self, session: AsyncSession, graph_definition: dict[str, object], owner_agent_id: UUID | None
    ) -> None:
        if graph_definition.get("runtime", "model-v1") != "team-v1":
            return
        try:
            graph = parse_team_graph(graph_definition, self._settings.orchestration_max_workers)
        except TeamGraphError as error:
            raise OrchestrationError(error.code, str(error)) from error
        for node in graph.nodes:
            if owner_agent_id is not None and node.agent_id == owner_agent_id:
                raise OrchestrationError("INVALID_TEAM_GRAPH", "A team cannot delegate to itself")
            record = await self._agent_repository.get(session, node.agent_id)
            if record is None:
                raise OrchestrationError("MISSING_AGENT_REFERENCE", "Team graph references an unknown agent")

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
            async with self._session_factory() as session:
                await self._validate_team_graph(session, agent.graph_definition, agent.id)
            execution = AgentExecutionRequest(
                agent_id=run.agent_id,
                run_id=run.id,
                input_text=run.input_text,
                model_ref=agent.model_ref,
                graph_definition=agent.graph_definition,
                delegation_context=self._execution_contexts.get(run_id),
            )
            response = await self._invoke_runtime(execution)
        except asyncio.CancelledError:
            await self._finish_cancelled(run_id)
            raise
        except ModelRouterError as error:
            await self._finish_failed(run_id, f"{error.code}: {error}")
        except OrchestrationError as error:
            await self._finish_failed(run_id, f"{error.code}: {error}")
        except Exception as error:
            await self._finish_failed(run_id, f"Run execution failed: {type(error).__name__}")
        else:
            await self._finish_succeeded(run_id, response)
        finally:
            self._registry.remove(run_id)
            self._execution_contexts.pop(run_id, None)

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
        async with self._terminal_lock_for(run_id):
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
        async with self._terminal_lock_for(run_id):
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
        async with self._terminal_lock_for(run_id):
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

    def _terminal_lock_for(self, run_id: UUID) -> asyncio.Lock:
        return self._terminal_locks.setdefault(run_id, asyncio.Lock())

    async def _invoke_runtime(self, execution: AgentExecutionRequest) -> ModelResponse:
        if "execution" in inspect.signature(self._runtime.invoke).parameters:
            return await self._runtime.invoke(execution)
        # Preserve the Phase 2 runtime protocol for existing in-process extensions.
        return await self._runtime.invoke(  # type: ignore[call-arg]
            agent_id=execution.agent_id,
            run_id=execution.run_id,
            input_text=execution.input_text,
            model_ref=execution.model_ref,
        )

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
