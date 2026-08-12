from collections.abc import Generator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient

from agentgraph.app import create_app
from agentgraph.models.router import DisabledProvider, ModelRouter
from agentgraph.runtime.graph import DeterministicGraphRuntime
from agentgraph.settings import Settings
from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def upgrade_database(database_url: str, revision: str = "head") -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, revision)


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
        yield test_client
