# ruff: noqa: E501

import asyncio
import json
from contextvars import ContextVar, Token
from datetime import datetime
from uuid import UUID, uuid4

from agentgraph.domain.remote import (
    ApprovalRequest,
    ApprovalStatus,
    Permission,
    Principal,
    RuntimeCommand,
    RuntimeCommandType,
    RuntimeEvent,
    RuntimeEventType,
)
from agentgraph.models.router import ModelRouter
from agentgraph.runtime.events import RuntimeEventBus
from agentgraph.services.errors import LifecycleConflictError
from agentgraph.services.manager import AgentManager


class AuthorizationError(Exception):
    pass


_request_principal: ContextVar[Principal | None] = ContextVar("request_principal", default=None)


def set_request_principal(principal: Principal | None) -> Token[Principal | None]:
    return _request_principal.set(principal)


class AuthorizationService:
    def __init__(self, remote_enabled: bool, policies_json: str) -> None:
        self._remote_enabled = remote_enabled
        self._policies = _parse_policies(policies_json)

    def principal(self, identity: str | None) -> Principal:
        del identity
        principal = _request_principal.get()
        if principal is None:
            raise AuthorizationError("Authentication is required")
        return principal

    @staticmethod
    def require(principal: Principal, permission: Permission) -> None:
        if permission not in principal.permissions and Permission.ADMIN not in principal.permissions:
            raise AuthorizationError("Principal lacks required permission")


class RemoteCommandService:
    def __init__(self, manager: AgentManager, model_router: ModelRouter, authorization: AuthorizationService) -> None:
        self._manager = manager
        self._model_router = model_router
        self._authorization = authorization

    async def dispatch(self, command: RuntimeCommand) -> object:
        permission = {
            RuntimeCommandType.CREATE_AGENT: Permission.EXECUTE,
            RuntimeCommandType.UPDATE_AGENT_GRAPH: Permission.EXECUTE,
            RuntimeCommandType.START_RUN: Permission.EXECUTE,
            RuntimeCommandType.STOP_RUN: Permission.CONTROL,
            RuntimeCommandType.GET_AGENT: Permission.READ,
            RuntimeCommandType.GET_RUN: Permission.READ,
            RuntimeCommandType.GET_RUN_TREE: Permission.READ,
            RuntimeCommandType.LIST_RUNS: Permission.READ,
            RuntimeCommandType.LIST_PROVIDERS: Permission.READ,
            RuntimeCommandType.LIST_AGENTS: Permission.READ,
        }[command.type]
        self._authorization.require(command.principal, permission)
        if command.type is RuntimeCommandType.CREATE_AGENT:
            return await self._manager.create_agent(
                name=str(command.payload["name"]),
                description=_optional_text(command.payload.get("description")),
                model_ref=str(command.payload["model_ref"]),
                graph_definition=_graph_definition(command.payload.get("graph_definition")),
            )
        if command.type is RuntimeCommandType.UPDATE_AGENT_GRAPH:
            return await self._manager.update_agent_graph(
                UUID(_required(command.target_id)), _graph_definition(command.payload.get("graph_definition"))
            )
        if command.type is RuntimeCommandType.START_RUN:
            return await self._manager.start_run(
                agent_id=UUID(_required(command.target_id)), input_text=str(command.payload["input_text"])
            )
        if command.type is RuntimeCommandType.STOP_RUN:
            return await self._manager.stop_run(UUID(_required(command.target_id)))
        if command.type is RuntimeCommandType.GET_AGENT:
            return await self._manager.get_agent(UUID(_required(command.target_id)))
        if command.type is RuntimeCommandType.GET_RUN:
            return await self._manager.get_run(UUID(_required(command.target_id)))
        if command.type is RuntimeCommandType.GET_RUN_TREE:
            return await self._manager.get_run_tree(UUID(_required(command.target_id)))
        if command.type is RuntimeCommandType.LIST_RUNS:
            return await self._manager.list_runs(UUID(_required(command.target_id)))
        if command.type is RuntimeCommandType.LIST_AGENTS:
            return await self._manager.list_agents()
        return await self._model_router.provider_statuses()


class ApprovalService:
    """Process-local approval contract; persistence and runtime waiting are future explicit work."""

    def __init__(self, events: RuntimeEventBus | None = None) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._decisions: dict[str, asyncio.Future[ApprovalStatus]] = {}
        self._events = events

    async def create(
        self,
        *,
        project_id: str,
        action: str,
        description: str,
        requested_by: str,
        run_id: str | None = None,
        task_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> ApprovalRequest:
        approval = ApprovalRequest(
            f"apr_{uuid4().hex}",
            project_id,
            action,
            description,
            requested_by,
            run_id=run_id,
            task_id=task_id,
            expires_at=expires_at,
        )
        self._requests[approval.id] = approval
        self._decisions[approval.id] = asyncio.get_running_loop().create_future()
        await self._publish(approval, RuntimeEventType.APPROVAL_REQUIRED)
        return approval

    async def decide(self, approval_id: str, approved: bool) -> ApprovalRequest:
        approval = self._requests.get(approval_id)
        if approval is None:
            raise KeyError(approval_id)
        if approval.status is not ApprovalStatus.PENDING:
            raise LifecycleConflictError("Approval is no longer pending")
        if approval.expires_at and approval.expires_at <= datetime.now(approval.expires_at.tzinfo):
            approval.status = ApprovalStatus.EXPIRED
            await self._publish(approval, RuntimeEventType.APPROVAL_EXPIRED)
            raise LifecycleConflictError("Approval has expired")
        approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        decision = self._decisions.get(approval.id)
        if decision is not None and not decision.done():
            decision.set_result(approval.status)
        await self._publish(
            approval,
            RuntimeEventType.APPROVAL_APPROVED if approved else RuntimeEventType.APPROVAL_REJECTED,
        )
        return approval

    async def wait_for_decision(self, approval_id: str, timeout_seconds: float) -> str:
        approval = self._requests.get(approval_id)
        decision = self._decisions.get(approval_id)
        if approval is None or decision is None:
            return "cancelled"
        try:
            status = await asyncio.wait_for(asyncio.shield(decision), timeout_seconds)
        except TimeoutError:
            if approval.status is ApprovalStatus.PENDING:
                approval.status = ApprovalStatus.EXPIRED
                await self._publish(approval, RuntimeEventType.APPROVAL_EXPIRED)
            return "expired"
        except asyncio.CancelledError:
            await self.cancel(approval_id)
            raise
        return status.value

    async def cancel(self, approval_id: str) -> None:
        approval = self._requests.get(approval_id)
        if approval is None or approval.status is not ApprovalStatus.PENDING:
            return
        approval.status = ApprovalStatus.CANCELLED
        decision = self._decisions.get(approval.id)
        if decision is not None and not decision.done():
            decision.set_result(approval.status)

    def list_pending(self, project_id: str | None = None) -> list[ApprovalRequest]:
        return [
            approval
            for approval in self._requests.values()
            if approval.status is ApprovalStatus.PENDING and (project_id is None or approval.project_id == project_id)
        ]

    async def _publish(self, approval: ApprovalRequest, event_type: RuntimeEventType) -> None:
        if self._events is None:
            return
        await self._events.publish(
            RuntimeEvent.create(
                event_type,
                approval.project_id,
                run_id=approval.run_id,
                task_id=approval.task_id,
                payload={"approval_id": approval.id, "action": approval.action, "status": approval.status},
            )
        )


def _parse_policies(value: str) -> dict[str, frozenset[Permission]]:
    try:
        raw = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    result: dict[str, frozenset[Permission]] = {}
    for identity, permissions in raw.items():
        if isinstance(identity, str) and isinstance(permissions, list):
            try:
                result[identity] = frozenset(Permission(item) for item in permissions)
            except ValueError:
                continue
    return result


def _required(value: str | None) -> str:
    if value is None:
        raise ValueError("Command target is required")
    return value


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _graph_definition(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("Graph definition must be an object")
    return {str(key): item for key, item in value.items()}
