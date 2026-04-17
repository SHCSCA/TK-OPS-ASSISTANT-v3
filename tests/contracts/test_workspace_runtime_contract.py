from __future__ import annotations

from fastapi.testclient import TestClient


def _assert_ok(payload: dict[str, object]) -> object:
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    return payload["data"]


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
    project_response = runtime_client.post(
        "/api/dashboard/projects",
        json={"name": "剪辑工作台项目", "description": "M05 contract coverage"},
    )
    project = _assert_ok(project_response.json())

    create_response = runtime_client.post(
        f"/api/workspace/projects/{project['id']}/timeline",
        json={"name": "主时间线"},
    )

    assert create_response.status_code == 201
    create_data = _assert_ok(create_response.json())
    timeline = create_data["timeline"]
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
    assert timeline["projectId"] == project["id"]
    assert timeline["tracks"] == []

    update_response = runtime_client.patch(
        f"/api/workspace/timelines/{timeline['id']}",
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
                    "clips": [],
                }
            ],
        },
    )

    assert update_response.status_code == 200
    update_data = _assert_ok(update_response.json())
    assert update_data["timeline"]["durationSeconds"] == 12
    assert update_data["timeline"]["tracks"][0]["kind"] == "video"


def test_workspace_ai_command_returns_blocked_contract(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post(
        "/api/workspace/projects/project-1/ai-commands",
        json={
            "timelineId": "timeline-1",
            "capabilityId": "magic_cut",
            "parameters": {"selectedClipId": "clip-1"},
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert set(data) == {"status", "task", "message"}
    assert data["status"] == "blocked"
    assert data["task"] is None
    assert "尚未接入" in data["message"]
