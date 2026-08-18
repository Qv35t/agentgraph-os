import base64
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyotp
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import options_to_json
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import PublicKeyCredentialDescriptor

from agentgraph.domain.remote import Permission
from agentgraph.domain.security import AuthenticationStrength, ChallengeKind, DeviceTrust, UserRole
from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import AuthChallengeRecord, UserRecord
from agentgraph.repositories.security import SecurityRepository
from agentgraph.services.vault import MasterKeyStore
from agentgraph.settings import Settings


class AuthenticationError(Exception):
    pass


class AuthenticationConflictError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class SessionPrincipal:
    user_id: str
    username: str
    role: UserRole
    session_id: str
    device_id: str
    device_trust: DeviceTrust
    authentication_strength: AuthenticationStrength
    permissions: frozenset[Permission]
    csrf_token: str


@dataclass(frozen=True, slots=True)
class SessionTokens:
    session_token: str
    csrf_token: str
    principal: SessionPrincipal


class AuthService:
    def __init__(
        self, session_factory: SessionFactory, settings: Settings, key_store: MasterKeyStore | None = None
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._repository = SecurityRepository()
        self._key_store = key_store or MasterKeyStore(settings.security_master_key_path)

    async def bootstrap(self, *, username: str, bootstrap_secret: str, device_name: str) -> dict[str, object]:
        self._require_bootstrap_secret(bootstrap_secret)
        async with self._session_factory() as session:
            if await self._repository.list_users(session):
                raise AuthenticationConflictError("Bootstrap is no longer available")
            user = await self._repository.create_user(session, username=username, role=UserRole.OWNER)
            challenge, options = await self._create_registration_challenge(session, user, device_name)
            await self._repository.create_audit_event(
                session,
                event_type="security.bootstrap",
                result="success",
                metadata={"username": username},
                actor_user_id=user.id,
            )
            await session.commit()
        self._consume_bootstrap_secret()
        return {"challenge_id": challenge.id, "options": options}

    async def begin_passkey_registration(self, principal: SessionPrincipal, device_name: str) -> dict[str, object]:
        async with self._session_factory() as session:
            user = await self._repository.get_user(session, principal.user_id)
            if user is None or user.disabled_at is not None:
                raise AuthenticationError("User is unavailable")
            challenge, options = await self._create_registration_challenge(session, user, device_name)
            await session.commit()
            return {"challenge_id": challenge.id, "options": options}

    async def finish_passkey_registration(self, *, challenge_id: str, credential: dict[str, object]) -> SessionTokens:
        async with self._session_factory() as session:
            challenge = await self._registration_challenge(session, challenge_id)
            try:
                verification = verify_registration_response(
                    credential=credential,
                    expected_challenge=challenge.challenge,
                    expected_rp_id=self._settings.webauthn_rp_id,
                    expected_origin=self._settings.webauthn_allowed_origins,
                    require_user_verification=True,
                )
            except InvalidRegistrationResponse as error:
                raise AuthenticationError("Passkey registration verification failed") from error
            if not await self._repository.consume_challenge(session, challenge.id, datetime.now(UTC)):
                raise AuthenticationConflictError("Passkey challenge is no longer valid")
            user = await self._repository.get_user(session, challenge.user_id or "")
            if user is None:
                raise AuthenticationError("User is unavailable")
            device = await self._repository.create_device(
                session,
                user_id=user.id,
                display_name=challenge.device_name or "Passkey device",
                trust=DeviceTrust.LIMITED,
            )
            await self._repository.create_passkey_credential(
                session,
                user_id=user.id,
                device_id=device.id,
                credential_id=verification.credential_id,
                public_key=verification.credential_public_key,
                sign_count=verification.sign_count,
            )
            tokens = await self._create_session(session, user, device.id, AuthenticationStrength.PASSKEY)
            await self._repository.create_audit_event(
                session,
                event_type="security.passkey_registered",
                result="success",
                metadata={},
                actor_user_id=user.id,
                session_id=tokens.principal.session_id,
                device_id=device.id,
            )
            await session.commit()
            return tokens

    async def begin_passkey_authentication(self, *, username: str) -> dict[str, object]:
        async with self._session_factory() as session:
            user = await self._repository.get_user_by_username(session, username)
            if user is None or user.disabled_at is not None:
                raise AuthenticationError("Authentication failed")
            credentials = [
                credential
                for credential in await self._repository.list_passkey_credentials_for_user(session, user.id)
                if credential.revoked_at is None
            ]
            if not credentials:
                raise AuthenticationError("Authentication failed")
            challenge_bytes = secrets.token_bytes(32)
            challenge = await self._repository.create_challenge(
                session,
                kind=ChallengeKind.PASSKEY_AUTHENTICATION,
                challenge=challenge_bytes,
                user_id=user.id,
                expires_at=datetime.now(UTC) + timedelta(seconds=self._settings.webauthn_challenge_ttl_seconds),
            )
            options = generate_authentication_options(
                rp_id=self._settings.webauthn_rp_id,
                challenge=challenge_bytes,
                allow_credentials=[PublicKeyCredentialDescriptor(id=item.credential_id) for item in credentials],
            )
            await session.commit()
            return {"challenge_id": challenge.id, "options": json.loads(options_to_json(options))}

    async def finish_passkey_authentication(self, *, challenge_id: str, credential: dict[str, object]) -> SessionTokens:
        async with self._session_factory() as session:
            challenge = await self._authentication_challenge(session, challenge_id)
            raw_id = credential.get("rawId")
            if not isinstance(raw_id, str):
                raise AuthenticationError("Authentication failed")
            credential_id = _base64url_decode(raw_id)
            passkey = await self._repository.get_passkey_credential(session, credential_id)
            if passkey is None or passkey.revoked_at is not None or passkey.user_id != challenge.user_id:
                raise AuthenticationError("Authentication failed")
            try:
                verification = verify_authentication_response(
                    credential=credential,
                    expected_challenge=challenge.challenge,
                    expected_rp_id=self._settings.webauthn_rp_id,
                    expected_origin=self._settings.webauthn_allowed_origins,
                    credential_public_key=passkey.public_key,
                    credential_current_sign_count=passkey.sign_count,
                    require_user_verification=True,
                )
            except InvalidAuthenticationResponse as error:
                raise AuthenticationError("Authentication failed") from error
            if not await self._repository.consume_challenge(session, challenge.id, datetime.now(UTC)):
                raise AuthenticationConflictError("Passkey challenge is no longer valid")
            user = await self._repository.get_user(session, passkey.user_id)
            device = await self._repository.get_device(session, passkey.device_id)
            if user is None or user.disabled_at is not None or device is None or device.revoked_at is not None:
                raise AuthenticationError("Authentication failed")
            await self._repository.update_passkey_credential(session, passkey, sign_count=verification.new_sign_count)
            await self._repository.update_device(session, device, last_authenticated_at=datetime.now(UTC))
            tokens = await self._create_session(session, user, device.id, AuthenticationStrength.PASSKEY)
            await self._repository.create_audit_event(
                session,
                event_type="security.login",
                result="success",
                metadata={},
                actor_user_id=user.id,
                session_id=tokens.principal.session_id,
                device_id=device.id,
            )
            await session.commit()
            return tokens

    async def principal_from_session_token(self, session_token: str | None) -> SessionPrincipal:
        if not session_token:
            raise AuthenticationError("Authentication is required")
        token_hash = _token_hash(session_token)
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            record = await self._repository.get_session_by_token_hash(session, token_hash)
            if record is None or record.revoked_at is not None or record.expires_at <= now:
                raise AuthenticationError("Session is invalid or expired")
            user = await self._repository.get_user(session, record.user_id)
            device = await self._repository.get_device(session, record.device_id)
            if user is None or user.disabled_at is not None or device is None or device.revoked_at is not None:
                raise AuthenticationError("Session is invalid or expired")
            strength = AuthenticationStrength.PASSKEY_TOTP if record.step_up_at is not None else record.strength
            return self._principal(user, record.id, device.id, device.trust, strength)

    async def logout(self, principal: SessionPrincipal) -> None:
        async with self._session_factory() as session:
            record = await self._repository.get_session(session, principal.session_id)
            if record is not None and record.revoked_at is None:
                await self._repository.update_session(session, record, revoked_at=datetime.now(UTC))
                await self._repository.create_audit_event(
                    session,
                    event_type="security.logout",
                    result="success",
                    metadata={},
                    actor_user_id=principal.user_id,
                    session_id=principal.session_id,
                    device_id=principal.device_id,
                )
                await session.commit()

    async def begin_totp_enrollment(self, principal: SessionPrincipal) -> dict[str, str]:
        secret = pyotp.random_base32()
        return {
            "secret": secret,
            "otpauth_uri": pyotp.TOTP(secret).provisioning_uri(
                name=principal.username, issuer_name=self._settings.totp_issuer
            ),
        }

    async def confirm_totp_enrollment(self, principal: SessionPrincipal, *, secret: str, code: str) -> None:
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            raise AuthenticationError("Invalid verification code")
        encrypted_secret = self._key_store.fernet().encrypt(secret.encode("ascii"))
        async with self._session_factory() as session:
            await self._repository.upsert_second_factor(
                session, user_id=principal.user_id, encrypted_secret=encrypted_secret, key_version=1
            )
            await self._repository.create_audit_event(
                session,
                event_type="security.totp_enrolled",
                result="success",
                metadata={},
                actor_user_id=principal.user_id,
                session_id=principal.session_id,
                device_id=principal.device_id,
            )
            await session.commit()

    async def verify_totp(self, principal: SessionPrincipal, code: str) -> SessionPrincipal:
        async with self._session_factory() as session:
            factor = await self._repository.get_second_factor(session, principal.user_id)
            if factor is None or factor.revoked_at is not None:
                raise AuthenticationError("Second factor is not enabled")
            try:
                secret = self._key_store.fernet().decrypt(factor.encrypted_secret).decode("ascii")
            except Exception as error:
                raise AuthenticationError("Second factor is unavailable") from error
            if not pyotp.TOTP(secret).verify(code, valid_window=1):
                await self._repository.create_audit_event(
                    session,
                    event_type="security.totp",
                    result="denied",
                    metadata={},
                    actor_user_id=principal.user_id,
                    session_id=principal.session_id,
                    device_id=principal.device_id,
                )
                await session.commit()
                raise AuthenticationError("Invalid verification code")
            record = await self._repository.get_session(session, principal.session_id)
            if record is None or record.revoked_at is not None:
                raise AuthenticationError("Session is invalid")
            await self._repository.update_session(session, record, step_up_at=datetime.now(UTC))
            await session.commit()
            return self._principal(
                await self._required_user(session, principal.user_id),
                record.id,
                record.device_id,
                principal.device_trust,
                AuthenticationStrength.PASSKEY_TOTP,
            )

    async def require_csrf(self, principal: SessionPrincipal, csrf_token: str | None, origin: str | None) -> None:
        if origin not in self._settings.webauthn_allowed_origins:
            raise AuthenticationError("Request origin is not allowed")
        if csrf_token is None or not hmac.compare_digest(csrf_token, principal.csrf_token):
            raise AuthenticationError("CSRF validation failed")

    async def _create_registration_challenge(
        self, session: AsyncSession, user: UserRecord, device_name: str
    ) -> tuple[AuthChallengeRecord, dict[str, object]]:
        # Kept private because the caller owns the concrete AsyncSession transaction.
        challenge_bytes = secrets.token_bytes(32)
        challenge = await self._repository.create_challenge(
            session,
            kind=ChallengeKind.PASSKEY_REGISTRATION,
            challenge=challenge_bytes,
            user_id=user.id,
            device_name=device_name,
            expires_at=datetime.now(UTC) + timedelta(seconds=self._settings.webauthn_challenge_ttl_seconds),
        )
        existing = await self._repository.list_passkey_credentials_for_user(session, user.id)
        options = generate_registration_options(
            rp_id=self._settings.webauthn_rp_id,
            rp_name=self._settings.webauthn_rp_name,
            user_name=user.username,
            user_id=user.id.encode("utf-8"),
            challenge=challenge_bytes,
            exclude_credentials=[PublicKeyCredentialDescriptor(id=item.credential_id) for item in existing],
        )
        return challenge, json.loads(options_to_json(options))

    async def _registration_challenge(self, session: AsyncSession, challenge_id: str) -> AuthChallengeRecord:
        challenge = await self._repository.get_challenge(session, challenge_id)
        if (
            challenge is None
            or challenge.kind is not ChallengeKind.PASSKEY_REGISTRATION
            or challenge.consumed_at is not None
            or challenge.expires_at <= datetime.now(UTC)
        ):
            raise AuthenticationError("Passkey challenge is invalid or expired")
        return challenge

    async def _authentication_challenge(self, session: AsyncSession, challenge_id: str) -> AuthChallengeRecord:
        challenge = await self._repository.get_challenge(session, challenge_id)
        if (
            challenge is None
            or challenge.kind is not ChallengeKind.PASSKEY_AUTHENTICATION
            or challenge.consumed_at is not None
            or challenge.expires_at <= datetime.now(UTC)
        ):
            raise AuthenticationError("Passkey challenge is invalid or expired")
        return challenge

    async def _create_session(
        self, session: AsyncSession, user: UserRecord, device_id: str, strength: AuthenticationStrength
    ) -> SessionTokens:
        session_token = secrets.token_urlsafe(32)
        record = await self._repository.create_session(
            session,
            user_id=user.id,
            device_id=device_id,
            token_hash=_token_hash(session_token),
            strength=strength,
            expires_at=datetime.now(UTC) + timedelta(seconds=self._settings.session_ttl_seconds),
        )
        device = await self._repository.get_device(session, device_id)
        if device is None:
            raise AuthenticationError("Device is unavailable")
        principal = self._principal(user, record.id, device_id, device.trust, strength)
        return SessionTokens(session_token=session_token, csrf_token=principal.csrf_token, principal=principal)

    async def _required_user(self, session: AsyncSession, user_id: str) -> UserRecord:
        user = await self._repository.get_user(session, user_id)
        if user is None:
            raise AuthenticationError("User is unavailable")
        return user

    def _principal(
        self,
        user: UserRecord,
        session_id: str,
        device_id: str,
        device_trust: DeviceTrust,
        authentication_strength: AuthenticationStrength,
    ) -> SessionPrincipal:
        return SessionPrincipal(
            user_id=user.id,
            username=user.username,
            role=user.role,
            session_id=session_id,
            device_id=device_id,
            device_trust=device_trust,
            authentication_strength=authentication_strength,
            permissions=_permissions_for_role(user.role),
            csrf_token=self._key_store.csrf_token(session_id),
        )

    def _require_bootstrap_secret(self, supplied: str) -> None:
        path = Path(self._settings.bootstrap_secret_path)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        if not path.exists():
            secret = secrets.token_urlsafe(32)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(descriptor, secret.encode("utf-8"))
            finally:
                os.close(descriptor)
        os.chmod(path, 0o600)
        expected = path.read_text(encoding="utf-8").strip()
        if not expected or not hmac.compare_digest(supplied, expected):
            raise AuthenticationError("Bootstrap secret is invalid")

    def _consume_bootstrap_secret(self) -> None:
        try:
            Path(self._settings.bootstrap_secret_path).unlink()
        except FileNotFoundError:
            pass


def _permissions_for_role(role: UserRole) -> frozenset[Permission]:
    if role in {UserRole.OWNER, UserRole.ADMIN}:
        return frozenset(Permission)
    return frozenset({Permission.READ, Permission.EXECUTE, Permission.CONTROL})


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _base64url_decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError as error:
        raise AuthenticationError("Authentication failed") from error
