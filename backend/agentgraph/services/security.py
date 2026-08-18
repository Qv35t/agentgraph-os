from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.domain.remote import Permission
from agentgraph.domain.security import (
    AuthenticationStrength,
    DeviceTrust,
    GrantStatus,
    LockdownState,
    SecurityApprovalDecision,
)
from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import (
    DeviceRecord,
    GrantRecord,
    SecurityApprovalRecord,
    SecurityAuditRecord,
    SecurityStateRecord,
)
from agentgraph.repositories.security import SecurityRepository
from agentgraph.services.auth import SessionPrincipal


class SecurityAuthorizationError(Exception):
    pass


class SecurityConflictError(Exception):
    pass


class SecurityService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._repository = SecurityRepository()

    async def require(self, principal: SessionPrincipal, permission: Permission, *, mfa: bool = False) -> None:
        if permission not in principal.permissions and Permission.ADMIN not in principal.permissions:
            raise SecurityAuthorizationError("Principal lacks required permission")
        if mfa and principal.authentication_strength is not AuthenticationStrength.PASSKEY_TOTP:
            raise SecurityAuthorizationError("A stepped-up session is required")
        if permission in {Permission.EXECUTE, Permission.CONTROL, Permission.APPROVE}:
            async with self._session_factory() as session:
                state = await self._state(session)
                if state.lockdown is LockdownState.LOCKED_DOWN:
                    await self._repository.create_audit_event(
                        session,
                        event_type="security.policy",
                        result="denied",
                        metadata={"permission": permission.value, "reason": "lockdown"},
                        actor_user_id=principal.user_id,
                        session_id=principal.session_id,
                        device_id=principal.device_id,
                    )
                    await session.commit()
                    raise SecurityAuthorizationError("Lockdown is active")

    async def list_devices(self, principal: SessionPrincipal) -> list[DeviceRecord]:
        async with self._session_factory() as session:
            return await self._repository.list_devices_for_user(session, principal.user_id)

    async def rename_device(self, principal: SessionPrincipal, device_id: str, display_name: str) -> DeviceRecord:
        async with self._session_factory() as session:
            device = await self._owned_device(session, principal, device_id)
            await self._repository.update_device(session, device, display_name=display_name)
            await session.commit()
            return device

    async def trust_device(self, principal: SessionPrincipal, device_id: str) -> DeviceRecord:
        await self.require(principal, Permission.ADMIN)
        async with self._session_factory() as session:
            device = await self._owned_device(session, principal, device_id)
            if device.revoked_at is not None:
                raise SecurityConflictError("A revoked device cannot be trusted")
            await self._repository.update_device(session, device, trust=DeviceTrust.TRUSTED)
            await self._repository.create_audit_event(
                session,
                event_type="security.device_trusted",
                result="success",
                metadata={"device_id": device.id},
                actor_user_id=principal.user_id,
                session_id=principal.session_id,
                device_id=device.id,
            )
            await session.commit()
            return device

    async def revoke_device(self, principal: SessionPrincipal, device_id: str) -> DeviceRecord:
        await self.require(principal, Permission.ADMIN)
        async with self._session_factory() as session:
            device = await self._owned_device(session, principal, device_id)
            if device.revoked_at is None:
                now = datetime.now(UTC)
                await self._repository.update_device(session, device, revoked_at=now)
                await self._repository.revoke_sessions_for_device(session, device.id, now)
                await self._repository.create_audit_event(
                    session,
                    event_type="security.device_revoked",
                    result="success",
                    metadata={"device_id": device.id},
                    actor_user_id=principal.user_id,
                    session_id=principal.session_id,
                    device_id=device.id,
                )
                await session.commit()
            return device

    async def create_approval(
        self,
        principal: SessionPrincipal,
        *,
        project_id: str,
        action: str,
        reason: str,
        scope: dict[str, object],
        expires_in_seconds: int,
        target: str | None = None,
        run_id: str | None = None,
        task_ref: str | None = None,
        risk: str | None = None,
    ) -> SecurityApprovalRecord:
        await self.require(principal, Permission.EXECUTE)
        async with self._session_factory() as session:
            record = await self._repository.create_approval(
                session,
                project_id=project_id,
                requested_by=principal.user_id,
                action=action,
                reason=reason,
                scope=scope,
                expires_at=datetime.now(UTC) + timedelta(seconds=expires_in_seconds),
                target=target,
                run_id=run_id,
                task_ref=task_ref,
                risk=risk,
            )
            await self._repository.create_audit_event(
                session,
                event_type="security.approval_created",
                result="success",
                metadata={"approval_id": record.id, "action": action},
                actor_user_id=principal.user_id,
                session_id=principal.session_id,
                device_id=principal.device_id,
            )
            await session.commit()
            return record

    async def list_approvals(
        self, principal: SessionPrincipal, status: str | None = None
    ) -> list[SecurityApprovalRecord]:
        await self.require(principal, Permission.READ)
        async with self._session_factory() as session:
            return await self._repository.list_approvals(session, status=status)

    async def decide_approval(
        self, principal: SessionPrincipal, approval_id: str, decision: SecurityApprovalDecision
    ) -> tuple[SecurityApprovalRecord, GrantRecord | None]:
        await self.require(principal, Permission.APPROVE)
        async with self._session_factory() as session:
            record = await self._repository.get_approval(session, approval_id)
            if record is None:
                raise KeyError(approval_id)
            if record.expires_at <= datetime.now(UTC):
                await self._repository.decide_approval(
                    session,
                    approval_id=record.id,
                    decision=SecurityApprovalDecision.REJECT,
                    decided_by_user_id=principal.user_id,
                    decided_at=datetime.now(UTC),
                    status="expired",
                )
                await session.commit()
                raise SecurityConflictError("Approval has expired")
            status = "rejected" if decision is SecurityApprovalDecision.REJECT else "approved"
            decided = await self._repository.decide_approval(
                session,
                approval_id=record.id,
                decision=decision,
                decided_by_user_id=principal.user_id,
                decided_at=datetime.now(UTC),
                status=status,
            )
            if not decided:
                raise SecurityConflictError("Approval is no longer pending")
            grant: GrantRecord | None = None
            if decision is SecurityApprovalDecision.ALLOW_FOR_TASK:
                if record.task_ref is None:
                    raise SecurityConflictError("Task-scoped approval requires a task")
                grant = await self._repository.create_grant(
                    session,
                    issuer_user_id=principal.user_id,
                    subject=record.requested_by,
                    action=record.action,
                    target=record.target,
                    run_id=record.run_id,
                    task_ref=record.task_ref,
                    expires_at=record.expires_at,
                    source_approval_id=record.id,
                )
            await self._repository.create_audit_event(
                session,
                event_type="security.approval_decided",
                result=status,
                metadata={"approval_id": record.id, "decision": decision.value},
                actor_user_id=principal.user_id,
                session_id=principal.session_id,
                device_id=principal.device_id,
            )
            await session.commit()
            return record, grant

    async def list_grants(self, principal: SessionPrincipal) -> list[GrantRecord]:
        await self.require(principal, Permission.READ)
        async with self._session_factory() as session:
            return await self._repository.list_grants(session, subject=principal.user_id)

    async def revoke_grant(self, principal: SessionPrincipal, grant_id: str) -> GrantRecord:
        await self.require(principal, Permission.APPROVE)
        async with self._session_factory() as session:
            grant = await self._repository.get_grant(session, grant_id)
            if grant is None or grant.issuer_user_id != principal.user_id:
                raise KeyError(grant_id)
            if grant.status is GrantStatus.ACTIVE:
                await self._repository.revoke_grant(session, grant, datetime.now(UTC))
                await self._repository.create_audit_event(
                    session,
                    event_type="security.grant_revoked",
                    result="success",
                    metadata={"grant_id": grant.id},
                    actor_user_id=principal.user_id,
                    session_id=principal.session_id,
                    device_id=principal.device_id,
                )
                await session.commit()
            return grant

    async def lockdown_state(self, principal: SessionPrincipal) -> SecurityStateRecord:
        await self.require(principal, Permission.READ)
        async with self._session_factory() as session:
            return await self._state(session)

    async def activate_lockdown(self, principal: SessionPrincipal) -> SecurityStateRecord:
        await self.require(principal, Permission.ADMIN, mfa=True)
        async with self._session_factory() as session:
            state = await self._state(session)
            if state.lockdown is LockdownState.NORMAL:
                await self._repository.update_state(session, state, LockdownState.LOCKED_DOWN)
                for grant in await self._repository.list_grants(session):
                    if grant.status is GrantStatus.ACTIVE:
                        await self._repository.revoke_grant(session, grant, datetime.now(UTC))
                await self._repository.create_audit_event(
                    session,
                    event_type="security.lockdown_activated",
                    result="success",
                    metadata={},
                    actor_user_id=principal.user_id,
                    session_id=principal.session_id,
                    device_id=principal.device_id,
                )
                await session.commit()
            return state

    async def deactivate_lockdown(self, principal: SessionPrincipal) -> SecurityStateRecord:
        await self.require(principal, Permission.ADMIN, mfa=True)
        async with self._session_factory() as session:
            state = await self._state(session)
            if state.lockdown is LockdownState.LOCKED_DOWN:
                await self._repository.update_state(session, state, LockdownState.NORMAL)
                await self._repository.create_audit_event(
                    session,
                    event_type="security.lockdown_deactivated",
                    result="success",
                    metadata={},
                    actor_user_id=principal.user_id,
                    session_id=principal.session_id,
                    device_id=principal.device_id,
                )
                await session.commit()
            return state

    async def list_audit(self, principal: SessionPrincipal, limit: int) -> list[SecurityAuditRecord]:
        await self.require(principal, Permission.ADMIN)
        async with self._session_factory() as session:
            return await self._repository.list_audit_events(session, limit=limit)

    async def require_vault_management(self, principal: SessionPrincipal) -> None:
        await self.require(principal, Permission.ADMIN)
        async with self._session_factory() as session:
            if (await self._state(session)).lockdown is LockdownState.LOCKED_DOWN:
                raise SecurityAuthorizationError("Lockdown is active")

    async def _owned_device(self, session: AsyncSession, principal: SessionPrincipal, device_id: str) -> DeviceRecord:
        device = await self._repository.get_device(session, device_id)
        if device is None or device.user_id != principal.user_id:
            raise KeyError(device_id)
        return device

    async def _state(self, session: AsyncSession) -> SecurityStateRecord:
        state = await self._repository.get_state(session)
        return state if state is not None else await self._repository.create_state(session)
