from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.dashboard_repository import DashboardRepository
from repositories.publishing_repository import PublishingRepository
from repositories.review_repository import ReviewRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from schemas.publishing import PublishPlanCreateInput
from services.publishing_service import PublishingService
from services.review_service import ReviewService


def _make_publishing_service(tmp_path: Path) -> PublishingService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    return PublishingService(PublishingRepository(session_factory=create_session_factory(engine)))


def _make_review_service(
    tmp_path: Path,
) -> tuple[ReviewService, DashboardRepository, ScriptRepository, StoryboardRepository]:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    dashboard_repository = DashboardRepository(session_factory=session_factory)
    script_repository = ScriptRepository(session_factory=session_factory)
    storyboard_repository = StoryboardRepository(session_factory=session_factory)
    review_repository = ReviewRepository(session_factory=session_factory)
    service = ReviewService(
        review_repository,
        dashboard_repository=dashboard_repository,
        script_repository=script_repository,
        storyboard_repository=storyboard_repository,
    )
    return service, dashboard_repository, script_repository, storyboard_repository


def test_publishing_receipt_history_and_calendar_conflicts(tmp_path: Path) -> None:
    service = _make_publishing_service(tmp_path)

    scheduled_at = datetime(2026, 4, 17, 8, 30, tzinfo=timezone.utc)
    first = service.create_plan(
        PublishPlanCreateInput(
            title="首发计划 A",
            account_id="account-1",
            project_id="project-1",
            scheduled_at=scheduled_at,
        )
    )
    service.create_plan(
        PublishPlanCreateInput(
            title="冲突计划 B",
            account_id="account-1",
            project_id="project-2",
            scheduled_at=scheduled_at,
        )
    )

    precheck = service.precheck(first.id)
    assert precheck.has_errors is True
    assert len(precheck.conflicts) == 1
    assert precheck.conflicts[0].conflicting_plan_id is not None

    with pytest.raises(HTTPException):
        service.submit(first.id)

    clean_plan = service.create_plan(
        PublishPlanCreateInput(
            title="首发计划 C",
            account_id="account-2",
            project_id="project-3",
            scheduled_at=scheduled_at,
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

    calendar = service.get_calendar()
    assert len(calendar.items) >= 1
    assert any(item.conflict_count >= 1 for item in calendar.items)


def test_review_adopt_creates_child_project_and_copies_context(tmp_path: Path) -> None:
    service, dashboard_repository, script_repository, storyboard_repository = _make_review_service(
        tmp_path
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
