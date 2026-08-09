from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domain.models import (
    DeviceWorkspace,
    DeviceWorkspaceLog,
    ExportProfile,
    PublishPlan,
    PublishReceipt,
)


REVISION_0014 = "0014_magic_cut_suggestion_drafts"
REVISION_0016 = "0016_p0_backfill"
REVISION_0017 = "0017_p0_enforce_and_cutover"
REVISION_0020 = "0020_p0e_ai_vertical_chain"
ACCOUNT_SCOPE_TRIGGERS = {
    "trg_knowledge_sources_account_base_insert",
    "trg_knowledge_sources_account_base_update",
    "trg_account_knowledge_bases_account_update",
}


def test_reconciled_defaults_support_real_orm_and_sql_inserts(tmp_path: Path) -> None:
    database_path = tmp_path / "defaults.db"
    command.upgrade(_config(database_path), "head")

    assert _column_default(database_path, "device_workspace_logs", "created_at") == (
        "CURRENT_TIMESTAMP"
    )
    assert _column_default(database_path, "export_profiles", "created_at") == (
        "CURRENT_TIMESTAMP"
    )
    assert _column_default(database_path, "export_profiles", "updated_at") == (
        "CURRENT_TIMESTAMP"
    )
    assert _column_default(database_path, "publish_receipts", "received_at") == (
        "CURRENT_TIMESTAMP"
    )
    assert _column_default(database_path, "publish_receipts", "created_at") == (
        "CURRENT_TIMESTAMP"
    )
    assert "datetime('now')" in _column_default(
        database_path, "voice_tracks", "updated_at"
    )
    assert "datetime('now')" in _column_default(
        database_path, "subtitle_tracks", "updated_at"
    )

    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    with Session(engine) as session:
        session.add(
            DeviceWorkspace(
                id="workspace-orm",
                name="ORM 工作区",
                root_path="C:/orm-workspace",
                status="offline",
                error_count=0,
            )
        )
        session.add(
            PublishPlan(id="plan-orm", title="ORM 发布计划", status="draft")
        )
        session.flush()
        session.add_all(
            [
                DeviceWorkspaceLog(
                    id="log-orm",
                    workspace_id="workspace-orm",
                    kind="diagnostic",
                    level="info",
                    message="真实 ORM 写入",
                ),
                ExportProfile(
                    id="export-orm",
                    name="ORM 导出配置",
                    format="mp4",
                    resolution="1080x1920",
                    fps=30,
                    video_bitrate="8000k",
                    audio_policy="merge_all",
                    subtitle_policy="burn_in",
                    is_default=False,
                ),
                PublishReceipt(
                    id="receipt-orm",
                    plan_id="plan-orm",
                    status="accepted",
                ),
            ]
        )
        session.commit()
    engine.dispose()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO projects (
                id, name, description, status, current_script_version,
                current_storyboard_version, created_at, updated_at, last_accessed_at
            ) VALUES ('project-sql', 'SQL 项目', '', 'active', 0, 0,
                      '2026-01-01', '2026-01-01', '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO voice_tracks (
                id, project_id, source, voice_name, segments_json, status, created_at
            ) VALUES ('voice-sql', 'project-sql', 'manual', '声音', '[]', 'draft',
                      '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO subtitle_tracks (
                id, project_id, source, language, style_json, segments_json,
                status, created_at
            ) VALUES ('subtitle-sql', 'project-sql', 'manual', 'zh-CN', '{}', '[]',
                      'draft', '2026-01-01')
            """
        )
        connection.commit()

    for table_name, column_name, row_id in (
        ("device_workspace_logs", "created_at", "log-orm"),
        ("export_profiles", "created_at", "export-orm"),
        ("export_profiles", "updated_at", "export-orm"),
        ("publish_receipts", "received_at", "receipt-orm"),
        ("publish_receipts", "created_at", "receipt-orm"),
        ("voice_tracks", "updated_at", "voice-sql"),
        ("subtitle_tracks", "updated_at", "subtitle-sql"),
    ):
        assert _scalar(
            database_path,
            f'SELECT "{column_name}" FROM "{table_name}" WHERE id = ?',
            (row_id,),
        ) not in (None, "")


def test_account_scope_constraints_reject_cross_account_writes(tmp_path: Path) -> None:
    database_path = tmp_path / "account-scope.db"
    command.upgrade(_config(database_path), "head")

    assert ACCOUNT_SCOPE_TRIGGERS.issubset(_trigger_names(database_path))
    with sqlite3.connect(database_path) as connection:
        for account_id in ("account-a", "account-b"):
            connection.execute(
                """
                INSERT INTO accounts (
                    id, name, platform, status, created_at, updated_at,
                    wizard_completed_at, revision
                ) VALUES (?, ?, 'tiktok', 'unbound', '2026-01-01', '2026-01-01',
                          '2026-01-01', 1)
                """,
                (account_id, account_id),
            )
            connection.execute(
                """
                INSERT INTO account_knowledge_bases (
                    id, account_id, status, rules_json, rules_version,
                    index_revision, revision, created_at, updated_at
                ) VALUES (?, ?, 'empty', '{}', 0, 0, 1, '2026-01-01', '2026-01-01')
                """,
                (f"base-{account_id}", account_id),
            )
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError, match="KNOWLEDGE_SOURCE_ACCOUNT_MISMATCH"):
            _insert_knowledge_source(
                connection,
                source_id="source-cross",
                account_id="account-b",
                knowledge_base_id="base-account-a",
            )

        _insert_knowledge_source(
            connection,
            source_id="source-valid",
            account_id="account-a",
            knowledge_base_id="base-account-a",
        )
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="KNOWLEDGE_SOURCE_ACCOUNT_MISMATCH"):
            connection.execute(
                "UPDATE knowledge_sources SET account_id = 'account-b' "
                "WHERE id = 'source-valid'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="KNOWLEDGE_BASE_ACCOUNT_MISMATCH"):
            connection.execute(
                "UPDATE account_knowledge_bases SET account_id = 'account-b' "
                "WHERE id = 'base-account-a'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="ck_runtime_events_account_topic"):
            _insert_runtime_event(
                connection,
                event_id="event-cross",
                topic="account:account-a:tasks",
                account_id="account-b",
            )

        _insert_runtime_event(
            connection,
            event_id="event-valid",
            topic="account:account-a:tasks",
            account_id="account-a",
        )
        connection.commit()


def test_account_scope_triggers_are_removed_and_recreated(tmp_path: Path) -> None:
    database_path = tmp_path / "trigger-round-trip.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    assert ACCOUNT_SCOPE_TRIGGERS.issubset(_trigger_names(database_path))

    command.downgrade(config, REVISION_0016)
    assert ACCOUNT_SCOPE_TRIGGERS.isdisjoint(_trigger_names(database_path))

    command.upgrade(config, REVISION_0017)
    assert ACCOUNT_SCOPE_TRIGGERS.issubset(_trigger_names(database_path))


def test_new_column_data_refuses_downgrade_without_changing_version_or_data(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "column-downgrade-refusal.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO projects (
                id, name, description, status, current_script_version,
                current_storyboard_version, created_at, updated_at, last_accessed_at,
                deleted_at
            ) VALUES ('project-deleted', '已删除项目', '', 'archived', 0, 0,
                      '2026-01-01', '2026-01-01', '2026-01-01', '2026-02-01')
            """
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="projects.deleted_at"):
        command.downgrade(config, REVISION_0014)

    assert _version(database_path) == REVISION_0020
    assert _scalar(
        database_path,
        "SELECT COUNT(*) FROM pragma_table_info('prompt_profiles') "
        "WHERE name = 'revision'",
        (),
    ) == 1
    assert _scalar(
        database_path,
        "SELECT COUNT(*) FROM pragma_table_info('account_ai_recipes') "
        "WHERE name = 'content_hash'",
        (),
    ) == 1
    assert _scalar(
        database_path,
        "SELECT deleted_at FROM projects WHERE id = ?",
        ("project-deleted",),
    ) == "2026-02-01"


def _insert_knowledge_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    account_id: str,
    knowledge_base_id: str,
) -> None:
    connection.execute(
        """
        INSERT INTO knowledge_sources (
            id, account_id, knowledge_base_id, kind, name, source_ref, status,
            metadata_json, revision, created_at, updated_at, source_mode
        ) VALUES (?, ?, ?, 'text', '来源', 'local:test', 'pending', '{}', 1,
                  '2026-01-01', '2026-01-01', 'text')
        """,
        (source_id, account_id, knowledge_base_id),
    )


def _insert_runtime_event(
    connection: sqlite3.Connection,
    *,
    event_id: str,
    topic: str,
    account_id: str,
) -> None:
    connection.execute(
        """
        INSERT INTO runtime_events (
            event_id, topic, sequence, event_type, account_id, payload_json, occurred_at
        ) VALUES (?, ?, 1, 'test.event', ?, '{}', '2026-01-01')
        """,
        (event_id, topic, account_id),
    )


def _config(database_path: Path) -> Config:
    runtime_root = Path(__file__).resolve().parents[2] / "apps" / "py-runtime"
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"
    return config


def _column_default(database_path: Path, table_name: str, column_name: str) -> str:
    with sqlite3.connect(database_path) as connection:
        columns = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    for column in columns:
        if str(column[1]) == column_name:
            return str(column[4] or "")
    raise AssertionError(f"字段不存在：{table_name}.{column_name}")


def _trigger_names(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def _version(database_path: Path) -> str:
    return str(
        _scalar(database_path, "SELECT version_num FROM alembic_version", ())
    )


def _scalar(
    database_path: Path,
    query: str,
    parameters: tuple[object, ...],
) -> object:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(query, parameters).fetchone()
    assert row is not None
    return row[0]
