from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTES_SRC = REPO_ROOT / "apps" / "py-runtime" / "src" / "api" / "routes"

if str(ROUTES_SRC) not in sys.path:
    sys.path.insert(0, str(ROUTES_SRC))

from workspace import router as workspace_router
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.timeline_repository import TimelineRepository
from schemas.envelope import error_response
from domain.models import Base
from domain.models import Project
from common.time import utc_now_iso
from services.task_manager import TaskManager
from services.workspace_service import WorkspaceService


def _assert_ok(payload: dict[str, object]) -> object:
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    return payload["data"]


@pytest.fixture
def runtime_client(tmp_path):
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        now = utc_now_iso()
        session.add(
            Project(
                id="project-workspace",
                name="剪辑工作台项目",
                description="",
                status="active",
                current_script_version=0,
                current_storyboard_version=0,
                created_at=now,
                updated_at=now,
                last_accessed_at=now,
            )
        )
        session.commit()
    repository = TimelineRepository(session_factory=session_factory)
    workspace_service = WorkspaceService(repository, task_manager=TaskManager())

    app = FastAPI()
    app.state.workspace_service = workspace_service
    app.include_router(workspace_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request, exc):  # type: ignore[no-untyped-def]
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(status_code=exc.status_code, content=error_response(message))

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request, exc):  # type: ignore[no-untyped-def]
        return JSONResponse(
            status_code=500,
            content=error_response("Internal server error"),
        )

    return TestClient(app)


def _create_workspace_timeline(runtime_client: TestClient) -> tuple[str, str]:
    create_response = runtime_client.post(
        "/api/workspace/projects/project-workspace/timeline",
        json={"name": "主时间线"},
    )
    assert create_response.status_code == 201
    timeline = _assert_ok(create_response.json())["timeline"]
    assert timeline is not None
    return "project-workspace", timeline["id"]


def _seed_timeline_with_clip(runtime_client: TestClient) -> tuple[str, str, str]:
    project_id, timeline_id = _create_workspace_timeline(runtime_client)

    update_response = runtime_client.patch(
        f"/api/workspace/timelines/{timeline_id}",
        json={
            "name": "主时间线",
            "durationSeconds": 12,
            "tracks": [
                {
                    "id": "track-video",
                    "kind": "video",
                    "name": "主画面",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-video-1",
                            "trackId": "track-video",
                            "sourceType": "manual",
                            "sourceId": None,
                            "label": "开场镜头",
                            "startMs": 0,
                            "durationMs": 4200,
                            "inPointMs": 0,
                            "outPointMs": None,
                            "status": "ready",
                            "prompt": "开场钩子",
                            "resolution": {"width": 1920, "height": 1080},
                            "editableFields": ["label", "startMs", "durationMs", "prompt"],
                        }
                    ],
                },
                {
                    "id": "track-audio",
                    "kind": "audio",
                    "name": "配音",
                    "orderIndex": 1,
                    "locked": False,
                    "muted": False,
                    "clips": [],
                },
            ],
        },
    )
    assert update_response.status_code == 200
    return project_id, timeline_id, "clip-video-1"


def test_workspace_timeline_contract_returns_empty_state(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/workspace/projects/project-empty/timeline")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"timeline", "message"}
    assert data["timeline"] is None
    assert "没有时间线" in data["message"]


def test_workspace_timeline_contract_creates_and_updates_draft(
    runtime_client: TestClient,
) -> None:
    project_id, timeline_id = _create_workspace_timeline(runtime_client)

    update_response = runtime_client.patch(
        f"/api/workspace/timelines/{timeline_id}",
        json={
            "name": "主时间线",
            "durationSeconds": 12,
            "tracks": [
                {
                    "id": "track-video-1",
                    "kind": "video",
                    "name": "视频轨 1",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-video-1",
                            "trackId": "track-video-1",
                            "sourceType": "manual",
                            "sourceId": None,
                            "label": "开场镜头",
                            "startMs": 0,
                            "durationMs": 4200,
                            "inPointMs": 0,
                            "outPointMs": None,
                            "status": "ready",
                            "prompt": "开场钩子",
                            "resolution": {"width": 1920, "height": 1080},
                            "editableFields": ["label", "startMs", "durationMs", "prompt"],
                        }
                    ],
                }
            ],
        },
    )

    assert update_response.status_code == 200
    update_data = _assert_ok(update_response.json())
    timeline = update_data["timeline"]
    assert set(timeline) == {
        "id",
        "projectId",
        "name",
        "status",
        "durationSeconds",
        "source",
        "tracks",
        "createdAt",
        "updatedAt",
    }
    assert timeline["projectId"] == project_id
    assert timeline["tracks"][0]["clips"][0]["prompt"] == "开场钩子"
    assert timeline["tracks"][0]["clips"][0]["resolution"]["width"] == 1920
    assert timeline["tracks"][0]["clips"][0]["editableFields"] == [
        "label",
        "startMs",
        "durationMs",
        "prompt",
    ]


def test_workspace_clip_contract_returns_detail_with_metadata(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.get(f"/api/workspace/clips/{clip_id}")

    assert response.status_code == 200
    clip = _assert_ok(response.json())
    assert clip["id"] == clip_id
    assert clip["prompt"] == "开场钩子"
    assert clip["resolution"]["width"] == 1920
    assert clip["editableFields"] == ["label", "startMs", "durationMs", "prompt"]


def test_workspace_clip_contract_moves_clip_atomically(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/clips/{clip_id}/move",
        json={"targetTrackId": "track-audio", "startMs": 5200},
    )

    assert response.status_code == 200
    timeline = _assert_ok(response.json())["timeline"]
    moved_clip = timeline["tracks"][1]["clips"][0]
    assert moved_clip["id"] == clip_id
    assert moved_clip["trackId"] == "track-audio"
    assert moved_clip["startMs"] == 5200
    assert timeline["tracks"][0]["clips"] == []


def test_workspace_clip_contract_trims_clip_atomically(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/clips/{clip_id}/trim",
        json={
            "startMs": 900,
            "durationMs": 3000,
            "inPointMs": 120,
            "outPointMs": 3120,
        },
    )

    assert response.status_code == 200
    timeline = _assert_ok(response.json())["timeline"]
    clip = timeline["tracks"][0]["clips"][0]
    assert clip["startMs"] == 900
    assert clip["durationMs"] == 3000
    assert clip["inPointMs"] == 120
    assert clip["outPointMs"] == 3120


def test_workspace_clip_contract_replaces_clip_atomically(
    runtime_client: TestClient,
) -> None:
    _, _, clip_id = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/clips/{clip_id}/replace",
        json={
            "sourceType": "voice_track",
            "sourceId": "voice-track-1",
            "label": "新旁白",
            "prompt": "请使用更稳重的语气",
            "resolution": {"width": 1280, "height": 720},
            "editableFields": ["label", "prompt"],
        },
    )

    assert response.status_code == 200
    timeline = _assert_ok(response.json())["timeline"]
    clip = timeline["tracks"][0]["clips"][0]
    assert clip["sourceType"] == "voice_track"
    assert clip["sourceId"] == "voice-track-1"
    assert clip["label"] == "新旁白"
    assert clip["prompt"] == "请使用更稳重的语气"
    assert clip["resolution"]["height"] == 720


def test_workspace_timeline_preview_returns_unavailable_when_helper_missing(
    runtime_client: TestClient,
) -> None:
    _, timeline_id, _ = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.get(f"/api/workspace/timelines/{timeline_id}/preview")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "unavailable"
    assert "不可用" in data["message"]


def test_workspace_timeline_precheck_returns_unavailable_when_helper_missing(
    runtime_client: TestClient,
) -> None:
    _, timeline_id, _ = _seed_timeline_with_clip(runtime_client)

    response = runtime_client.post(f"/api/workspace/timelines/{timeline_id}/precheck")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "unavailable"
    assert "不可用" in data["message"]


def test_workspace_ai_command_returns_real_taskbus_task(
    runtime_client: TestClient,
) -> None:
    project_id, timeline_id = _create_workspace_timeline(runtime_client)

    response = runtime_client.post(
        f"/api/workspace/projects/{project_id}/ai-commands",
        json={
            "timelineId": timeline_id,
            "capabilityId": "magic_cut",
            "parameters": {"selectedClipId": "clip-video-1"},
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "queued"
    assert data["task"] is not None
    assert data["task"]["kind"] == "ai-workspace-command"
    assert data["task"]["projectId"] == project_id
    assert data["task"]["ownerRef"] == {"kind": "timeline", "id": timeline_id}
