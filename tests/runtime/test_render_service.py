from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from common.time import utc_now
from domain.models import Base, Project, RenderTask
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.render_repository import RenderRepository
from schemas.renders import (
    ExportProfileCreateInput,
    RenderResourceUsageDto,
    RenderTaskUpdateInput,
)
from services.render_service import RenderService


def _make_render_service(tmp_path: Path) -> RenderService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    now = utc_now()
    with session_factory() as session:
        session.add(
            Project(
                id="project-render",
                name="渲染测试项目",
                description="",
                status="active",
                current_script_version=0,
                current_storyboard_version=0,
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
                last_accessed_at=now.isoformat(),
            )
        )
        session.add(
            RenderTask(
                id="render-task-1",
                project_id="project-render",
                project_name="渲染测试项目",
                preset="1080p",
                format="mp4",
                status="rendering",
                progress=35,
                output_path=None,
                error_message=None,
                started_at=now,
                finished_at=None,
            )
        )
        session.commit()

    return RenderService(RenderRepository(session_factory=session_factory))


def test_list_templates_seeds_builtin_default_profile(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path)

    templates = service.list_templates()

    assert templates
    assert templates[0].is_default is True


def test_fetch_resource_usage_returns_real_disk_snapshot(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path)

    usage = service.fetch_resource_usage()

    assert isinstance(usage, RenderResourceUsageDto)
    assert usage.disk.status == "ready"
    assert usage.disk.usagePct is not None
    assert usage.gpu.status == "unavailable"


def test_update_task_broadcasts_render_progress_and_status_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_render_service(tmp_path)
    captured: list[dict[str, object]] = []

    async def _capture(message: dict[str, object]) -> None:
        captured.append(message)

    monkeypatch.setattr("services.render_service.ws_manager.broadcast", _capture)

    updated = service.update_task(
        "render-task-1",
        RenderTaskUpdateInput(status="rendering", progress=42),
    )

    assert updated.progress == 42
    assert len(captured) == 2
    assert captured[0]["type"] == "render.progress"
    assert captured[0]["taskId"] == "render-task-1"
    assert captured[1]["type"] == "render.status.changed"
    assert captured[1]["stage"]["code"] == "rendering"


def test_retry_task_keeps_existing_reset_semantics(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path)
    service.update_task(
        "render-task-1",
        RenderTaskUpdateInput(status="failed", progress=60, error_message="失败"),
    )

    retried = service.retry_task("render-task-1")

    assert retried.status == "queued"
    assert retried.progress == 0
    assert retried.error_message is None
    assert retried.failure.error_code is None


def test_task_detail_reports_existing_output_file(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path)
    output_file = tmp_path / "render-output.mp4"
    output_file.write_bytes(b"render-bytes")

    task = service.update_task(
        "render-task-1",
        RenderTaskUpdateInput(
            status="completed",
            progress=100,
            output_path=str(output_file),
        ),
    )

    assert task.stage.code == "completed"
    assert task.output.exists is True
    assert task.output.size_bytes == len(b"render-bytes")
    assert task.output.can_open is True
    assert task.failure.error_code is None


def test_task_detail_reports_missing_output_file_as_failure(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path)
    missing_output = tmp_path / "missing-output.mp4"

    task = service.update_task(
        "render-task-1",
        RenderTaskUpdateInput(
            status="completed",
            progress=100,
            output_path=str(missing_output),
        ),
    )

    assert task.output.exists is False
    assert task.failure.error_code == "render.output_not_found"
    assert task.failure.retryable is True


def test_cancel_task_returns_structured_conflict_when_not_cancellable(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path)
    service.update_task(
        "render-task-1",
        RenderTaskUpdateInput(status="completed", progress=100),
    )

    with pytest.raises(HTTPException) as exc_info:
        service.cancel_task("render-task-1")

    assert exc_info.value.status_code == 409
    assert getattr(exc_info.value, "error_code", None) == "render.task_not_cancellable"


def test_create_profile_rejects_empty_name(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path)

    with pytest.raises(HTTPException):
        service.create_profile(
            ExportProfileCreateInput(
                name="  ",
                format="mp4",
                resolution="1080x1920",
                fps=30,
                video_bitrate="8000k",
                audio_policy="merge_all",
                subtitle_policy="burn_in",
            )
        )
