from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.review import router as review_router
from domain.models import Base
from domain.models.publishing import PublishPlan
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.dashboard_repository import DashboardRepository
from repositories.publishing_repository import PublishingRepository
from repositories.review_repository import ReviewRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from schemas.review import ReviewSummaryUpdateInput
from services.review_service import ReviewService


def _make_review_client(
    tmp_path,
) -> tuple[TestClient, ReviewService, DashboardRepository, ScriptRepository, PublishingRepository]:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    dashboard_repository = DashboardRepository(session_factory=session_factory)
    script_repository = ScriptRepository(session_factory=session_factory)
    storyboard_repository = StoryboardRepository(session_factory=session_factory)
    review_repository = ReviewRepository(session_factory=session_factory)
    publishing_repository = PublishingRepository(session_factory=session_factory)

    review_service = ReviewService(
        review_repository,
        dashboard_repository=dashboard_repository,
        script_repository=script_repository,
        storyboard_repository=storyboard_repository,
        publishing_repository=publishing_repository,
    )

    app = FastAPI()
    app.state.review_service = review_service
    app.state.dashboard_repository = dashboard_repository
    app.state.script_repository = script_repository
    app.state.storyboard_repository = storyboard_repository
    app.state.publishing_repository = publishing_repository
    app.include_router(review_router)

    return (
        TestClient(app),
        review_service,
        dashboard_repository,
        script_repository,
        publishing_repository,
    )


def test_review_summary_contract_includes_contextual_fields(tmp_path) -> None:
    client, review_service, dashboard_repository, script_repository, publishing_repository = (
        _make_review_client(tmp_path)
    )

    project = dashboard_repository.create_project(
        name="Review Contract Project",
        description="Contract coverage",
    )
    script_repository.save_version(
        project.id,
        source="ai",
        content="前三秒先抛出结论\n主体段落补充论据\n结尾给出行动指令",
        provider="openai",
        model="gpt-4.1-mini",
    )
    plan = publishing_repository.create_plan(
        PublishPlan(
            title="首轮发布计划",
            project_id=project.id,
            status="submitted",
            scheduled_at=datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
        )
    )
    publishing_repository.create_receipt(
        plan_id=plan.id,
        status="receipt_pending",
        platform_response_json=json.dumps(
            {
                "stage": "receipt",
                "summary": "平台已接收，等待回执确认。",
                "errorCode": None,
                "errorMessage": None,
                "isFinal": False,
            },
            ensure_ascii=False,
        ),
    )

    review_service.update_summary(
        project.id,
        ReviewSummaryUpdateInput(
            project_name=project.name,
            total_views=1200,
            total_likes=36,
            total_comments=9,
            avg_watch_time_sec=6.8,
            completion_rate=0.28,
        ),
    )

    analyze_response = client.post(f"/api/review/projects/{project.id}/analyze")
    assert analyze_response.status_code == 200

    summary_response = client.get(f"/api/review/projects/{project.id}/summary")
    assert summary_response.status_code == 200
    payload = summary_response.json()

    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert {
        "id",
        "project_id",
        "project_name",
        "total_views",
        "total_likes",
        "total_comments",
        "avg_watch_time_sec",
        "completion_rate",
        "review_summary",
        "issue_categories",
        "feedback_targets",
        "latest_execution_result",
        "suggestions",
        "last_analyzed_at",
        "created_at",
        "updated_at",
    }.issubset(payload["data"].keys())

    assert project.name in payload["data"]["review_summary"]
    assert payload["data"]["issue_categories"]
    assert payload["data"]["feedback_targets"]
    assert payload["data"]["latest_execution_result"]["source"] == "publishing"
    assert payload["data"]["latest_execution_result"]["plan_id"] == plan.id
    assert payload["data"]["latest_execution_result"]["title"] == "首轮发布计划"
    assert payload["data"]["latest_execution_result"]["status"] == "receipt_pending"
    assert payload["data"]["latest_execution_result"]["summary"] == "平台已接收，等待回执确认。"
    assert payload["data"]["latest_execution_result"]["scheduled_at"].startswith(
        "2026-04-20T09:00:00"
    )
    assert payload["data"]["latest_execution_result"]["received_at"]
    assert any(
        target["target_type"] == "script_version" for target in payload["data"]["feedback_targets"]
    )
    assert any(
        "脚本第 1 版" in suggestion["description"] or "发布计划" in suggestion["description"]
        for suggestion in payload["data"]["suggestions"]
    )



def test_review_apply_to_script_contract_returns_distinct_result_dto(tmp_path) -> None:
    client, review_service, dashboard_repository, script_repository, _publishing_repository = (
        _make_review_client(tmp_path)
    )

    project = dashboard_repository.create_project(
        name="Review Contract Project",
        description="Contract coverage",
    )
    script_repository.save_version(
        project.id,
        source="user",
        content="Hook\nBody\nCTA",
    )

    review_service.analyze(project.id)
    summary_response = client.get(f"/api/review/projects/{project.id}/summary")
    assert summary_response.status_code == 200
    suggestion_id = summary_response.json()["data"]["suggestions"][0]["id"]

    apply_response = client.post(f"/api/review/suggestions/{suggestion_id}/apply-to-script")

    assert apply_response.status_code == 200
    payload = apply_response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {
        "projectId",
        "suggestionId",
        "status",
        "message",
        "currentScriptVersion",
        "scriptVersion",
    }
    assert payload["data"]["projectId"] == project.id
    assert payload["data"]["status"] == "已应用"
    assert "复盘建议" in payload["data"]["message"]
    assert payload["data"]["currentScriptVersion"] == 2

    versions = script_repository.list_versions(project.id)
    assert len(versions) == 2
    assert versions[0].content != versions[1].content
    assert "复盘建议" in versions[0].content

    refreshed_summary = client.get(f"/api/review/projects/{project.id}/summary")
    assert refreshed_summary.status_code == 200
    suggestion = refreshed_summary.json()["data"]["suggestions"][0]
    assert suggestion["adopted"] is True
    assert suggestion.get("adoptedAsProjectId", suggestion.get("adopted_as_project_id")) is None
    assert suggestion.get("adoptedAt", suggestion.get("adopted_at")) is not None

    projects = dashboard_repository.list_recent_projects()
    assert len(projects) == 1
    assert projects[0].id == project.id
