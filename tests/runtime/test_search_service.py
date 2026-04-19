from __future__ import annotations

from pathlib import Path

from domain.models import (
    Account,
    Asset,
    AutomationTask,
    Base,
    DeviceWorkspace,
    Project,
    RenderTask,
    ScriptVersion,
)
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.dashboard_repository import DashboardRepository
from repositories.script_repository import ScriptRepository
from common.time import utc_now, utc_now_iso
from services.search_service import SearchService


def _make_search_service(tmp_path: Path) -> SearchService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    dashboard_repository = DashboardRepository(session_factory=session_factory)
    script_repository = ScriptRepository(session_factory=session_factory)

    now = utc_now()
    project = dashboard_repository.create_project(
        name="Alpha 项目",
        description="Alpha 描述",
    )
    script_repository.save_version(
        project.id,
        source="ai",
        content="Alpha Hook\nAlpha 片段说明",
        provider="openai",
        model="gpt-5",
    )

    with session_factory() as session:
        session.add(
            Asset(
                id="asset-alpha",
                name="Alpha 资产",
                type="video",
                source="local",
                group_id=None,
                file_path=None,
                file_size_bytes=None,
                duration_ms=None,
                thumbnail_path="/tmp/alpha-thumb.png",
                thumbnail_generated_at=utc_now_iso(),
                tags="alpha,creator",
                project_id=project.id,
                metadata_json=None,
                created_at=utc_now_iso(),
                updated_at=utc_now_iso(),
            )
        )
        session.add(
            Account(
                id="account-alpha",
                name="Alpha Creator",
                platform="tiktok",
                username="alpha_creator",
                avatar_url=None,
                status="active",
                auth_expires_at=None,
                follower_count=1024,
                following_count=128,
                video_count=36,
                tags="alpha",
                notes=None,
                created_at=utc_now_iso(),
                updated_at=utc_now_iso(),
            )
        )
        session.add(
            DeviceWorkspace(
                id="workspace-alpha",
                name="Alpha Workspace",
                root_path="D:/tkops/alpha",
                status="online",
                error_count=0,
                last_used_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            RenderTask(
                id="render-alpha",
                project_id=project.id,
                project_name="Alpha 项目",
                preset="1080p",
                format="mp4",
                status="queued",
                progress=10,
                output_path=None,
                error_message=None,
                started_at=None,
                finished_at=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            AutomationTask(
                id="automation-alpha",
                name="Alpha 自动化任务",
                type="sync_status",
                enabled=True,
                cron_expr=None,
                last_run_at=None,
                last_run_status="queued",
                run_count=0,
                config_json=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    return SearchService(
        session_factory=session_factory,
    )


def test_search_service_aggregates_supported_buckets(tmp_path: Path) -> None:
    service = _make_search_service(tmp_path)

    result = service.search("Alpha", limit=5)

    assert result.projects
    assert result.scripts
    assert result.tasks
    assert result.assets
    assert result.accounts
    assert result.workspaces
    assert set(result.projects[0].model_dump()) == {"id", "name", "subtitle", "updatedAt"}
    assert set(result.scripts[0].model_dump()) == {
        "id",
        "projectId",
        "title",
        "snippet",
        "updatedAt",
    }
    assert set(result.tasks[0].model_dump()) == {"id", "kind", "label", "status", "updatedAt"}
    assert set(result.assets[0].model_dump()) == {
        "id",
        "name",
        "type",
        "thumbnailUrl",
        "updatedAt",
    }
    assert set(result.accounts[0].model_dump()) == {"id", "name", "status"}
    assert set(result.workspaces[0].model_dump()) == {"id", "name", "status"}


def test_search_service_respects_requested_types(tmp_path: Path) -> None:
    service = _make_search_service(tmp_path)

    result = service.search("Alpha", types=["projects", "assets"], limit=3)

    assert result.projects
    assert result.assets
    assert result.scripts == []
    assert result.tasks == []
    assert result.accounts == []
    assert result.workspaces == []
