from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    return payload["data"]


def _create_ready_account(runtime_client: TestClient) -> dict[str, object]:
    response = runtime_client.post(
        "/api/accounts",
        json={
            "name": "发布账号 A",
            "platform": "tiktok",
            "username": "publisher_a",
            "status": "active",
        },
    )
    assert response.status_code == 200
    return _assert_ok(response.json())


def _bind_workspace(
    runtime_client: TestClient,
    *,
    account_id: str,
    root_path: str,
) -> None:
    workspace_response = runtime_client.post(
        "/api/devices/browser-instances",
        json={"name": "发布工作区", "root_path": root_path},
    )
    assert workspace_response.status_code == 201
    workspace = _assert_ok(workspace_response.json())
    binding_response = runtime_client.put(
        f"/api/accounts/{account_id}/binding",
        json={"browserInstanceId": workspace["id"], "status": "active"},
    )
    assert binding_response.status_code == 200


def test_publishing_contract_exposes_precheck_blockers(runtime_client: TestClient) -> None:
    create_response = runtime_client.post(
        "/api/publishing/plans",
        json={
            "title": "待补齐发布计划",
            "project_id": "project-blocked",
        },
    )
    assert create_response.status_code == 201
    plan = _assert_ok(create_response.json())
    assert {
        "precheck_summary",
        "latest_receipt",
        "publish_readiness",
        "recovery",
    }.issubset(plan)

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
    assert precheck["blocking_count"] >= 1
    assert {
        "code",
        "label",
        "result",
        "message",
        "error_code",
        "affected_target",
        "next_action",
    }.issubset(precheck["items"][0])

    blocked_submit = runtime_client.post(f"/api/publishing/plans/{plan['id']}/submit")
    assert blocked_submit.status_code == 409
    error = blocked_submit.json()
    assert error["error_code"] == "publishing.precheck_failed"


def test_publishing_contract_exposes_receipt_summary(runtime_client: TestClient, tmp_path: Path) -> None:
    workspace_root = tmp_path / "publish-workspace"
    workspace_root.mkdir()
    account = _create_ready_account(runtime_client)
    _bind_workspace(runtime_client, account_id=account["id"], root_path=str(workspace_root))

    create_response = runtime_client.post(
        "/api/publishing/plans",
        json={
            "title": "可提交发布计划",
            "account_id": account["id"],
            "account_name": account["name"],
            "project_id": "project-ready",
            "video_asset_id": "asset-ready",
            "scheduled_at": "2026-04-21T10:30:00+00:00",
        },
    )
    assert create_response.status_code == 201
    plan = _assert_ok(create_response.json())

    submit_response = runtime_client.post(f"/api/publishing/plans/{plan['id']}/submit")
    assert submit_response.status_code == 200
    submit_result = _assert_ok(submit_response.json())
    assert {
        "plan_id",
        "status",
        "submitted_at",
        "message",
        "receipt_status",
        "error_code",
        "error_message",
        "next_action",
        "receipt",
    } == set(submit_result)

    latest_receipt_response = runtime_client.get(f"/api/publishing/plans/{plan['id']}/receipt")
    assert latest_receipt_response.status_code == 200
    latest_receipt = _assert_ok(latest_receipt_response.json())
    assert {
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
    } == set(latest_receipt)
    assert latest_receipt["status"] == "receipt_pending"
