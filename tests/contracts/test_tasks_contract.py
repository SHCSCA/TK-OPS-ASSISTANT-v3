from __future__ import annotations

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


def test_tasks_contract_returns_404_for_unknown_task(runtime_client: TestClient) -> None:
    response = runtime_client.get("/api/tasks/missing-task")

    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "任务不存在"
