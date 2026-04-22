from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import Base
from domain.models.account import Account
from domain.models.publishing import PublishPlan
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.account_repository import AccountRepository
from repositories.dashboard_repository import DashboardRepository
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from repositories.publishing_repository import PublishingRepository
from repositories.review_repository import ReviewRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from schemas.publishing import PublishPlanCreateInput
from schemas.review import ReviewSummaryUpdateInput
from services.publishing_service import PublishingService
from services.review_service import ReviewService


def _make_publishing_service(tmp_path: Path) -> PublishingService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    return PublishingService(
        PublishingRepository(session_factory=session_factory),
        account_repository=AccountRepository(session_factory=session_factory),
        device_workspace_repository=DeviceWorkspaceRepository(session_factory=session_factory),
    )



def _prepare_ready_publish_account(
    tmp_path: Path,
    service: PublishingService,
) -> tuple[str, str]:
    assert service._account_repository is not None
    assert service._device_workspace_repository is not None

    now = utc_now_iso()
    account_id = str(uuid4())
    service._account_repository.create_account(
        Account(
            id=account_id,
            name="发布账号",
            platform="tiktok",
            username="publisher_ready",
            avatar_url=None,
            status="active",
            auth_expires_at=None,
            follower_count=None,
            following_count=None,
            video_count=None,
            tags=None,
            notes=None,
            last_validated_at=now,
            created_at=now,
            updated_at=now,
        )
    )

    workspace_root = tmp_path / "publish-workspace"
    workspace_root.mkdir()
    workspace = service._device_workspace_repository.create_workspace(
        name="发布工作区",
        root_path=str(workspace_root),
    )
    service._device_workspace_repository.update_workspace(workspace.id, status="ready")
    service._device_workspace_repository.upsert_binding(
        account_id=account_id,
        browser_instance_id=workspace.id,
        status="active",
        source="manual",
    )
    return account_id, str(workspace_root)



def _make_review_service(
    tmp_path: Path,
) -> tuple[
    ReviewService,
    DashboardRepository,
    ScriptRepository,
    StoryboardRepository,
    PublishingRepository,
]:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    dashboard_repository = DashboardRepository(session_factory=session_factory)
    script_repository = ScriptRepository(session_factory=session_factory)
    storyboard_repository = StoryboardRepository(session_factory=session_factory)
    review_repository = ReviewRepository(session_factory=session_factory)
    publishing_repository = PublishingRepository(session_factory=session_factory)
    service = ReviewService(
        review_repository,
        dashboard_repository=dashboard_repository,
        script_repository=script_repository,
        storyboard_repository=storyboard_repository,
        publishing_repository=publishing_repository,
    )
    return (
        service,
        dashboard_repository,
        script_repository,
        storyboard_repository,
        publishing_repository,
    )



def test_publishing_receipt_history_and_calendar_conflicts(tmp_path: Path) -> None:
    service = _make_publishing_service(tmp_path)
    ready_account_id, _ = _prepare_ready_publish_account(tmp_path, service)

    scheduled_at = datetime(2026, 4, 17, 8, 30, tzinfo=timezone.utc)
    first = service.create_plan(
        PublishPlanCreateInput(
            title="首发计划 A",
            account_id=ready_account_id,
            project_id="project-1",
            video_asset_id="asset-1",
            scheduled_at=scheduled_at,
        )
    )
    service.create_plan(
        PublishPlanCreateInput(
            title="冲突计划 B",
            account_id=ready_account_id,
            project_id="project-2",
            video_asset_id="asset-2",
            scheduled_at=scheduled_at,
        )
    )

    precheck = service.precheck(first.id)
    assert precheck.has_errors is True
    assert len(precheck.conflicts) == 1
    assert precheck.conflicts[0].conflicting_plan_id is not None
    assert precheck.readiness.can_submit is False

    with pytest.raises(HTTPException):
        service.submit(first.id)

    clean_plan = service.create_plan(
        PublishPlanCreateInput(
            title="首发计划 C",
            account_id=ready_account_id,
            project_id="project-3",
            video_asset_id="asset-3",
            scheduled_at=datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc),
        )
    )

    first_submit = service.submit(clean_plan.id)
    second_submit = service.submit(clean_plan.id)
    assert first_submit.plan_id == clean_plan.id
    assert second_submit.plan_id == clean_plan.id

    receipts = service.list_receipts(clean_plan.id)
    assert len(receipts) == 2
    latest = service.get_latest_receipt(clean_plan.id)
    assert latest.id == receipts[0].id
    assert latest.status == "receipt_pending"

    calendar = service.get_calendar()
    assert len(calendar.items) >= 1
    assert any(item.conflict_count >= 1 for item in calendar.items)



def test_publishing_plan_summary_includes_readiness_and_receipt(tmp_path: Path) -> None:
    service = _make_publishing_service(tmp_path)
    ready_account_id, _ = _prepare_ready_publish_account(tmp_path, service)

    plan = service.create_plan(
        PublishPlanCreateInput(
            title="发布计划摘要",
            account_id=ready_account_id,
            project_id="project-ready",
            video_asset_id="asset-ready",
            scheduled_at=datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc),
        )
    )

    precheck = service.precheck(plan.id)
    assert precheck.has_errors is False
    assert precheck.readiness.can_submit is True
    assert precheck.blocking_count == 0

    submitted = service.submit(plan.id)
    assert submitted.receipt_status == "receipt_pending"
    assert submitted.receipt is not None
    assert submitted.receipt.summary == "已提交平台，等待平台回执。"

    refreshed = service.get_plan(plan.id)
    assert refreshed.publish_readiness.can_submit is True
    assert refreshed.precheck_summary.status == "ready"
    assert refreshed.latest_receipt is not None
    assert refreshed.latest_receipt.status == "receipt_pending"
    assert refreshed.recovery.can_cancel is True



def test_publishing_precheck_blocks_when_workspace_missing(tmp_path: Path) -> None:
    service = _make_publishing_service(tmp_path)
    ready_account_id, workspace_root = _prepare_ready_publish_account(tmp_path, service)
    Path(workspace_root).rmdir()

    plan = service.create_plan(
        PublishPlanCreateInput(
            title="工作区缺失发布计划",
            account_id=ready_account_id,
            project_id="project-blocked",
            video_asset_id="asset-blocked",
            scheduled_at=datetime(2026, 4, 17, 11, 0, tzinfo=timezone.utc),
        )
    )

    precheck = service.precheck(plan.id)
    assert precheck.has_errors is True
    device_item = next(item for item in precheck.items if item.code == "device_binding")
    assert device_item.error_code == "publishing.device_binding_required"
    assert precheck.readiness.can_submit is False
    assert precheck.readiness.error_code == "publishing.device_binding_required"

    with pytest.raises(HTTPException) as exc_info:
        service.submit(plan.id)
    assert exc_info.value.status_code == 409



def test_review_analyze_uses_project_version_and_publish_plan_context(tmp_path: Path) -> None:
    service, dashboard_repository, script_repository, _storyboard_repository, publishing_repository = (
        _make_review_service(tmp_path)
    )

    source_project = dashboard_repository.create_project(
        name="复盘源项目",
        description="用于验证 review analyze 上下文",
    )
    script_repository.save_version(
        source_project.id,
        source="user",
        content="第一版脚本\n先写出主题\n再补结尾",
    )
    script_repository.save_version(
        source_project.id,
        source="ai",
        content="第二版脚本\n前三秒先抛结论\n中段补充论据\n结尾明确 CTA",
        provider="openai",
        model="gpt-4.1-mini",
    )
    dashboard_repository.update_project_versions(
        source_project.id,
        current_script_version=2,
        current_storyboard_version=0,
    )
    service.update_summary(
        source_project.id,
        ReviewSummaryUpdateInput(
            project_name=source_project.name,
            total_views=1800,
            total_likes=30,
            total_comments=7,
            avg_watch_time_sec=6.2,
            completion_rate=0.24,
        ),
    )
    plan = publishing_repository.create_plan(
        PublishPlan(
            title="第二轮发布计划",
            project_id=source_project.id,
            status="submitted",
            scheduled_at=datetime(2026, 4, 18, 10, 0, tzinfo=timezone.utc),
        )
    )
    publishing_repository.create_receipt(
        plan_id=plan.id,
        status="receipt_pending",
        platform_response_json=json.dumps(
            {
                "stage": "receipt",
                "summary": "平台已接收，等待平台确认。",
                "errorCode": None,
                "errorMessage": None,
                "isFinal": False,
            },
            ensure_ascii=False,
        ),
    )

    result = service.analyze(source_project.id)
    summary = service.get_summary(source_project.id)

    assert result.status == "done"
    assert source_project.name in result.message
    assert source_project.name in summary.review_summary
    assert summary.latest_execution_result is not None
    assert summary.latest_execution_result.plan_id == plan.id
    assert summary.latest_execution_result.status == "receipt_pending"
    assert summary.latest_execution_result.summary == "平台已接收，等待平台确认。"
    assert any(item.target_type == "script_version" for item in summary.feedback_targets)
    assert any(item.target_type == "publishing_plan" for item in summary.feedback_targets)
    assert any(item.category == "脚本留存" for item in summary.issue_categories)
    assert any(
        "脚本第 2 版" in suggestion.description or "第二轮发布计划" in suggestion.description
        for suggestion in summary.suggestions
    )



def test_review_adopt_creates_child_project_and_copies_context(tmp_path: Path) -> None:
    service, dashboard_repository, script_repository, storyboard_repository, _publishing_repository = (
        _make_review_service(tmp_path)
    )

    source_project = dashboard_repository.create_project(
        name="源项目",
        description="用于验证 review adopt",
    )
    script_repository.save_version(
        source_project.id,
        source="user",
        content="第一版脚本",
    )
    script_repository.save_version(
        source_project.id,
        source="ai",
        content="第二版脚本",
    )
    storyboard_repository.save_version(
        source_project.id,
        based_on_script_revision=2,
        source="user",
        scenes=[{"title": "开场", "duration": "3s"}],
    )
    storyboard_repository.save_version(
        source_project.id,
        based_on_script_revision=2,
        source="ai",
        scenes=[{"title": "开场优化", "duration": "3s"}],
    )

    service.analyze(source_project.id)
    summary = service.get_summary(source_project.id)
    suggestion_id = summary.suggestions[0].id

    adopted_project = service.adopt_suggestion(suggestion_id)
    assert adopted_project.id != source_project.id
    assert adopted_project.name != source_project.name

    child_scripts = script_repository.list_versions(adopted_project.id)
    child_storyboards = storyboard_repository.list_versions(adopted_project.id)
    assert child_scripts[0].content == "第二版脚本"
    assert child_storyboards[0].scenes[0]["title"] == "开场优化"

    source_summary = service.get_summary(source_project.id)
    adopted = next(item for item in source_summary.suggestions if item.id == suggestion_id)
    assert adopted.adopted is True
    assert adopted.adopted_as_project_id == adopted_project.id
    assert adopted.adopted_at is not None



def test_review_apply_to_script_updates_original_project_only(tmp_path: Path) -> None:
    service, dashboard_repository, script_repository, _storyboard_repository, _publishing_repository = (
        _make_review_service(tmp_path)
    )

    source_project = dashboard_repository.create_project(
        name="原项目",
        description="用于验证 apply-to-script",
    )
    script_repository.save_version(
        source_project.id,
        source="user",
        content="第一版脚本",
    )
    script_repository.save_version(
        source_project.id,
        source="ai",
        content="第二版脚本",
    )

    service.analyze(source_project.id)
    summary = service.get_summary(source_project.id)
    suggestion = summary.suggestions[0]

    result = service.apply_suggestion_to_script(suggestion.id)

    assert result.projectId == source_project.id
    assert result.suggestionId == suggestion.id
    assert result.status == "已应用"
    assert "复盘建议" in result.message
    assert result.currentScriptVersion == 3
    assert "复盘建议" in result.scriptVersion.content
    assert "第二版脚本" in result.scriptVersion.content

    projects = dashboard_repository.list_recent_projects()
    assert len(projects) == 1
    assert projects[0].id == source_project.id
    assert projects[0].current_script_version == 3

    versions = script_repository.list_versions(source_project.id)
    assert len(versions) == 3
    assert versions[0].revision == 3
    assert versions[0].content == result.scriptVersion.content
    assert versions[0].content != versions[1].content

    refreshed_summary = service.get_summary(source_project.id)
    applied = next(item for item in refreshed_summary.suggestions if item.id == suggestion.id)
    assert applied.adopted is True
    assert applied.adopted_as_project_id is None
    assert applied.adopted_at is not None
