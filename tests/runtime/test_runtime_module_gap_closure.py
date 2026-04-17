from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

from common.time import utc_now
from domain.models import Account, Base, ImportedVideo
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.account_repository import AccountRepository
from repositories.automation_repository import AutomationRepository
from repositories.dashboard_repository import DashboardRepository
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from repositories.imported_video_repository import ImportedVideoRepository
from repositories.publishing_repository import PublishingRepository
from repositories.render_repository import RenderRepository
from repositories.review_repository import ReviewRepository
from repositories.script_repository import ScriptRepository
from repositories.video_deconstruction_repository import VideoDeconstructionRepository
from schemas.automation import AutomationTaskCreateInput
from schemas.device_workspaces import (
    BrowserInstanceCreateInput,
    DeviceWorkspaceCreateInput,
    ExecutionBindingCreateInput,
)
from schemas.publishing import PublishPlanCreateInput
from schemas.renders import RenderTaskCreateInput, RenderTaskUpdateInput
from services.automation_service import AutomationService
from services.dashboard_service import DashboardService
from services.device_workspace_service import DeviceWorkspaceService
from services.publishing_service import PublishingService
from services.render_service import RenderService
from services.review_service import ReviewService
from services.video_deconstruction_service import VideoDeconstructionService


def _make_session_factory(tmp_path: Path):
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)


def _create_project(dashboard_repository: DashboardRepository) -> str:
    return dashboard_repository.create_project(name="Gap Project", description="").id


def _create_account(session_factory) -> str:
    repository = AccountRepository(session_factory=session_factory)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    account = Account(
        id="account-1",
        name="Creator A",
        platform="tiktok",
        username="creator_a",
        avatar_url=None,
        status="active",
        auth_expires_at=None,
        follower_count=None,
        following_count=None,
        video_count=None,
        tags=None,
        notes=None,
        created_at=now,
        updated_at=now,
    )
    return repository.create_account(account).id


def _create_imported_video(
    repository: ImportedVideoRepository,
    *,
    project_id: str,
    video_id: str = "video-1",
) -> str:
    video = ImportedVideo(
        id=video_id,
        project_id=project_id,
        file_path="D:/videos/demo.mp4",
        file_name="demo.mp4",
        file_size_bytes=1024,
        duration_seconds=45.0,
        width=1080,
        height=1920,
        frame_rate=30.0,
        codec="h264",
        status="ready",
        error_message=None,
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    return repository.create(video).id


def test_device_workspace_service_blocks_bound_browser_instance_delete(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    _create_account(session_factory)
    service = DeviceWorkspaceService(DeviceWorkspaceRepository(session_factory=session_factory))

    workspace = service.create_workspace(
        DeviceWorkspaceCreateInput(name="Main", root_path=str(tmp_path / "workspace"))
    )
    instance = service.create_browser_instance(
        BrowserInstanceCreateInput(
            workspace_id=workspace.id,
            name="Chrome Main",
            profile_path=str(tmp_path / "profiles" / "chrome-main"),
            browser_type="chrome",
        )
    )
    service.create_binding(
        ExecutionBindingCreateInput(
            account_id="account-1",
            device_workspace_id=workspace.id,
            browser_instance_id=instance.id,
            source="publish",
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        service.delete_browser_instance(instance.id)

    assert exc_info.value.status_code == 409


def test_automation_service_cancel_run_updates_run_and_logs(tmp_path: Path) -> None:
    service = AutomationService(AutomationRepository(session_factory=_make_session_factory(tmp_path)))

    task = service.create_task(AutomationTaskCreateInput(name="同步状态", type="sync"))
    trigger = service.trigger_task(task.id)

    logs = service.get_run_logs(trigger.run_id)
    assert logs.lines

    cancelled = service.cancel_run(trigger.run_id)
    assert cancelled.status == "cancelled"
    assert "取消" in (cancelled.log_text or "")


def test_publishing_service_submit_creates_receipt(tmp_path: Path) -> None:
    service = PublishingService(PublishingRepository(session_factory=_make_session_factory(tmp_path)))

    plan = service.create_plan(PublishPlanCreateInput(title="发布计划"))
    service.precheck(plan.id)
    submit_result = service.submit(plan.id)
    receipt = service.get_receipt(plan.id)

    assert submit_result.status == "submitted"
    assert receipt.plan_id == plan.id
    assert receipt.status == "manual_required"


def test_render_service_retry_resets_failed_task(tmp_path: Path) -> None:
    service = RenderService(RenderRepository(session_factory=_make_session_factory(tmp_path)))

    task = service.create_task(RenderTaskCreateInput(project_id="project-1", preset="1080p"))
    service.update_task(
        task.id,
        RenderTaskUpdateInput(status="failed", progress=100, error_message="编码失败"),
    )

    retried = service.retry_task(task.id)

    assert retried.status == "queued"
    assert retried.progress == 0
    assert retried.error_message is None


def test_review_service_apply_suggestion_creates_script_revision(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    dashboard_repository = DashboardRepository(session_factory=session_factory)
    dashboard_service = DashboardService(dashboard_repository)
    project_id = _create_project(dashboard_repository)
    service = ReviewService(
        ReviewRepository(session_factory=session_factory),
        dashboard_service,
        ScriptRepository(session_factory=session_factory),
    )

    generated = service.generate_suggestions(project_id)
    suggestions = service.get_suggestions(project_id)
    applied = service.apply_suggestion_to_script(suggestions[0].id)

    assert generated.generated_count >= 1
    assert applied.project_id == project_id
    assert applied.script_revision == 1


def test_video_deconstruction_service_extracts_and_applies_ready_structure(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    dashboard_repository = DashboardRepository(session_factory=session_factory)
    dashboard_service = DashboardService(dashboard_repository)
    project_id = _create_project(dashboard_repository)
    imported_video_repository = ImportedVideoRepository(session_factory=session_factory)
    video_id = _create_imported_video(imported_video_repository, project_id=project_id)
    repository = VideoDeconstructionRepository(session_factory=session_factory)
    service = VideoDeconstructionService(
        imported_video_repository=imported_video_repository,
        repository=repository,
        dashboard_service=dashboard_service,
        script_repository=ScriptRepository(session_factory=session_factory),
    )

    service.start_transcription(video_id)
    transcript = repository.get_transcript(video_id)
    assert transcript is not None
    transcript.text = "这是拆解后得到的结构化文案。"
    transcript.status = "ready"
    transcript.updated_at = utc_now()
    repository.save_transcript(transcript)

    service.run_segmentation(video_id)
    extraction = service.extract_structure(video_id)
    applied = service.apply_to_project(extraction.id)

    assert extraction.status == "ready"
    assert applied.projectId == project_id
    assert applied.scriptRevision == 1
