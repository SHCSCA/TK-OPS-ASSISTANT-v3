from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


def test_tasks_contract_lists_active_tasks_with_json_envelope(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/tasks")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert isinstance(payload["data"], list)


def test_tasks_contract_supports_filters_and_extended_task_shape(
    runtime_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import api.routes.tasks as tasks_route

    fake_task = SimpleNamespace(
        to_dict=lambda: {
            "id": "task-1",
            "kind": "video-import",
            "label": "导入视频",
            "status": "running",
            "progressPct": 35,
            "startedAt": "2026-04-17T08:00:00Z",
            "finishedAt": None,
            "etaMs": 120000,
            "projectId": "project-1",
            "ownerRef": {"kind": "imported-video", "id": "video-1"},
            "errorCode": None,
            "errorMessage": None,
            "retryable": False,
            "createdAt": "2026-04-17T08:00:00Z",
            "updatedAt": "2026-04-17T08:01:00Z",
        }
    )

    called: dict[str, object] = {}

    def fake_list_tasks(*, kind: str | None = None, statuses: set[str] | None = None):
        called["kind"] = kind
        called["statuses"] = statuses
        return [fake_task]

    monkeypatch.setattr(tasks_route.task_manager, "list_tasks", fake_list_tasks, raising=False)

    response = runtime_client.get("/api/tasks", params={"type": "video-import", "status": "running,queued"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"] == [
        {
            "id": "task-1",
            "kind": "video-import",
            "label": "导入视频",
            "status": "running",
            "progressPct": 35,
            "startedAt": "2026-04-17T08:00:00Z",
            "finishedAt": None,
            "etaMs": 120000,
            "projectId": "project-1",
            "ownerRef": {"kind": "imported-video", "id": "video-1"},
            "errorCode": None,
            "errorMessage": None,
            "retryable": False,
            "createdAt": "2026-04-17T08:00:00Z",
            "updatedAt": "2026-04-17T08:01:00Z",
        }
    ]
    assert called == {"kind": "video-import", "statuses": {"running", "queued"}}


def test_tasks_contract_returns_404_for_unknown_task(runtime_client: TestClient) -> None:
    response = runtime_client.get("/api/tasks/missing-task")

    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "任务不存在"
