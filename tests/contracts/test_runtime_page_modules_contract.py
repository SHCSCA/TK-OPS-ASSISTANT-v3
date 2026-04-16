from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _assert_ok(payload: dict[str, object]) -> object:
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    return payload["data"]


def _assert_deleted_envelope(response) -> None:  # type: ignore[no-untyped-def]
    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data == {"deleted": True}


def test_assets_contract_covers_crud_import_and_references(
    runtime_client: TestClient,
    tmp_path: Path,
) -> None:
    list_response = runtime_client.get("/api/assets")
    assert list_response.status_code == 200
    assert _assert_ok(list_response.json()) == []

    project_response = runtime_client.post(
        "/api/dashboard/projects",
        json={"name": "Asset Project", "description": "Asset contract coverage"},
    )
    project_id = _assert_ok(project_response.json())["id"]

    create_response = runtime_client.post(
        "/api/assets",
        json={
            "name": "Import Clip",
            "type": "video",
            "source": "local",
            "filePath": "D:/tkops/imports/clip.mp4",
            "projectId": project_id,
        },
    )
    assert create_response.status_code == 200
    asset = _assert_ok(create_response.json())
    assert set(asset) == {
        "id",
        "name",
        "type",
        "source",
        "filePath",
        "fileSizeBytes",
        "durationMs",
        "thumbnailPath",
        "tags",
        "projectId",
        "metadataJson",
        "createdAt",
        "updatedAt",
    }
    asset_id = asset["id"]

    imported_file = tmp_path / "clip.mp4"
    imported_file.write_bytes(b"tkops-video")
    import_response = runtime_client.post(
        "/api/assets/import",
        json={
            "filePath": str(imported_file),
            "type": "video",
            "source": "local",
            "projectId": project_id,
            "tags": '["开场"]',
        },
    )
    assert import_response.status_code == 200
    imported_asset = _assert_ok(import_response.json())
    assert imported_asset["name"] == "clip.mp4"
    assert imported_asset["filePath"] == str(imported_file)
    assert imported_asset["fileSizeBytes"] == len(b"tkops-video")

    missing_response = runtime_client.post(
        "/api/assets/import",
        json={
            "filePath": str(tmp_path / "missing.mp4"),
            "type": "video",
            "source": "local",
        },
    )
    assert missing_response.status_code == 400
    missing_payload = missing_response.json()
    assert missing_payload["ok"] is False
    assert "文件不存在" in missing_payload["error"]

    refs_response = runtime_client.post(
        f"/api/assets/{asset_id}/references",
        json={"referenceType": "storyboard", "referenceId": "scene-1"},
    )
    assert refs_response.status_code == 200
    ref = _assert_ok(refs_response.json())
    assert set(ref) == {"id", "assetId", "referenceType", "referenceId", "createdAt"}

    ref_detail_response = runtime_client.get(f"/api/assets/references/{ref['id']}")
    assert ref_detail_response.status_code == 200
    assert _assert_ok(ref_detail_response.json())["id"] == ref["id"]

    list_refs_response = runtime_client.get(f"/api/assets/{asset_id}/references")
    assert list_refs_response.status_code == 200
    assert len(_assert_ok(list_refs_response.json())) == 1

    blocked_delete_response = runtime_client.delete(f"/api/assets/{asset_id}")
    assert blocked_delete_response.status_code == 409
    blocked_payload = blocked_delete_response.json()
    assert blocked_payload["ok"] is False
    assert "资产存在引用" in blocked_payload["error"]

    _assert_deleted_envelope(runtime_client.delete(f"/api/assets/references/{ref['id']}"))
    _assert_deleted_envelope(runtime_client.delete(f"/api/assets/{asset_id}"))
    _assert_deleted_envelope(runtime_client.delete(f"/api/assets/{imported_asset['id']}"))


def test_accounts_contract_covers_groups_refresh_and_delete(runtime_client: TestClient) -> None:
    group_response = runtime_client.post(
        "/api/accounts/groups",
        json={"name": "TikTok Main", "description": "主账号组", "color": "#35f0a3"},
    )
    assert group_response.status_code == 200
    group = _assert_ok(group_response.json())
    assert set(group) == {"id", "name", "description", "color", "createdAt"}

    account_response = runtime_client.post(
        "/api/accounts",
        json={"name": "Creator A", "platform": "tiktok", "username": "creator_a"},
    )
    assert account_response.status_code == 200
    account = _assert_ok(account_response.json())
    assert set(account) == {
        "id",
        "name",
        "platform",
        "username",
        "avatarUrl",
        "status",
        "authExpiresAt",
        "followerCount",
        "followingCount",
        "videoCount",
        "tags",
        "notes",
        "createdAt",
        "updatedAt",
    }

    refresh_response = runtime_client.post(f"/api/accounts/{account['id']}/refresh-stats")
    assert refresh_response.status_code == 200
    assert set(_assert_ok(refresh_response.json())) == {
        "id",
        "status",
        "updatedAt",
        "providerStatus",
    }

    member_response = runtime_client.post(
        f"/api/accounts/groups/{group['id']}/members",
        json={"accountId": account["id"]},
    )
    assert member_response.status_code == 200
    assert _assert_ok(member_response.json())["accountId"] == account["id"]

    _assert_deleted_envelope(
        runtime_client.delete(f"/api/accounts/groups/{group['id']}/members/{account['id']}")
    )
    _assert_deleted_envelope(runtime_client.delete(f"/api/accounts/{account['id']}"))
    _assert_deleted_envelope(runtime_client.delete(f"/api/accounts/groups/{group['id']}"))


def test_device_workspaces_contract_uses_json_envelope_for_delete(
    runtime_client: TestClient,
) -> None:
    create_response = runtime_client.post(
        "/api/devices/workspaces",
        json={"name": "Local PC Workspace", "root_path": "D:/tkops/workspaces/main"},
    )
    assert create_response.status_code == 201
    workspace = _assert_ok(create_response.json())
    assert set(workspace) == {
        "id",
        "name",
        "root_path",
        "status",
        "error_count",
        "last_used_at",
        "created_at",
        "updated_at",
    }

    health_response = runtime_client.post(
        f"/api/devices/workspaces/{workspace['id']}/health-check"
    )
    assert health_response.status_code == 200
    assert set(_assert_ok(health_response.json())) == {"workspace_id", "status", "checked_at"}

    _assert_deleted_envelope(runtime_client.delete(f"/api/devices/workspaces/{workspace['id']}"))


def test_automation_contract_uses_json_envelope_for_delete(runtime_client: TestClient) -> None:
    create_response = runtime_client.post(
        "/api/automation/tasks",
        json={"name": "同步发布状态", "type": "sync_status"},
    )
    assert create_response.status_code == 201
    task = _assert_ok(create_response.json())
    assert set(task) == {
        "id",
        "name",
        "type",
        "enabled",
        "cron_expr",
        "last_run_at",
        "last_run_status",
        "run_count",
        "config_json",
        "created_at",
        "updated_at",
    }

    trigger_response = runtime_client.post(f"/api/automation/tasks/{task['id']}/trigger")
    assert trigger_response.status_code == 200
    assert set(_assert_ok(trigger_response.json())) == {"task_id", "run_id", "status", "message"}

    runs_response = runtime_client.get(f"/api/automation/tasks/{task['id']}/runs")
    assert runs_response.status_code == 200
    assert len(_assert_ok(runs_response.json())) == 1

    _assert_deleted_envelope(runtime_client.delete(f"/api/automation/tasks/{task['id']}"))


def test_publishing_contract_uses_json_envelope_for_delete(runtime_client: TestClient) -> None:
    create_response = runtime_client.post(
        "/api/publishing/plans",
        json={"title": "发布计划 A", "account_name": "Creator A", "project_id": "project-1"},
    )
    assert create_response.status_code == 201
    plan = _assert_ok(create_response.json())
    assert set(plan) == {
        "id",
        "title",
        "account_id",
        "account_name",
        "project_id",
        "video_asset_id",
        "status",
        "scheduled_at",
        "submitted_at",
        "published_at",
        "error_message",
        "precheck_result_json",
        "created_at",
        "updated_at",
    }

    precheck_response = runtime_client.post(f"/api/publishing/plans/{plan['id']}/precheck")
    assert precheck_response.status_code == 200
    assert set(_assert_ok(precheck_response.json())) == {
        "plan_id",
        "items",
        "has_errors",
        "checked_at",
    }

    submit_response = runtime_client.post(f"/api/publishing/plans/{plan['id']}/submit")
    assert submit_response.status_code == 200
    assert set(_assert_ok(submit_response.json())) == {
        "plan_id",
        "status",
        "submitted_at",
        "message",
    }

    cancel_response = runtime_client.post(f"/api/publishing/plans/{plan['id']}/cancel")
    assert cancel_response.status_code == 200
    assert _assert_ok(cancel_response.json())["status"] == "cancelled"

    _assert_deleted_envelope(runtime_client.delete(f"/api/publishing/plans/{plan['id']}"))


def test_renders_contract_uses_json_envelope_for_delete(runtime_client: TestClient) -> None:
    create_response = runtime_client.post(
        "/api/renders/tasks",
        json={"project_id": "project-1", "project_name": "Demo", "preset": "1080p"},
    )
    assert create_response.status_code == 201
    task = _assert_ok(create_response.json())
    assert set(task) == {
        "id",
        "project_id",
        "project_name",
        "preset",
        "format",
        "status",
        "progress",
        "output_path",
        "error_message",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    }

    cancel_response = runtime_client.post(f"/api/renders/tasks/{task['id']}/cancel")
    assert cancel_response.status_code == 200
    assert set(_assert_ok(cancel_response.json())) == {"task_id", "status", "message"}

    _assert_deleted_envelope(runtime_client.delete(f"/api/renders/tasks/{task['id']}"))


def test_review_contract_covers_summary_update_and_analyze(
    runtime_client: TestClient,
) -> None:
    summary_response = runtime_client.get("/api/review/projects/project-review/summary")
    assert summary_response.status_code == 200
    summary = _assert_ok(summary_response.json())
    assert set(summary) == {
        "id",
        "project_id",
        "project_name",
        "total_views",
        "total_likes",
        "total_comments",
        "avg_watch_time_sec",
        "completion_rate",
        "suggestions",
        "last_analyzed_at",
        "created_at",
        "updated_at",
    }

    update_response = runtime_client.patch(
        "/api/review/projects/project-review/summary",
        json={"project_name": "复盘项目", "total_views": 0, "completion_rate": 0},
    )
    assert update_response.status_code == 200
    assert _assert_ok(update_response.json())["project_name"] == "复盘项目"

    analyze_response = runtime_client.post("/api/review/projects/project-review/analyze")
    assert analyze_response.status_code == 200
    assert set(_assert_ok(analyze_response.json())) == {
        "project_id",
        "status",
        "message",
        "analyzed_at",
    }
