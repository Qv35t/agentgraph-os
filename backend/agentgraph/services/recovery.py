from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.domain.entities import AgentStatus, RunStatus
from agentgraph.domain.recovery import (
    CHECKPOINT_FORMAT_VERSION,
    ActionLedgerStatus,
    CheckpointReason,
    RecoveryOutcome,
    checkpoint_checksum,
)
from agentgraph.domain.remote import RuntimeEvent, RuntimeEventType
from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import AgentRecord, AgentRunRecord, RunActionLedgerEntryRecord, RunCheckpointRecord
from agentgraph.repositories.agents import AgentRepository
from agentgraph.repositories.recovery import RecoveryRepository
from agentgraph.repositories.runs import RunRepository
from agentgraph.runtime.events import RuntimeEventBus
from agentgraph.settings import Settings

_SECRET_MARKERS = ("api_key", "token", "password", "authorization", "secret", "credential")


class RecoveryService:
    """Persists recovery evidence and stops interrupted work without replaying it."""

    def __init__(self, session_factory: SessionFactory, events: RuntimeEventBus | None, settings: Settings) -> None:
        self._session_factory = session_factory
        self._events = events
        self._settings = settings
        self._agents = AgentRepository()
        self._runs = RunRepository()
        self._recovery = RecoveryRepository()

    async def create_initial_checkpoint(
        self, session: AsyncSession, run: AgentRunRecord, agent: AgentRecord
    ) -> RunCheckpointRecord:
        execution_spec = {
            "runtime": agent.graph_definition.get("runtime", "model-v1"),
            "model_ref": agent.model_ref,
            "graph_definition": agent.graph_definition,
            "input_sha256": _digest(run.input_text),
        }
        run.execution_spec = execution_spec
        return await self._create_checkpoint(
            session,
            run,
            CheckpointReason.CREATED,
            {"execution_spec": execution_spec, "run_status": run.status},
        )

    async def create_lifecycle_checkpoint(
        self, session: AsyncSession, run: AgentRunRecord, reason: CheckpointReason
    ) -> RunCheckpointRecord:
        return await self._create_checkpoint(
            session,
            run,
            reason,
            {"execution_spec": run.execution_spec or {}, "run_status": run.status},
        )

    async def publish_checkpoint(self, checkpoint: RunCheckpointRecord) -> None:
        await self._publish(
            RuntimeEventType.CHECKPOINT_CREATED,
            checkpoint.run_id,
            {"checkpoint_id": checkpoint.id, "sequence": checkpoint.sequence, "reason": checkpoint.reason},
        )

    async def record_action_intent(
        self,
        *,
        run_id: UUID,
        tool_invocation_id: str,
        action_type: str,
        risk: str,
        metadata: dict[str, object],
    ) -> str:
        async with self._session_factory() as session:
            entry = await self._recovery.create_action(
                session,
                run_id=run_id,
                tool_invocation_id=tool_invocation_id,
                action_type=action_type,
                risk=risk,
                metadata=_sanitize(metadata),
            )
            await session.commit()
            return entry.id

    async def update_action(self, entry_id: str, status: ActionLedgerStatus) -> None:
        async with self._session_factory() as session:
            entry = await self._recovery.get_action(session, entry_id)
            if entry is None:
                return
            entry.status = status
            if status is ActionLedgerStatus.STARTED:
                entry.started_at = _now()
            elif status in {ActionLedgerStatus.CONFIRMED, ActionLedgerStatus.FAILED, ActionLedgerStatus.UNCERTAIN}:
                entry.finished_at = _now()
            await session.commit()

    async def recover_stale_runs(self) -> None:
        recovered: list[tuple[str, RecoveryOutcome, RunCheckpointRecord]] = []
        async with self._session_factory() as session:
            for run in await self._runs.list_stale(session):
                checkpoint, outcome, details = await self._assess_stale_run(session, run.id)
                await self._recovery.create_decision(
                    session,
                    run_id=UUID(run.id),
                    checkpoint_id=checkpoint.id if checkpoint else None,
                    outcome=outcome,
                    details=details,
                )
                run.status = RunStatus.FAILED
                run.error = "Run interrupted by application restart"
                run.finished_at = _now()
                agent = await self._agents.get(session, UUID(run.agent_id))
                if agent is not None:
                    agent.status = AgentStatus.ERROR
                terminal_checkpoint = await self.create_lifecycle_checkpoint(session, run, CheckpointReason.FAILED)
                recovered.append((run.id, outcome, terminal_checkpoint))
            await session.commit()
        for run_id, outcome, checkpoint in recovered:
            await self.publish_checkpoint(checkpoint)
            await self._publish(
                RuntimeEventType.RECOVERY_ASSESSED,
                run_id,
                {"outcome": outcome, "automatic_resume": False, "automatic_rollback": False},
                severity="warning",
            )

    async def _assess_stale_run(
        self, session: AsyncSession, run_id: str
    ) -> tuple[RunCheckpointRecord | None, RecoveryOutcome, dict[str, object]]:
        try:
            checkpoint = await self._recovery.latest_checkpoint(session, UUID(run_id))
            actions = await self._recovery.list_actions(session, UUID(run_id))
        except (LookupError, TypeError, ValueError):
            return None, RecoveryOutcome.BLOCKED_CORRUPT_CHECKPOINT, {
                "reason": "A checkpoint could not be decoded or validated."
            }
        outcome, details = _recovery_outcome(run_id, checkpoint, actions)
        return checkpoint, outcome, details

    async def report(self, run_id: UUID) -> dict[str, object]:
        async with self._session_factory() as session:
            checkpoints = await self._recovery.list_checkpoint_metadata(session, run_id)
            actions = await self._recovery.list_actions(session, run_id)
            decisions = await self._recovery.list_decisions(session, run_id)
        return {
            "run_id": str(run_id),
            "checkpoints": [
                {
                    "checkpoint_id": checkpoint["id"],
                    "sequence": checkpoint["sequence"],
                    "format_version": checkpoint["format_version"],
                    "reason": checkpoint["reason"],
                    "checksum": checkpoint["checksum"],
                    "created_at": checkpoint["created_at"],
                }
                for checkpoint in checkpoints
            ],
            "actions": [
                {
                    "entry_id": action.id,
                    "action_type": action.action_type,
                    "risk": action.risk,
                    "status": action.status,
                    "rollback_status": action.rollback_status,
                    "created_at": action.created_at,
                    "started_at": action.started_at,
                    "finished_at": action.finished_at,
                }
                for action in actions
            ],
            "decisions": [
                {
                    "decision_id": decision.id,
                    "checkpoint_id": decision.checkpoint_id,
                    "outcome": decision.outcome,
                    "details": _sanitize(decision.details),
                    "created_at": decision.created_at,
                }
                for decision in decisions
            ],
            "limits": {
                "automatic_resume": False,
                "automatic_rollback": False,
                "description": "Interrupted runs are assessed and stopped; they are never replayed automatically.",
            },
        }

    async def _create_checkpoint(
        self, session: AsyncSession, run: AgentRunRecord, reason: CheckpointReason, state: dict[str, object]
    ) -> RunCheckpointRecord:
        state = {"format_version": CHECKPOINT_FORMAT_VERSION, "run_id": run.id, **state}
        return await self._recovery.create_checkpoint(session, run_id=UUID(run.id), reason=reason, state=state)

    async def _publish(
        self, event_type: RuntimeEventType, run_id: str, payload: dict[str, object], severity: str = "info"
    ) -> None:
        if self._events is None:
            return
        await self._events.publish(
            RuntimeEvent.create(
                event_type, self._settings.project_id, run_id=run_id, payload=payload, severity=severity
            )
        )


def _recovery_outcome(
    run_id: str, checkpoint: RunCheckpointRecord | None, actions: list[RunActionLedgerEntryRecord]
) -> tuple[RecoveryOutcome, dict[str, object]]:
    if checkpoint is None:
        return RecoveryOutcome.BLOCKED_NO_CHECKPOINT, {
            "reason": "No durable checkpoint exists for this interrupted run."
        }
    if not _checkpoint_is_valid(run_id, checkpoint):
        return RecoveryOutcome.BLOCKED_CORRUPT_CHECKPOINT, {
            "reason": "The latest checkpoint failed integrity validation."
        }
    uncertain = [
        item.action_type
        for item in actions
        if item.status
        in {ActionLedgerStatus.INTENT_RECORDED, ActionLedgerStatus.STARTED, ActionLedgerStatus.UNCERTAIN}
    ]
    if uncertain:
        return RecoveryOutcome.BLOCKED_UNCERTAIN_ACTION, {
            "reason": "An external action may have occurred before the interruption.",
            "uncertain_actions": uncertain,
        }
    return RecoveryOutcome.STOPPED_NO_REPLAY, {
        "reason": "No uncertain action was recorded; automatic replay remains disabled."
    }


def _checkpoint_is_valid(run_id: str, checkpoint: RunCheckpointRecord) -> bool:
    state = checkpoint.state
    if not isinstance(state, dict):
        return False
    if (
        checkpoint.format_version != CHECKPOINT_FORMAT_VERSION
        or state.get("format_version") != CHECKPOINT_FORMAT_VERSION
    ):
        return False
    if state.get("run_id") != run_id or not isinstance(state.get("execution_spec"), dict):
        return False
    if state.get("run_status") not in {status.value for status in RunStatus}:
        return False
    return checkpoint.checksum == checkpoint_checksum(state)


def _sanitize(metadata: dict[str, object]) -> dict[str, object]:
    return {key: "[redacted]" if _is_secret(key) else _sanitize_value(value) for key, value in metadata.items()}


def _sanitize_value(value: object) -> object:
    if isinstance(value, dict):
        return _sanitize({str(key): item for key, item in value.items()})
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def _is_secret(key: str) -> bool:
    return any(marker in key.lower() for marker in _SECRET_MARKERS)


def _digest(value: str) -> str:
    from hashlib import sha256

    return sha256(value.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)
