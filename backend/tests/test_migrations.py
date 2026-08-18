import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config

from agentgraph.settings import Settings
from alembic import command

from .conftest import BACKEND_ROOT, upgrade_database


def test_alembic_upgrade_created_backend_tables(database_path: Path, settings: Settings) -> None:
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    expected_tables = {
        "agents",
        "agent_runs",
        "memory_records",
        "run_memory_records",
        "tool_invocations",
        "run_delegations",
        "nodes",
        "run_checkpoints",
        "run_action_ledger_entries",
        "run_recovery_decisions",
        "alembic_version",
    }
    assert expected_tables.issubset(tables)
    with sqlite3.connect(database_path) as connection:
        run_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)")}
    assert {"provider_id", "model_id", "total_tokens", "latency_ms", "execution_spec"}.issubset(run_columns)
    with sqlite3.connect(database_path) as connection:
        node_columns = {row[1] for row in connection.execute("PRAGMA table_info(nodes)")}
    assert {"id", "status", "enrollment_hash", "capabilities", "last_seen_at"}.issubset(node_columns)


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


def test_phase5_database_upgrades_and_downgrades_phase6_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "phase5.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    upgrade_database(database_url, "20260812_0003")
    with sqlite3.connect(database_path) as connection:
        before = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "vision_assets" in before
    assert "memory_records" not in before

    upgrade_database(database_url)
    with sqlite3.connect(database_path) as connection:
        upgraded = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"memory_records", "run_memory_records", "tool_invocations"}.issubset(upgraded)

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "20260812_0003")
    with sqlite3.connect(database_path) as connection:
        downgraded = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "vision_assets" in downgraded
    assert "memory_records" not in downgraded

    upgrade_database(database_url)
    with sqlite3.connect(database_path) as connection:
        reupgraded = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"memory_records", "run_memory_records", "tool_invocations"}.issubset(reupgraded)


def test_phase6_database_upgrades_and_downgrades_phase7_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "phase6.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    upgrade_database(database_url, "20260815_0004")
    with sqlite3.connect(database_path) as connection:
        before = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "run_delegations" not in before

    upgrade_database(database_url)
    with sqlite3.connect(database_path) as connection:
        upgraded = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "run_delegations" in upgraded

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "20260815_0004")
    with sqlite3.connect(database_path) as connection:
        downgraded = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "run_delegations" not in downgraded

    upgrade_database(database_url)
    with sqlite3.connect(database_path) as connection:
        reupgraded = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "run_delegations" in reupgraded


def test_phase8_database_upgrades_and_downgrades_phase9_node_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "phase8.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    upgrade_database(database_url, "20260816_0005")
    upgrade_database(database_url)
    with sqlite3.connect(database_path) as connection:
        assert "nodes" in {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "20260816_0005")
    with sqlite3.connect(database_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "nodes" not in tables


def test_phase9_database_upgrades_and_downgrades_phase10_recovery_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "phase9.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    upgrade_database(database_url, "20260817_0006")
    upgrade_database(database_url)
    with sqlite3.connect(database_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        run_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)")}
    assert {"run_checkpoints", "run_action_ledger_entries", "run_recovery_decisions"}.issubset(tables)
    assert "execution_spec" in run_columns

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "20260817_0006")
    with sqlite3.connect(database_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "run_checkpoints" not in tables


def test_phase10_database_upgrades_and_downgrades_phase11_security_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "phase10.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    upgrade_database(database_url, "20260817_0007")
    upgrade_database(database_url)
    expected_tables = {
        "users",
        "security_devices",
        "auth_sessions",
        "passkey_credentials",
        "auth_challenges",
        "second_factors",
        "security_approvals",
        "security_grants",
        "vault_credentials",
        "security_audit_events",
        "security_state",
    }
    expected_indexes = {
        "ix_security_devices_user_id",
        "ix_auth_sessions_user_id",
        "ix_auth_sessions_device_id",
        "ix_auth_sessions_expires_at",
        "ix_passkey_credentials_user_id",
        "ix_passkey_credentials_device_id",
        "ix_auth_challenges_user_id",
        "ix_security_approvals_status_expires_at",
        "ix_security_grants_subject_action_target_run_task_expires_at",
        "ix_security_audit_events_event_type",
        "ix_security_audit_events_created_at",
    }
    with sqlite3.connect(database_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        indexes = {
            row[0]
            for table in expected_tables
            for row in connection.execute(f"SELECT name FROM pragma_index_list('{table}')")
        }
    assert expected_tables.issubset(tables)
    assert expected_indexes.issubset(indexes)

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "20260817_0007")
    with sqlite3.connect(database_path) as connection:
        downgraded = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert not expected_tables & downgraded
    assert {"run_checkpoints", "run_action_ledger_entries", "run_recovery_decisions"}.issubset(downgraded)

    upgrade_database(database_url)
    with sqlite3.connect(database_path) as connection:
        reupgraded = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert expected_tables.issubset(reupgraded)
