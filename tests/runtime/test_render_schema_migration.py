from __future__ import annotations

from sqlalchemy import text

from persistence.engine import (
    create_runtime_engine,
    create_session_factory,
    initialize_domain_schema,
)
from repositories.account_repository import AccountRepository
from repositories.automation_repository import AutomationRepository
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from repositories.render_repository import RenderRepository
from repositories.publishing_repository import PublishingRepository


def test_initialize_domain_schema_repair_render_tasks_legacy_columns(tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine = create_runtime_engine(tmp_path / "runtime.db")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id TEXT PRIMARY KEY)"))
        connection.execute(text("INSERT INTO projects (id) VALUES ('project-render')"))
        connection.execute(
            text(
                """
                CREATE TABLE render_tasks (
                    id VARCHAR NOT NULL,
                    project_id VARCHAR NOT NULL,
                    timeline_id VARCHAR,
                    status VARCHAR NOT NULL,
                    output_path TEXT,
                    profile_json TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    source VARCHAR NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (id),
                    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO render_tasks (
                    id,
                    project_id,
                    timeline_id,
                    status,
                    output_path,
                    profile_json,
                    progress,
                    source,
                    error_message,
                    created_at,
                    updated_at
                )
                VALUES (
                    'legacy-task',
                    'project-render',
                    'timeline-old',
                    'running',
                    NULL,
                    '{"stages":[]}',
                    12,
                    'local',
                    'legacy-error',
                    '2026-04-20 10:00:00',
                    '2026-04-20 10:00:00'
                )
                """
            )
        )

    initialize_domain_schema(engine)

    with engine.connect() as connection:
        columns = {
            row["name"] for row in connection.execute(
                text("PRAGMA table_info(render_tasks)")
            ).mappings().all()
        }

    assert {"project_name", "preset", "format", "started_at", "finished_at"} <= columns

    # 使用修复后的表结构再调用 list_tasks，确保不会再抛出 OperationalError
    repository = RenderRepository(session_factory=create_session_factory(engine))
    tasks = repository.list_tasks()
    assert len(tasks) == 1
    assert tasks[0].id == "legacy-task"
    assert tasks[0].preset == "1080p"
    assert tasks[0].format == "mp4"
    assert tasks[0].project_name is None
    assert tasks[0].error_message == "legacy-error"


def test_initialize_domain_schema_repair_publish_plans_legacy_timestamps(tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine = create_runtime_engine(tmp_path / "runtime.db")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id TEXT PRIMARY KEY)"))
        connection.execute(text("INSERT INTO projects (id) VALUES ('project-publish')"))
        connection.execute(
            text(
                """
                CREATE TABLE publish_plans (
                    id VARCHAR NOT NULL,
                    project_id VARCHAR NOT NULL,
                    account_id VARCHAR NOT NULL,
                    binding_id VARCHAR,
                    status VARCHAR NOT NULL,
                    scheduled_at TEXT,
                    caption TEXT NOT NULL,
                    source VARCHAR NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (id),
                    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO publish_plans (
                    id,
                    project_id,
                    account_id,
                    binding_id,
                    status,
                    scheduled_at,
                    caption,
                    source,
                    metadata_json,
                    created_at
                )
                VALUES (
                    'legacy-plan',
                    'project-publish',
                    'account-publish',
                    'binding-publish',
                    'scheduled',
                    '',
                    'caption',
                    'local',
                    '{\"hashtags\": []}',
                    '2026-04-20 10:00:00'
                )
                """
            )
        )

    initialize_domain_schema(engine)

    repository = PublishingRepository(session_factory=create_session_factory(engine))
    plans = repository.list_plans()

    assert len(plans) == 1
    assert plans[0].id == "legacy-plan"
    assert plans[0].status == "scheduled"


def test_initialize_domain_schema_repair_accounts_and_device_workspaces_and_automation_tasks(tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine = create_runtime_engine(tmp_path / "runtime.db")
    session_factory = create_session_factory(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE accounts (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    username TEXT,
                    avatar_url TEXT,
                    status TEXT NOT NULL,
                    auth_expires_at TEXT,
                    follower_count INTEGER,
                    following_count INTEGER,
                    video_count INTEGER,
                    tags TEXT,
                    notes TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO accounts (
                    id,
                    platform,
                    username,
                    avatar_url,
                    status,
                    auth_expires_at,
                    follower_count,
                    following_count,
                    video_count,
                    tags,
                    notes
                )
                VALUES (
                    'account-legacy',
                    'tiktok',
                    'legacy_user',
                    NULL,
                    'active',
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL
                )
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE TABLE projects (id TEXT PRIMARY KEY)
                """
            )
        )
        connection.execute(text("INSERT INTO projects (id) VALUES ('project-legacy')"))
        connection.execute(
            text(
                """
                CREATE TABLE device_workspaces (
                    id VARCHAR PRIMARY KEY,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    status VARCHAR NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_used_at TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO device_workspaces (
                    id,
                    name,
                    root_path,
                    status,
                    created_at,
                    updated_at,
                    last_used_at
                )
                VALUES (
                    'workspace-legacy',
                    'legacy-workspace',
                    '/tmp/legacy',
                    'offline',
                    '2026-04-20 10:00:00',
                    '2026-04-20 10:00:00',
                    NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE automation_tasks (
                    id VARCHAR PRIMARY KEY,
                    type VARCHAR NOT NULL,
                    enabled INTEGER NOT NULL,
                    cron_expr TEXT,
                    last_run_at TEXT,
                    last_run_status TEXT,
                    run_count INTEGER NOT NULL,
                    config_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO automation_tasks (
                    id,
                    type,
                    enabled,
                    cron_expr,
                    last_run_at,
                    last_run_status,
                    run_count,
                    config_json,
                    created_at,
                    updated_at
                )
                VALUES (
                    'task-legacy',
                    'legacy-type',
                    1,
                    NULL,
                    NULL,
                    NULL,
                    0,
                    NULL,
                    '2026-04-20 10:00:00',
                    '2026-04-20 10:00:00'
                )
                """
            )
        )

    initialize_domain_schema(engine)

    account_columns = _table_columns(engine, "accounts")
    workspace_columns = _table_columns(engine, "device_workspaces")
    automation_columns = _table_columns(engine, "automation_tasks")

    assert {"name", "created_at", "updated_at"} <= account_columns
    assert "error_count" in workspace_columns
    assert "name" in automation_columns

    account_repository = AccountRepository(session_factory=session_factory)
    device_workspace_repository = DeviceWorkspaceRepository(session_factory=session_factory)
    automation_repository = AutomationRepository(session_factory=session_factory)

    accounts = account_repository.list_accounts()
    workspaces = device_workspace_repository.list_workspaces()
    tasks = automation_repository.list_tasks()

    assert len(accounts) == 1
    assert accounts[0].id == "account-legacy"
    assert len(workspaces) == 1
    assert workspaces[0].id == "workspace-legacy"
    assert len(tasks) == 1
    assert tasks[0].id == "task-legacy"


def _table_columns(engine, table_name: str) -> set[str]:  # type: ignore[no-untyped-def]
    with engine.connect() as connection:
        rows = connection.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    return {str(row["name"]) for row in rows}
