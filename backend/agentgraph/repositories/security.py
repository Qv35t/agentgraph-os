from datetime import datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from agentgraph.domain.security import (
    AuthenticationStrength,
    ChallengeKind,
    DeviceTrust,
    GrantStatus,
    LockdownState,
    SecurityApprovalDecision,
    UserRole,
)
from agentgraph.persistence.models import (
    AuthChallengeRecord,
    DeviceRecord,
    GrantRecord,
    PasskeyCredentialRecord,
    SecondFactorRecord,
    SecurityApprovalRecord,
    SecurityAuditRecord,
    SecurityStateRecord,
    SessionRecord,
    UserRecord,
    VaultCredentialRecord,
)


class SecurityRepository:
    async def create_user(self, session: AsyncSession, *, username: str, role: UserRole) -> UserRecord:
        record = UserRecord(username=username, role=role)
        session.add(record)
        await session.flush()
        return record

    async def get_user(self, session: AsyncSession, user_id: str) -> UserRecord | None:
        return await session.get(UserRecord, user_id)

    async def get_user_by_username(self, session: AsyncSession, username: str) -> UserRecord | None:
        return cast(UserRecord | None, await session.scalar(select(UserRecord).where(UserRecord.username == username)))

    async def list_users(self, session: AsyncSession) -> list[UserRecord]:
        return list(await session.scalars(select(UserRecord).order_by(UserRecord.created_at)))

    async def disable_user(self, session: AsyncSession, record: UserRecord, disabled_at: datetime) -> None:
        record.disabled_at = disabled_at
        await session.flush()

    async def create_device(
        self, session: AsyncSession, *, user_id: str, display_name: str, trust: DeviceTrust
    ) -> DeviceRecord:
        record = DeviceRecord(user_id=user_id, display_name=display_name, trust=trust)
        session.add(record)
        await session.flush()
        return record

    async def get_device(self, session: AsyncSession, device_id: str) -> DeviceRecord | None:
        return await session.get(DeviceRecord, device_id)

    async def list_devices_for_user(self, session: AsyncSession, user_id: str) -> list[DeviceRecord]:
        return list(
            await session.scalars(
                select(DeviceRecord).where(DeviceRecord.user_id == user_id).order_by(DeviceRecord.created_at.desc())
            )
        )

    async def update_device(
        self,
        session: AsyncSession,
        record: DeviceRecord,
        *,
        display_name: str | None = None,
        trust: DeviceTrust | None = None,
        revoked_at: datetime | None = None,
        last_authenticated_at: datetime | None = None,
    ) -> None:
        if display_name is not None:
            record.display_name = display_name
        if trust is not None:
            record.trust = trust
        if revoked_at is not None:
            record.revoked_at = revoked_at
        if last_authenticated_at is not None:
            record.last_authenticated_at = last_authenticated_at
        await session.flush()

    async def create_session(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        device_id: str,
        token_hash: str,
        strength: AuthenticationStrength,
        expires_at: datetime,
    ) -> SessionRecord:
        record = SessionRecord(
            user_id=user_id,
            device_id=device_id,
            token_hash=token_hash,
            strength=strength,
            expires_at=expires_at,
        )
        session.add(record)
        await session.flush()
        return record

    async def get_session(self, session: AsyncSession, session_id: str) -> SessionRecord | None:
        return await session.get(SessionRecord, session_id)

    async def get_session_by_token_hash(self, session: AsyncSession, token_hash: str) -> SessionRecord | None:
        return cast(
            SessionRecord | None,
            await session.scalar(select(SessionRecord).where(SessionRecord.token_hash == token_hash)),
        )

    async def list_sessions_for_user(self, session: AsyncSession, user_id: str) -> list[SessionRecord]:
        return list(
            await session.scalars(
                select(SessionRecord).where(SessionRecord.user_id == user_id).order_by(SessionRecord.created_at.desc())
            )
        )

    async def revoke_sessions_for_device(self, session: AsyncSession, device_id: str, revoked_at: datetime) -> None:
        await session.execute(
            update(SessionRecord)
            .where(SessionRecord.device_id == device_id, SessionRecord.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        await session.flush()

    async def update_session(
        self,
        session: AsyncSession,
        record: SessionRecord,
        *,
        last_activity_at: datetime | None = None,
        step_up_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        if last_activity_at is not None:
            record.last_activity_at = last_activity_at
        if step_up_at is not None:
            record.step_up_at = step_up_at
        if revoked_at is not None:
            record.revoked_at = revoked_at
        await session.flush()

    async def create_passkey_credential(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        device_id: str,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int = 0,
    ) -> PasskeyCredentialRecord:
        record = PasskeyCredentialRecord(
            user_id=user_id,
            device_id=device_id,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=sign_count,
        )
        session.add(record)
        await session.flush()
        return record

    async def get_passkey_credential(
        self, session: AsyncSession, credential_id: bytes
    ) -> PasskeyCredentialRecord | None:
        return cast(
            PasskeyCredentialRecord | None,
            await session.scalar(
                select(PasskeyCredentialRecord).where(PasskeyCredentialRecord.credential_id == credential_id)
            ),
        )

    async def list_passkey_credentials_for_user(
        self, session: AsyncSession, user_id: str
    ) -> list[PasskeyCredentialRecord]:
        return list(
            await session.scalars(
                select(PasskeyCredentialRecord)
                .where(PasskeyCredentialRecord.user_id == user_id)
                .order_by(PasskeyCredentialRecord.created_at.desc())
            )
        )

    async def update_passkey_credential(
        self,
        session: AsyncSession,
        record: PasskeyCredentialRecord,
        *,
        sign_count: int | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        if sign_count is not None:
            record.sign_count = sign_count
        if revoked_at is not None:
            record.revoked_at = revoked_at
        await session.flush()

    async def create_challenge(
        self,
        session: AsyncSession,
        *,
        kind: ChallengeKind,
        challenge: bytes,
        expires_at: datetime,
        user_id: str | None = None,
        device_name: str | None = None,
    ) -> AuthChallengeRecord:
        record = AuthChallengeRecord(
            kind=kind,
            challenge=challenge,
            user_id=user_id,
            device_name=device_name,
            expires_at=expires_at,
        )
        session.add(record)
        await session.flush()
        return record

    async def get_challenge(self, session: AsyncSession, challenge_id: str) -> AuthChallengeRecord | None:
        return await session.get(AuthChallengeRecord, challenge_id)

    async def consume_challenge(self, session: AsyncSession, challenge_id: str, consumed_at: datetime) -> bool:
        result = await session.execute(
            update(AuthChallengeRecord)
            .where(
                AuthChallengeRecord.id == challenge_id,
                AuthChallengeRecord.consumed_at.is_(None),
                AuthChallengeRecord.expires_at > consumed_at,
            )
            .values(consumed_at=consumed_at)
        )
        await session.flush()
        return cast(CursorResult[object], result).rowcount == 1

    async def get_second_factor(self, session: AsyncSession, user_id: str) -> SecondFactorRecord | None:
        return await session.get(SecondFactorRecord, user_id)

    async def upsert_second_factor(
        self, session: AsyncSession, *, user_id: str, encrypted_secret: bytes, key_version: int
    ) -> SecondFactorRecord:
        record = await self.get_second_factor(session, user_id)
        if record is None:
            record = SecondFactorRecord(user_id=user_id, encrypted_secret=encrypted_secret, key_version=key_version)
            session.add(record)
        else:
            record.encrypted_secret = encrypted_secret
            record.key_version = key_version
            record.revoked_at = None
        await session.flush()
        return record

    async def revoke_second_factor(
        self, session: AsyncSession, record: SecondFactorRecord, revoked_at: datetime
    ) -> None:
        record.revoked_at = revoked_at
        await session.flush()

    async def create_approval(
        self,
        session: AsyncSession,
        *,
        project_id: str,
        requested_by: str,
        action: str,
        reason: str,
        scope: dict[str, object],
        expires_at: datetime,
        target: str | None = None,
        run_id: str | None = None,
        task_ref: str | None = None,
        risk: str | None = None,
    ) -> SecurityApprovalRecord:
        record = SecurityApprovalRecord(
            project_id=project_id,
            requested_by=requested_by,
            action=action,
            reason=reason,
            scope=scope,
            expires_at=expires_at,
            target=target,
            run_id=run_id,
            task_ref=task_ref,
            risk=risk,
        )
        session.add(record)
        await session.flush()
        return record

    async def get_approval(self, session: AsyncSession, approval_id: str) -> SecurityApprovalRecord | None:
        return await session.get(SecurityApprovalRecord, approval_id)

    async def list_approvals(self, session: AsyncSession, *, status: str | None = None) -> list[SecurityApprovalRecord]:
        statement = select(SecurityApprovalRecord).order_by(SecurityApprovalRecord.created_at.desc())
        if status is not None:
            statement = statement.where(SecurityApprovalRecord.status == status)
        return list(await session.scalars(statement))

    async def decide_approval(
        self,
        session: AsyncSession,
        *,
        approval_id: str,
        decision: SecurityApprovalDecision,
        decided_by_user_id: str,
        decided_at: datetime,
        status: str,
    ) -> bool:
        result = await session.execute(
            update(SecurityApprovalRecord)
            .where(SecurityApprovalRecord.id == approval_id, SecurityApprovalRecord.status == "pending")
            .values(
                decision=decision,
                decided_by_user_id=decided_by_user_id,
                decided_at=decided_at,
                status=status,
            )
        )
        await session.flush()
        return cast(CursorResult[object], result).rowcount == 1

    async def create_grant(
        self,
        session: AsyncSession,
        *,
        issuer_user_id: str,
        subject: str,
        action: str,
        expires_at: datetime,
        target: str | None = None,
        run_id: str | None = None,
        task_ref: str | None = None,
        device_id: str | None = None,
        source_approval_id: str | None = None,
    ) -> GrantRecord:
        record = GrantRecord(
            issuer_user_id=issuer_user_id,
            subject=subject,
            action=action,
            expires_at=expires_at,
            target=target,
            run_id=run_id,
            task_ref=task_ref,
            device_id=device_id,
            source_approval_id=source_approval_id,
        )
        session.add(record)
        await session.flush()
        return record

    async def get_grant(self, session: AsyncSession, grant_id: str) -> GrantRecord | None:
        return await session.get(GrantRecord, grant_id)

    async def list_grants(self, session: AsyncSession, *, subject: str | None = None) -> list[GrantRecord]:
        statement = select(GrantRecord).order_by(GrantRecord.created_at.desc())
        if subject is not None:
            statement = statement.where(GrantRecord.subject == subject)
        return list(await session.scalars(statement))

    async def revoke_grant(
        self,
        session: AsyncSession,
        record: GrantRecord,
        revoked_at: datetime,
        status: GrantStatus = GrantStatus.REVOKED,
    ) -> None:
        record.status = status
        record.revoked_at = revoked_at
        await session.flush()

    async def create_audit_event(
        self,
        session: AsyncSession,
        *,
        event_type: str,
        result: str,
        metadata: dict[str, object],
        actor_user_id: str | None = None,
        session_id: str | None = None,
        device_id: str | None = None,
        target: str | None = None,
    ) -> SecurityAuditRecord:
        record = SecurityAuditRecord(
            event_type=event_type,
            result=result,
            metadata_json=metadata,
            actor_user_id=actor_user_id,
            session_id=session_id,
            device_id=device_id,
            target=target,
        )
        session.add(record)
        await session.flush()
        return record

    async def list_audit_events(self, session: AsyncSession, *, limit: int = 100) -> list[SecurityAuditRecord]:
        return list(
            await session.scalars(
                select(SecurityAuditRecord).order_by(SecurityAuditRecord.created_at.desc()).limit(limit)
            )
        )

    async def get_state(self, session: AsyncSession) -> SecurityStateRecord | None:
        return await session.get(SecurityStateRecord, 1)

    async def create_state(self, session: AsyncSession) -> SecurityStateRecord:
        record = SecurityStateRecord(id=1)
        session.add(record)
        await session.flush()
        return record

    async def update_state(self, session: AsyncSession, record: SecurityStateRecord, lockdown: LockdownState) -> None:
        record.lockdown = lockdown
        await session.flush()

    async def create_vault_credential(
        self,
        session: AsyncSession,
        *,
        name: str,
        credential_type: str,
        encrypted_value: bytes,
        key_version: int,
        created_by_user_id: str,
    ) -> VaultCredentialRecord:
        record = VaultCredentialRecord(
            name=name,
            credential_type=credential_type,
            encrypted_value=encrypted_value,
            key_version=key_version,
            created_by_user_id=created_by_user_id,
        )
        session.add(record)
        await session.flush()
        return record

    async def get_vault_credential(self, session: AsyncSession, credential_id: str) -> VaultCredentialRecord | None:
        return await session.get(VaultCredentialRecord, credential_id)

    async def list_vault_credentials(self, session: AsyncSession) -> list[VaultCredentialRecord]:
        return list(
            await session.scalars(select(VaultCredentialRecord).order_by(VaultCredentialRecord.created_at.desc()))
        )

    async def update_vault_credential(
        self,
        session: AsyncSession,
        record: VaultCredentialRecord,
        *,
        encrypted_value: bytes | None = None,
        key_version: int | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        if encrypted_value is not None:
            record.encrypted_value = encrypted_value
        if key_version is not None:
            record.key_version = key_version
        if revoked_at is not None:
            record.revoked_at = revoked_at
        await session.flush()
