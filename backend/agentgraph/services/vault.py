import hashlib
import hmac
import os
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import VaultCredentialRecord
from agentgraph.repositories.security import SecurityRepository
from agentgraph.settings import Settings


class VaultError(Exception):
    pass


class MasterKeyStore:
    """Owns the local Fernet key; it is never represented in persistence or APIs."""

    def __init__(self, key_path: str) -> None:
        self._path = Path(key_path)
        self._fernet: Fernet | None = None

    def fernet(self) -> Fernet:
        if self._fernet is None:
            self._fernet = Fernet(self._load_or_create())
        return self._fernet

    def csrf_token(self, session_id: str) -> str:
        key = self._load_or_create()
        return hmac.new(key, session_id.encode("utf-8"), hashlib.sha256).hexdigest()

    def _load_or_create(self) -> bytes:
        parent = self._path.parent
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(parent, 0o700)
        try:
            descriptor = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            os.chmod(self._path, 0o600)
            key = self._path.read_bytes()
        else:
            key = Fernet.generate_key()
            try:
                os.write(descriptor, key)
            finally:
                os.close(descriptor)
        try:
            Fernet(key)
        except ValueError as error:
            raise VaultError("The local security master key is invalid") from error
        return key


class VaultService:
    def __init__(
        self, session_factory: SessionFactory, settings: Settings, key_store: MasterKeyStore | None = None
    ) -> None:
        self._session_factory = session_factory
        self._repository = SecurityRepository()
        self._key_store = key_store or MasterKeyStore(settings.security_master_key_path)

    async def create(
        self, *, owner_user_id: str, name: str, credential_type: str, secret: str
    ) -> VaultCredentialRecord:
        if not secret:
            raise VaultError("Credential value is required")
        encrypted_value = self._key_store.fernet().encrypt(secret.encode("utf-8"))
        async with self._session_factory() as session:
            record = await self._repository.create_vault_credential(
                session,
                name=name,
                credential_type=credential_type,
                encrypted_value=encrypted_value,
                key_version=1,
                created_by_user_id=owner_user_id,
            )
            await session.commit()
            return record

    async def list_metadata(self) -> list[VaultCredentialRecord]:
        async with self._session_factory() as session:
            return await self._repository.list_vault_credentials(session)

    async def replace(self, *, credential_id: str, secret: str) -> VaultCredentialRecord:
        if not secret:
            raise VaultError("Credential value is required")
        async with self._session_factory() as session:
            record = await self._repository.get_vault_credential(session, credential_id)
            if record is None or record.revoked_at is not None:
                raise VaultError("Credential was not found")
            await self._repository.update_vault_credential(
                session,
                record,
                encrypted_value=self._key_store.fernet().encrypt(secret.encode("utf-8")),
                key_version=1,
            )
            await session.commit()
            return record

    async def revoke(self, credential_id: str) -> VaultCredentialRecord:
        async with self._session_factory() as session:
            record = await self._repository.get_vault_credential(session, credential_id)
            if record is None or record.revoked_at is not None:
                raise VaultError("Credential was not found")
            await self._repository.update_vault_credential(session, record, revoked_at=datetime.now(UTC))
            await session.commit()
            return record

    def _decrypt_for_broker(self, record: VaultCredentialRecord) -> str:
        """Private to the future broker boundary; no API or agent contract exposes this."""
        try:
            return self._key_store.fernet().decrypt(record.encrypted_value).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError) as error:
            raise VaultError("Credential cannot be decrypted") from error
