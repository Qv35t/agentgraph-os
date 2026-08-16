import asyncio
import json
from datetime import datetime
from time import monotonic
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agentgraph.domain.remote import RuntimeEvent, RuntimeEventType
from agentgraph.domain.tools import ToolDefinition, ToolResult, ToolRisk, ToolStatus
from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import ToolInvocationRecord
from agentgraph.repositories.tool_invocations import ToolInvocationRepository
from agentgraph.runtime.events import RuntimeEventBus
from agentgraph.services.remote import ApprovalService
from agentgraph.settings import Settings


class DesktopLauncher(Protocol):
    async def launch(self, arguments: tuple[str, ...]) -> None: ...


class DesktopOpenApplicationArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    application_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")


class _SubprocessDesktopLauncher:
    async def launch(self, arguments: tuple[str, ...]) -> None:
        # `arguments` originates only from server-owned allowlist configuration.
        await asyncio.create_subprocess_exec(
            *arguments,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )


class ToolService:
    """Executes only registered, typed tools after policy and approval checks."""

    _definitions = {
        "system.current_time": ToolDefinition(
            id="system.current_time",
            description="Return the current local system time.",
            risk=ToolRisk.READ,
            requires_approval=False,
        ),
        "desktop.open_application": ToolDefinition(
            id="desktop.open_application",
            description="Open a configured local application alias.",
            risk=ToolRisk.CONTROL,
            requires_approval=True,
        ),
    }

    def __init__(
        self,
        session_factory: SessionFactory,
        approvals: ApprovalService,
        events: RuntimeEventBus,
        settings: Settings,
        launcher: DesktopLauncher | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._approvals = approvals
        self._events = events
        self._settings = settings
        self._launcher = launcher or _SubprocessDesktopLauncher()
        self._allowlist = _application_allowlist(settings.tool_application_allowlist_json)
        self._repository = ToolInvocationRepository()

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._definitions.values())

    async def execute(self, *, run_id: UUID, tool_id: str, arguments: dict[str, object]) -> ToolResult:
        definition = self._definitions.get(tool_id)
        if not self._settings.tools_enabled:
            return ToolResult(tool_id, ToolStatus.FAILED, error_code="tool_disabled")
        if definition is None:
            return ToolResult(tool_id, ToolStatus.FAILED, error_code="tool_not_found")

        validated = self._validate_arguments(tool_id, arguments)
        if validated is None:
            return ToolResult(tool_id, ToolStatus.FAILED, error_code="tool_invalid_arguments")
        if tool_id == "desktop.open_application" and validated.application_id not in self._allowlist:
            return ToolResult(tool_id, ToolStatus.FAILED, error_code="tool_not_allowed")

        invocation = ToolInvocationRecord(
            run_id=str(run_id),
            tool_id=tool_id,
            risk=definition.risk.value,
            status=ToolStatus.PENDING_APPROVAL.value if definition.requires_approval else ToolStatus.SUCCEEDED.value,
            input_metadata={"application_id": validated.application_id}
            if isinstance(validated, DesktopOpenApplicationArguments)
            else {},
        )
        async with self._session_factory() as session:
            await self._repository.create(session, invocation)
            await session.commit()
            await session.refresh(invocation)

        approval_id: str | None = None
        if definition.requires_approval:
            approval = await self._approvals.create(
                project_id=self._settings.project_id,
                action=tool_id,
                description="Lexi requested a controlled desktop action.",
                requested_by="lexi",
                run_id=str(run_id),
            )
            approval_id = approval.id
            await self._update_invocation(invocation.id, approval_id=approval_id)
            decision = await self._approvals.wait_for_decision(
                approval_id, self._settings.tool_approval_timeout_seconds
            )
            if decision == "rejected":
                return await self._complete(
                    invocation.id, ToolResult(tool_id, ToolStatus.REJECTED, approval_id=approval_id)
                )
            if decision == "expired":
                return await self._complete(
                    invocation.id, ToolResult(tool_id, ToolStatus.EXPIRED, approval_id=approval_id)
                )
            if decision == "cancelled":
                return await self._complete(
                    invocation.id, ToolResult(tool_id, ToolStatus.CANCELLED, approval_id=approval_id)
                )

        started = monotonic()
        await self._events.publish(
            RuntimeEvent.create(
                RuntimeEventType.TOOL_STARTED,
                self._settings.project_id,
                run_id=str(run_id),
                payload={"tool_id": tool_id, "risk": definition.risk.value, "approval_id": approval_id},
            )
        )
        try:
            output = await asyncio.wait_for(
                self._execute_validated(tool_id, validated), self._settings.tool_execution_timeout_seconds
            )
        except asyncio.CancelledError:
            result = ToolResult(tool_id, ToolStatus.CANCELLED, error_code="tool_cancelled", approval_id=approval_id)
            await self._complete(invocation.id, result, started)
            raise
        except TimeoutError:
            result = ToolResult(tool_id, ToolStatus.FAILED, error_code="tool_timeout", approval_id=approval_id)
        except OSError:
            result = ToolResult(tool_id, ToolStatus.FAILED, error_code="tool_execution_failed", approval_id=approval_id)
        else:
            result = ToolResult(tool_id, ToolStatus.SUCCEEDED, output=output, approval_id=approval_id)
        return await self._complete(invocation.id, result, started)

    def _validate_arguments(
        self, tool_id: str, arguments: dict[str, object]
    ) -> DesktopOpenApplicationArguments | None:
        if tool_id == "system.current_time":
            return DesktopOpenApplicationArguments.model_construct(application_id="system") if not arguments else None
        try:
            return DesktopOpenApplicationArguments.model_validate(arguments)
        except ValueError:
            return None

    async def list_run_invocations(self, run_id: UUID) -> list[dict[str, object]]:
        async with self._session_factory() as session:
            invocations = await self._repository.list_for_run(session, run_id)
            return [
                {
                    "id": invocation.id,
                    "tool_id": invocation.tool_id,
                    "risk": invocation.risk,
                    "status": invocation.status,
                    "approval_id": invocation.approval_id,
                    "error_code": invocation.error_code,
                    "started_at": invocation.started_at,
                    "finished_at": invocation.finished_at,
                    "duration_ms": invocation.duration_ms,
                }
                for invocation in invocations
            ]

    async def _execute_validated(self, tool_id: str, arguments: DesktopOpenApplicationArguments) -> str:
        if tool_id == "system.current_time":
            return datetime.now().astimezone().isoformat(timespec="seconds")
        await self._launcher.launch(self._allowlist[arguments.application_id])
        return f"Opened configured application '{arguments.application_id}'."

    async def _complete(
        self, invocation_id: str, result: ToolResult, started: float | None = None
    ) -> ToolResult:
        duration_ms = int((monotonic() - started) * 1000) if started is not None else None
        completed = ToolResult(
            result.tool_id,
            result.status,
            output=_bounded(result.output, self._settings.tool_max_output_chars),
            error_code=result.error_code,
            duration_ms=duration_ms,
            approval_id=result.approval_id,
        )
        async with self._session_factory() as session:
            invocation = await self._repository.get(session, invocation_id)
            run_id = invocation.run_id if invocation is not None else None
            if invocation is not None:
                invocation.status = completed.status.value
                invocation.output_metadata = {"output": completed.output} if completed.output else None
                invocation.error_code = completed.error_code
                invocation.finished_at = datetime.now().astimezone()
                invocation.duration_ms = completed.duration_ms
                await session.commit()
        event_type = RuntimeEventType.TOOL_COMPLETED
        if completed.status is not ToolStatus.SUCCEEDED:
            event_type = RuntimeEventType.TOOL_FAILED
        await self._events.publish(
            RuntimeEvent.create(
                event_type,
                self._settings.project_id,
                run_id=run_id,
                payload={
                    "tool_id": completed.tool_id,
                    "status": completed.status.value,
                    "error_code": completed.error_code,
                    "duration_ms": completed.duration_ms,
                    "approval_id": completed.approval_id,
                },
                severity="error" if event_type is RuntimeEventType.TOOL_FAILED else "info",
            )
        )
        return completed

    async def _update_invocation(self, invocation_id: str, *, approval_id: str) -> None:
        async with self._session_factory() as session:
            invocation = await self._repository.get(session, invocation_id)
            if invocation is not None:
                invocation.approval_id = approval_id
                await session.commit()


def _application_allowlist(raw: str) -> dict[str, tuple[str, ...]]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    result: dict[str, tuple[str, ...]] = {}
    for application_id, command in value.items():
        if not isinstance(application_id, str) or not isinstance(command, list) or not command:
            continue
        if all(isinstance(argument, str) and argument for argument in command):
            result[application_id] = tuple(command)
    return result


def _bounded(value: str | None, limit: int) -> str | None:
    if value is None or len(value) <= limit:
        return value
    return f"{value[:limit]} [truncated]"
