from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.review import router as review_router
from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.dashboard_repository import DashboardRepository
from repositories.review_repository import ReviewRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from services.review_service import ReviewService


def _make_review_client(tmp_path) -> tuple[TestClient, ReviewService, DashboardRepository, ScriptRepository]:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    dashboard_repository = DashboardRepository(session_factory=session_factory)
    script_repository = ScriptRepository(session_factory=session_factory)
    storyboard_repository = StoryboardRepository(session_factory=session_factory)
    review_repository = ReviewRepository(session_factory=session_factory)

    review_service = ReviewService(
        review_repository,
        dashboard_repository=dashboard_repository,
        script_repository=script_repository,
        storyboard_repository=storyboard_repository,
    )

    app = FastAPI()
    app.state.review_service = review_service
    app.state.dashboard_repository = dashboard_repository
    app.state.script_repository = script_repository
    app.state.storyboard_repository = storyboard_repository
    app.include_router(review_router)

    return TestClient(app), review_service, dashboard_repository, script_repository


def test_review_apply_to_script_contract_returns_distinct_result_dto(tmp_path) -> None:
    client, review_service, dashboard_repository, script_repository = _make_review_client(tmp_path)

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

    apply_response = client.post(
        f"/api/review/suggestions/{suggestion_id}/apply-to-script"
    )

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
