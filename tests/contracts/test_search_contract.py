from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_search_contract_returns_grouped_results(
    runtime_client: TestClient,
    tmp_path: Path,
) -> None:
    project_response = runtime_client.post(
        "/api/dashboard/projects",
        json={"name": "Alpha 项目", "description": "Alpha 描述"},
    )
    project_id = project_response.json()["data"]["id"]

    runtime_client.put(
        f"/api/scripts/projects/{project_id}/document",
        json={"content": "Alpha Hook\n第二行文案"},
    )
    runtime_client.post(
        "/api/assets",
        json={"name": "Alpha 资产", "type": "image", "source": "imported"},
    )
    runtime_client.post(
        "/api/accounts",
        json={"name": "Alpha 账号", "platform": "tiktok", "status": "active"},
    )

    workspace_root = tmp_path / "alpha-workspace"
    workspace_root.mkdir()
    runtime_client.post(
        "/api/devices/workspaces",
        json={"name": "Alpha 工作区", "root_path": str(workspace_root)},
    )

    response = runtime_client.get("/api/search", params={"q": "Alpha"})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {
        "projects",
        "scripts",
        "tasks",
        "assets",
        "accounts",
        "workspaces",
    }

    assert payload["data"]["projects"][0]["name"] == "Alpha 项目"
    assert set(payload["data"]["projects"][0]) == {"id", "name", "subtitle", "updatedAt"}
    assert payload["data"]["scripts"][0]["projectId"] == project_id
    assert set(payload["data"]["scripts"][0]) == {
        "id",
        "projectId",
        "title",
        "snippet",
        "updatedAt",
    }
    assert payload["data"]["assets"][0]["name"] == "Alpha 资产"
    assert set(payload["data"]["assets"][0]) == {
        "id",
        "name",
        "type",
        "thumbnailUrl",
        "updatedAt",
    }
    assert payload["data"]["accounts"][0]["name"] == "Alpha 账号"
    assert set(payload["data"]["accounts"][0]) == {"id", "name", "status"}
    assert payload["data"]["workspaces"][0]["name"] == "Alpha 工作区"
    assert set(payload["data"]["workspaces"][0]) == {"id", "name", "status"}
