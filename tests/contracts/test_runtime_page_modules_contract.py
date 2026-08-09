from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from domain.models.account import Account
from tests.runtime.p0c_account_integration_support import (
    create_account,
    mutation_headers,
    seed_eligible_execution_environment,
    session,
)


def _assert_ok(payload: dict[str, object]) -> object:
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    return payload["data"]


def _assert_deleted_envelope(response) -> None:  # type: ignore[no-untyped-def]
    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data == {"deleted": True}


def _prepare_v1_account_connection(
    runtime_client: TestClient,
    *,
    name: str,
    username: str | None,
    key: str,
    root: Path,
    mark_ready: bool = False,
) -> dict[str, object]:
    account_id, revision = create_account(
        runtime_client,
        name=name,
        idempotency_key=f"idem-contract-{key}-account",
    )
    if username is not None:
        patched = runtime_client.patch(
            f"/api/v1/accounts/{account_id}",
            headers=mutation_headers(revision=revision),
            json={"username": username},
        )
        assert patched.status_code == 200, patched.text
        revision = int(patched.json()["meta"]["revision"])

    environment_id, eligibility_revision, workspace_id, browser_id = (
        seed_eligible_execution_environment(
        runtime_client,
        account_id=account_id,
        key=key,
        root=root,
        )
    )
    now = datetime.now(UTC)

    bound = runtime_client.put(
        f"/api/v1/accounts/{account_id}/connection/binding",
        headers=mutation_headers(
            revision=revision,
            idempotency_key=f"idem-contract-{key}-binding",
        ),
        json={
            "environmentId": environment_id,
            "eligibilityRevision": eligibility_revision,
        },
    )
    assert bound.status_code == 200, bound.text

    if mark_ready:
        with session(runtime_client) as database:
            account = database.get(Account, account_id)
            assert account is not None
            account.status = "ready"
            account.wizard_completed_at = now.isoformat()
            account.status_reason_code = None
            database.commit()
    return {
        "id": account_id,
        "name": name,
        "workspaceId": workspace_id,
        "browserInstanceId": browser_id,
        "connection": bound.json()["data"],
    }


def test_assets_contract_covers_groups_batch_ops_and_thumbnail_fields(
    runtime_client: TestClient,
    tmp_path: Path,
) -> None:
    group_response = runtime_client.post("/api/assets/groups", json={"name": "主素材"})
    assert group_response.status_code == 200
    group = _assert_ok(group_response.json())
    assert set(group) == {"id", "name", "parentId", "createdAt"}

    second_group_response = runtime_client.post(
        "/api/assets/groups",
        json={"name": "待整理素材"},
    )
    second_group = _assert_ok(second_group_response.json())

    source_file = tmp_path / "demo.mp4"
    source_file.write_bytes(b"tkops-video")
    create_response = runtime_client.post(
        "/api/assets",
        json={
            "name": "Demo Clip",
            "type": "video",
            "source": "local",
            "groupId": group["id"],
            "filePath": str(source_file),
        },
    )
    assert create_response.status_code == 200
    asset = _assert_ok(create_response.json())
    assert {
        "id",
        "name",
        "type",
        "source",
        "groupId",
        "filePath",
        "fileSizeBytes",
        "durationMs",
        "thumbnailPath",
        "thumbnailGeneratedAt",
        "tags",
        "projectId",
        "metadataJson",
        "createdAt",
        "updatedAt",
    }.issubset(asset)

    imported_file = tmp_path / "demo.mp4"
    imported_file.write_bytes(b"tkops-video")
    import_response = runtime_client.post(
        "/api/assets/import",
        json={
            "filePath": str(imported_file),
            "type": "video",
            "source": "local",
            "groupId": group["id"],
        },
    )
    assert import_response.status_code == 200
    imported = _assert_ok(import_response.json())

    move_response = runtime_client.post(
        "/api/assets/batch-move-group",
        json={"assetIds": [asset["id"], imported["id"]], "groupId": second_group["id"]},
    )
    assert move_response.status_code == 200
    assert _assert_ok(move_response.json()) == {
        "movedCount": 2,
        "groupId": second_group["id"],
    }

    group_list = runtime_client.get("/api/assets/groups")
    assert group_list.status_code == 200
    assert len(_assert_ok(group_list.json())) == 2

    delete_response = runtime_client.post(
        "/api/assets/batch-delete",
        json={"assetIds": [asset["id"], imported["id"]]},
    )
    assert delete_response.status_code == 200
    assert _assert_ok(delete_response.json()) == {"deletedCount": 2}

    _assert_deleted_envelope(runtime_client.delete(f"/api/assets/groups/{group['id']}"))
    _assert_deleted_envelope(runtime_client.delete(f"/api/assets/groups/{second_group['id']}"))


def test_accounts_and_devices_contract_cover_binding_and_logs(
    licensed_runtime_client: TestClient,
    tmp_path: Path,
) -> None:
    runtime_client = licensed_runtime_client
    account = _prepare_v1_account_connection(
        runtime_client,
        name="Creator A",
        username="creator_a",
        key="account-device",
        root=tmp_path,
    )
    workspace_response = runtime_client.get(
        f"/api/devices/browser-instances/{account['workspaceId']}"
    )
    assert workspace_response.status_code == 200
    workspace = _assert_ok(workspace_response.json())
    assert {
        "id",
        "name",
        "root_path",
        "status",
        "error_count",
        "last_used_at",
        "created_at",
        "updated_at",
    }.issubset(workspace)

    binding = account["connection"]
    assert set(binding) == {
        "accountId",
        "deviceWorkspace",
        "browserInstance",
        "executionBinding",
        "lastCheck",
        "healthStatus",
        "authStatus",
        "revision",
    }
    assert binding["executionBinding"]["id"] == "binding_account-device"
    assert "secret" not in str(binding)

    binding_list = runtime_client.get("/api/devices/bindings")
    assert binding_list.status_code == 200
    assert len(_assert_ok(binding_list.json())) == 1

    health_response = runtime_client.post(f"/api/devices/browser-instances/{workspace['id']}/health-check")
    assert health_response.status_code == 200

    logs_response = runtime_client.get(f"/api/devices/browser-instances/{workspace['id']}/logs")
    assert logs_response.status_code == 200
    logs = _assert_ok(logs_response.json())
    assert len(logs) >= 1
    assert set(logs[0]) == {"id", "workspaceId", "kind", "level", "message", "contextJson", "createdAt"}


def test_automation_contract_covers_pause_and_resume(runtime_client: TestClient) -> None:
    create_response = runtime_client.post(
        "/api/automation/tasks",
        json={
            "name": "同步发布状态",
            "type": "sync_status",
            "rule": {"kind": "interval", "config": {"minutes": 15, "workspaceId": "workspace-1"}},
        },
    )
    assert create_response.status_code == 201
    task = _assert_ok(create_response.json())
    assert {
        "id",
        "name",
        "type",
        "enabled",
        "cron_expr",
        "last_run_at",
        "last_run_status",
        "run_count",
        "rule",
        "config_json",
        "created_at",
        "updated_at",
    }.issubset(task)

    pause_response = runtime_client.post(f"/api/automation/tasks/{task['id']}/pause")
    assert pause_response.status_code == 200
    assert _assert_ok(pause_response.json())["enabled"] is False

    resume_response = runtime_client.post(f"/api/automation/tasks/{task['id']}/resume")
    assert resume_response.status_code == 200
    assert _assert_ok(resume_response.json())["enabled"] is True

    trigger_response = runtime_client.post(f"/api/automation/tasks/{task['id']}/trigger")
    assert trigger_response.status_code == 200

    _assert_deleted_envelope(runtime_client.delete(f"/api/automation/tasks/{task['id']}"))


def test_publishing_contract_covers_calendar_and_receipts(
    licensed_runtime_client: TestClient,
    tmp_path: Path,
) -> None:
    runtime_client = licensed_runtime_client
    account = _prepare_v1_account_connection(
        runtime_client,
        name="Creator A",
        username="creator_a",
        key="publishing-calendar",
        root=tmp_path,
        mark_ready=True,
    )

    first = runtime_client.post(
        "/api/publishing/plans",
        json={
            "title": "???? A",
            "account_id": account["id"],
            "account_name": account["name"],
            "project_id": "project-1",
            "video_asset_id": "asset-1",
            "scheduled_at": "2026-04-17T08:30:00+00:00",
        },
    )
    assert first.status_code == 201
    plan = _assert_ok(first.json())
    assert {
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
        "precheck_summary",
        "latest_receipt",
        "publish_readiness",
        "recovery",
        "created_at",
        "updated_at",
    }.issubset(plan)

    conflict = runtime_client.post(
        "/api/publishing/plans",
        json={
            "title": "???? B",
            "account_id": account["id"],
            "account_name": account["name"],
            "project_id": "project-2",
            "video_asset_id": "asset-2",
            "scheduled_at": "2026-04-17T08:30:00+00:00",
        },
    )
    conflict_plan = _assert_ok(conflict.json())

    precheck_response = runtime_client.post(f"/api/publishing/plans/{plan['id']}/precheck")
    assert precheck_response.status_code == 200
    precheck = _assert_ok(precheck_response.json())
    assert {
        "plan_id",
        "items",
        "conflicts",
        "has_errors",
        "checked_at",
        "blocking_count",
        "readiness",
    } == set(precheck)
    assert len(precheck["conflicts"]) == 1
    assert set(precheck["conflicts"][0]) == {
        "conflicting_plan_id",
        "conflicting_title",
        "conflicting_scheduled_at",
        "reason",
    }

    blocked_submit = runtime_client.post(f"/api/publishing/plans/{plan['id']}/submit")
    assert blocked_submit.status_code == 409

    update_response = runtime_client.patch(
        f"/api/publishing/plans/{conflict_plan['id']}",
        json={"scheduled_at": "2026-04-17T09:00:00+00:00"},
    )
    assert update_response.status_code == 200

    submit_response = runtime_client.post(f"/api/publishing/plans/{conflict_plan['id']}/submit")
    assert submit_response.status_code == 200

    receipts_response = runtime_client.get(f"/api/publishing/plans/{conflict_plan['id']}/receipts")
    assert receipts_response.status_code == 200
    receipts = _assert_ok(receipts_response.json())
    assert len(receipts) == 1
    assert set(receipts[0]) == {
        "id",
        "plan_id",
        "status",
        "stage",
        "summary",
        "error_code",
        "error_message",
        "next_action",
        "is_final",
        "platform_response_json",
        "received_at",
        "created_at",
    }

    latest_receipt = runtime_client.get(f"/api/publishing/plans/{conflict_plan['id']}/receipt")
    assert latest_receipt.status_code == 200
    assert _assert_ok(latest_receipt.json())["plan_id"] == conflict_plan["id"]

    calendar_response = runtime_client.get("/api/publishing/calendar")
    assert calendar_response.status_code == 200
    calendar = _assert_ok(calendar_response.json())
    assert set(calendar) == {"items", "generated_at"}
    assert len(calendar["items"]) >= 2
    assert set(calendar["items"][0]) == {
        "plan_id",
        "title",
        "status",
        "scheduled_at",
        "account_name",
        "conflict_count",
    }

    _assert_deleted_envelope(runtime_client.delete(f"/api/publishing/plans/{plan['id']}"))
    _assert_deleted_envelope(runtime_client.delete(f"/api/publishing/plans/{conflict_plan['id']}"))

def test_review_contract_covers_analyze_and_adopt(runtime_client: TestClient) -> None:
    project_response = runtime_client.post(
        "/api/dashboard/projects",
        json={"name": "Review Project", "description": "review contract coverage"},
    )
    assert project_response.status_code == 200
    project = _assert_ok(project_response.json())

    runtime_client.app.state.script_repository.save_version(
        project["id"],
        source="ai",
        content="?????",
    )
    runtime_client.app.state.storyboard_repository.save_version(
        project["id"],
        based_on_script_revision=1,
        source="ai",
        scenes=[{"title": "????", "duration": "3s"}],
    )

    analyze_response = runtime_client.post(f"/api/review/projects/{project['id']}/analyze")
    assert analyze_response.status_code == 200

    summary_response = runtime_client.get(f"/api/review/projects/{project['id']}/summary")
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
        "review_summary",
        "issue_categories",
        "feedback_targets",
        "latest_execution_result",
        "suggestions",
        "last_analyzed_at",
        "created_at",
        "updated_at",
    }
    suggestion_id = summary["suggestions"][0]["id"]
    assert set(summary["suggestions"][0]) == {
        "id",
        "code",
        "category",
        "title",
        "description",
        "priority",
        "adopted",
        "adopted_as_project_id",
        "adopted_at",
    }
    assert summary["issue_categories"]
    assert summary["feedback_targets"]

    adopt_response = runtime_client.post(
        f"/api/review/projects/{project['id']}/suggestions/{suggestion_id}/adopt"
    )
    assert adopt_response.status_code == 200
    adopted_project = _assert_ok(adopt_response.json())
    assert adopted_project["id"] != project["id"]

    current_summary = runtime_client.get(f"/api/review/projects/{project['id']}/summary")
    adopted = _assert_ok(current_summary.json())["suggestions"][0]
    assert adopted["adopted"] is True
    assert adopted["adopted_as_project_id"] == adopted_project["id"]
