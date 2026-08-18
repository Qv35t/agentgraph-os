import asyncio
import hashlib
import secrets
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from agentgraph.app import create_app
from agentgraph.domain.security import AuthenticationStrength, DeviceTrust, UserRole
from agentgraph.models.router import DisabledProvider, ModelRouter
from agentgraph.persistence.database import create_database_engine, create_session_factory
from agentgraph.persistence.models import DeviceRecord, SessionRecord, UserRecord
from agentgraph.runtime.graph import DeterministicGraphRuntime
from agentgraph.settings import Settings
from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def upgrade_database(database_url: str, revision: str = "head") -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, revision)


def seed_test_session(
    client: TestClient,
    settings: Settings,
    *,
    role: UserRole = UserRole.OWNER,
) -> str:
    """Seed a durable authenticated principal for an isolated TestClient database."""

    session_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()

    async def seed() -> None:
        engine = create_database_engine(settings.database_url)
        session_factory = create_session_factory(engine)
        try:
            async with session_factory() as session:
                user = UserRecord(username=f"test-{role.value}-{session_token[:8]}", role=role)
                session.add(user)
                await session.flush()
                device = DeviceRecord(user_id=user.id, display_name="Test device", trust=DeviceTrust.TRUSTED)
                session.add(device)
                await session.flush()
                expires_at = datetime.now(UTC) + timedelta(seconds=settings.session_ttl_seconds)
                session.add(
                    SessionRecord(
                        user_id=user.id,
                        device_id=device.id,
                        token_hash=token_hash,
                        strength=AuthenticationStrength.DEVELOPMENT,
                        expires_at=expires_at,
                    )
                )
                await session.flush()
                # SQLite's DateTime bind drops offsets; preserve UTC for AuthService expiry checks.
                await session.execute(
                    text("UPDATE auth_sessions SET expires_at = :expires_at WHERE token_hash = :token_hash"),
                    {"expires_at": expires_at.isoformat(), "token_hash": token_hash},
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(seed())
    client.cookies.set(settings.session_cookie_name, session_token)
    principal = asyncio.run(cast(Any, client).app.state.auth_service.principal_from_session_token(session_token))
    client.headers.update({"x-agentgraph-csrf": principal.csrf_token, "origin": settings.webauthn_allowed_origins[0]})
    return session_token


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "agentgraph.db"


@pytest.fixture
def database_url(database_path: Path) -> str:
    return f"sqlite+aiosqlite:///{database_path}"


@pytest.fixture
def settings(database_url: str) -> Settings:
    upgrade_database(database_url)
    return Settings(database_url=database_url, legacy_api_enabled=True)


@pytest.fixture
def client(settings: Settings) -> Generator[TestClient, None, None]:
    router = ModelRouter(
        {provider_id: DisabledProvider(provider_id) for provider_id in ("ollama", "opencode", "openrouter")},
        "ollama://qwen3-4b-nothink:latest",
    )
    with TestClient(
        create_app(settings.model_copy(update={"legacy_api_enabled": True}), DeterministicGraphRuntime(), router)
    ) as test_client:
        seed_test_session(test_client, settings)
        yield test_client
