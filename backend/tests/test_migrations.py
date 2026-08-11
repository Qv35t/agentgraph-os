import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from agentgraph.settings import Settings

from .conftest import upgrade_database


def test_alembic_upgrade_created_backend_tables(database_path: Path, settings: Settings) -> None:
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert {"agents", "agent_runs", "alembic_version"}.issubset(tables)
    with sqlite3.connect(database_path) as connection:
        run_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)")}
    assert {"provider_id", "model_id", "total_tokens", "latency_ms"}.issubset(run_columns)


def test_phase2_data_survives_model_metadata_migration(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    upgrade_database(database_url, "20260811_0001")
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO agents "
            "(id, name, status, model_ref, graph_definition, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("legacy", "Legacy", "idle", "local/default", "{}", now, now),
        )
    upgrade_database(database_url)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT model_ref FROM agents WHERE id='legacy'").fetchone() == ("local/default",)
