from __future__ import annotations

from fastapi.testclient import TestClient


def test_search_contract_requires_query(runtime_client: TestClient) -> None:
    response = runtime_client.get("/api/search")

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]


def test_search_contract_covers_global_result_shape(runtime_client: TestClient) -> None:
    runtime_client.app.state.dashboard_repository.create_project(
        name="Alpha 项目",
        description="Alpha 描述",
    )

    response = runtime_client.get(
        "/api/search",
        params={"q": "Alpha", "types": "projects,assets", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    result = payload["data"]
    assert set(result) == {
        "projects",
        "scripts",
        "tasks",
        "assets",
        "accounts",
        "workspaces",
    }
