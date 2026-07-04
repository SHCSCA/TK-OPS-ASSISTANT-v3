from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from common.time import utc_now
from common.http_errors import RuntimeHTTPException
from domain.models import Base, Project, RenderTask, Timeline
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.render_repository import RenderRepository
from repositories.timeline_repository import TimelineRepository
from schemas.renders import (
    ExportProfileCreateInput,
    RenderResourceUsageDto,
    RenderTaskCreateInput,
    RenderTaskUpdateInput,
)
from services.render_service import RenderService


class _FakeMinimalRenderer:
    def __init__(self, *, fail: bool = False, skip_output: bool = False) -> None:
        self.fail = fail
        self.skip_output = skip_output
        self.calls: list[dict[str, object]] = []

    def render_minimal_mp4(
        self,
        *,
        output_path: Path,
        project_id: str | None,
        project_name: str | None,
        preset: str,
        format: str,
    ) -> SimpleNamespace:
        self.calls.append(
            {
                "output_path": output_path,
                "project_id": project_id,
                "project_name": project_name,
                "preset": preset,
                "format": format,
            }
        )
        if self.fail:
            return SimpleNamespace(
                output_path=None,
                error_code="media.ffmpeg_unavailable",
                error_message="FFmpeg 未安装或未配置到可执行路径。",
            )
        if not self.skip_output:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"minimal-render-output")
        return SimpleNamespace(output_path=output_path, error_code=None, error_message=None)


class _FailingTimelineRepository:
    def get_by_id(self, timeline_id: str) -> Timeline | None:
        raise RuntimeError(f"timeline lookup failed: {timeline_id}")


def _make_render_service(
    tmp_path: Path,
    *,
    renderer: _FakeMinimalRenderer | None = None,
) -> RenderService:
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
        session.add(
            Timeline(
                id="timeline-render",
                project_id="project-render",
                name="主时间线",
                status="draft",
                duration_seconds=12,
                tracks_json="[]",
                source="test",
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
        )
        session.commit()

    return RenderService(
        RenderRepository(session_factory=session_factory),
        timeline_repository=TimelineRepository(session_factory=session_factory),
        export_root=tmp_path / "exports",
        renderer=renderer or _FakeMinimalRenderer(),
    )


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
    assert usage.disk.path == str(tmp_path / "exports")
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


def test_update_task_broadcasts_render_error_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_render_service(tmp_path)
    captured: list[dict[str, object]] = []

    async def _capture(message: dict[str, object]) -> None:
        captured.append(message)

    monkeypatch.setattr("services.render_service.ws_manager.broadcast", _capture)

    service.update_task(
        "render-task-1",
        RenderTaskUpdateInput(
            status="failed",
            error_code="media.ffmpeg_failed",
            error_message="渲染失败",
        ),
    )

    status_event = captured[-1]
    assert status_event["type"] == "render.status.changed"
    assert status_event["errorCode"] == "media.ffmpeg_failed"
    assert status_event["failure"]["error_code"] == "media.ffmpeg_failed"


def test_create_task_runs_minimal_renderer_and_writes_output_file(tmp_path: Path) -> None:
    renderer = _FakeMinimalRenderer()
    service = _make_render_service(tmp_path, renderer=renderer)

    task = service.create_task(
        RenderTaskCreateInput(
            project_id="project-render",
            project_name="渲染测试项目",
            timeline_id="timeline-render",
            preset="1080p",
            format="mp4",
        )
    )

    assert task.timeline_id == "timeline-render"
    assert task.status == "completed"
    assert task.progress == 100
    assert task.started_at is not None
    assert task.finished_at is not None
    assert task.output.path is not None
    assert Path(task.output.path).exists()
    assert task.output.size_bytes == len(b"minimal-render-output")
    assert task.failure.error_code is None
    assert len(renderer.calls) == 1
    assert renderer.calls[0]["project_id"] == "project-render"
    assert Path(str(renderer.calls[0]["output_path"])).parent.parent == tmp_path / "exports"


def test_create_task_rejects_timeline_from_other_project(tmp_path: Path) -> None:
    renderer = _FakeMinimalRenderer()
    service = _make_render_service(tmp_path, renderer=renderer)

    with pytest.raises(RuntimeHTTPException) as exc_info:
        service.create_task(
            RenderTaskCreateInput(
                project_id="project-other",
                project_name="错误项目",
                timeline_id="timeline-render",
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "render.timeline_project_mismatch"
    assert renderer.calls == []


def test_create_task_logs_timeline_lookup_failure(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    renderer = _FakeMinimalRenderer()
    service = RenderService(
        RenderRepository(session_factory=session_factory),
        timeline_repository=_FailingTimelineRepository(),  # type: ignore[arg-type]
        export_root=tmp_path / "exports",
        renderer=renderer,
    )

    with caplog.at_level(logging.ERROR, logger="services.render_service"):
        with pytest.raises(HTTPException) as exc_info:
            service.create_task(
                RenderTaskCreateInput(
                    project_id="project-render",
                    project_name="渲染测试项目",
                    timeline_id="timeline-render",
                )
            )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "渲染任务时间线校验失败"
    assert renderer.calls == []
    assert "渲染任务时间线校验失败" in caplog.text


def test_create_task_records_structured_failure_when_renderer_unavailable(
    tmp_path: Path,
) -> None:
    service = _make_render_service(tmp_path, renderer=_FakeMinimalRenderer(fail=True))

    task = service.create_task(
        RenderTaskCreateInput(
            project_id="project-render",
            project_name="渲染测试项目",
        )
    )

    assert task.status == "failed"
    assert task.progress == 0
    assert task.output.exists is False
    assert task.failure.error_code == "media.ffmpeg_unavailable"
    assert task.failure.error_message == "FFmpeg 未安装或未配置到可执行路径。"
    assert task.failure.retryable is True


def test_create_task_marks_failed_when_renderer_returns_missing_output(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path, renderer=_FakeMinimalRenderer(skip_output=True))

    task = service.create_task(RenderTaskCreateInput(project_id="project-render"))

    assert task.status == "failed"
    assert task.failure.error_code == "render.output_not_found"
    assert task.failure.retryable is True


def test_retry_task_reruns_minimal_renderer_and_clears_failure(tmp_path: Path) -> None:
    renderer = _FakeMinimalRenderer()
    service = _make_render_service(tmp_path, renderer=renderer)
    service.update_task(
        "render-task-1",
        RenderTaskUpdateInput(
            status="failed",
            progress=60,
            error_code="media.ffmpeg_unavailable",
            error_message="失败",
        ),
    )

    retried = service.retry_task("render-task-1")

    assert retried.status == "completed"
    assert retried.progress == 100
    assert retried.output.exists is True
    assert retried.error_code is None
    assert retried.error_message is None
    assert retried.failure.error_code is None
    assert len(renderer.calls) == 1


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


def test_task_detail_reports_inaccessible_output_file_as_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_render_service(tmp_path)
    output_file = tmp_path / "blocked-output.mp4"
    original_exists = Path.exists
    original_stat = Path.stat

    def fake_exists(path: Path) -> bool:
        if path == output_file:
            return True
        return original_exists(path)

    def fake_stat(path: Path):
        if path == output_file:
            raise OSError("permission denied")
        return original_stat(path)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "stat", fake_stat)

    task = service.update_task(
        "render-task-1",
        RenderTaskUpdateInput(
            status="completed",
            progress=100,
            output_path=str(output_file),
        ),
    )

    assert task.output.exists is False
    assert task.output.can_open is False
    assert task.failure.error_code == "render.output_not_found"


def test_task_detail_reports_completed_without_output_path_as_failure(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path)

    task = service.update_task(
        "render-task-1",
        RenderTaskUpdateInput(status="completed", progress=100, output_path=None),
    )

    assert task.output.path is None
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


def test_cancel_task_returns_cancelled_result_for_rendering_task(tmp_path: Path) -> None:
    service = _make_render_service(tmp_path)

    cancelled = service.cancel_task("render-task-1")
    task = service.get_task("render-task-1")

    assert cancelled.status == "cancelled"
    assert cancelled.message == "渲染任务已取消。"
    assert task.failure.error_code == "render.task_cancelled"


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
