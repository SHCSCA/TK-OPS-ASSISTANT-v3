from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select

from domain.models.account import Account
from domain.models.device_workspace import ExecutionBinding
from domain.models.runtime_event import RuntimeEvent
from tests.runtime.p0c_account_integration_support import (
    create_account,
    mutation_headers,
    seed_workspace_and_browser,
    session,
)


def test_account_list_composes_active_positioning_summary(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    account_id, revision = create_account(
        client,
        name="定位摘要账号",
        idempotency_key="idem_p0d_positioning_account",
    )

    initial = client.get("/api/v1/accounts")
    initial_item = _account_item(initial, account_id)
    assert initial_item["positioningSummary"] is None
    assert initial_item["lastUsedAt"] is None

    created = client.post(
        f"/api/v1/accounts/{account_id}/positioning/versions",
        headers=mutation_headers(
            revision=revision,
            idempotency_key="idem_p0d_positioning_version",
        ),
        json={
            "audience": {"segment": "独立创作者"},
            "contentPillars": ["AI 工具", "内容方法"],
            "tone": {"style": "清晰克制"},
            "prohibitedTopics": ["虚假承诺"],
            "publishingConstraints": {"maxDurationSeconds": 90},
        },
    )
    assert created.status_code == 201
    version = int(created.json()["data"]["version"])
    activated = client.post(
        (
            f"/api/v1/accounts/{account_id}/positioning/"
            f"versions/{version}/activate"
        ),
        headers=mutation_headers(
            revision=int(created.json()["meta"]["revision"]),
            idempotency_key="idem_p0d_positioning_activate",
        ),
    )
    assert activated.status_code == 200

    listed = client.get("/api/v1/accounts")
    item = _account_item(listed, account_id)
    assert item["positioningSummary"] == "面向独立创作者 · AI 工具 / 内容方法"
    assert item["lastUsedAt"] is None


def test_workspace_activation_is_explicit_idempotent_and_audited(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    account_id, revision = create_account(
        client,
        name="工作区激活账号",
        idempotency_key="idem_p0d_workspace_activation_account",
    )
    path = f"/api/v1/accounts/{account_id}/workspace-activation"
    headers = mutation_headers(
        revision=revision,
        idempotency_key="idem_p0d_workspace_activation",
    )

    first = client.post(path, headers=headers)
    replay = client.post(path, headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["data"]["lastUsedAt"] is not None
    assert first.json()["data"]["revision"] == revision + 1
    assert first.json()["meta"]["revision"] == revision + 1
    assert first.json()["meta"]["idempotentReplay"] is False
    assert replay.json()["data"] == first.json()["data"]
    assert replay.json()["meta"]["idempotentReplay"] is True
    assert first.json()["meta"]["invalidations"] == [
        "accounts:list",
        "current-context",
        f"account:{account_id}:detail",
        f"account:{account_id}:workspace",
    ]

    with session(client) as database:
        stored = database.get(Account, account_id)
        assert stored is not None
        assert stored.last_used_at == first.json()["data"]["lastUsedAt"]
        assert int(stored.revision) == revision + 1
        event_count = database.scalar(
            select(func.count(RuntimeEvent.event_id)).where(
                RuntimeEvent.account_id == account_id,
                RuntimeEvent.event_type == "account.workspace.activated",
            )
        )
        assert int(event_count or 0) == 1

    client.get(f"/api/v1/accounts/{account_id}")
    client.get(f"/api/v1/accounts/{account_id}/workspace-context")
    with session(client) as database:
        stored_after_reads = database.get(Account, account_id)
        assert stored_after_reads is not None
        assert int(stored_after_reads.revision) == revision + 1
        assert (
            stored_after_reads.last_used_at
            == first.json()["data"]["lastUsedAt"]
        )


def test_connection_candidates_are_real_scoped_and_redacted(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_a, revision_a = create_account(
        client,
        name="候选账号 A",
        idempotency_key="idem_p0d_candidates_a",
    )
    account_b, _ = create_account(
        client,
        name="候选账号 B",
        idempotency_key="idem_p0d_candidates_b",
    )
    workspace_a, browser_a = seed_workspace_and_browser(
        client,
        account_id=account_a,
        key="p0d-candidate-a",
        root=runtime_data_dir,
    )
    workspace_b, browser_b = seed_workspace_and_browser(
        client,
        account_id=account_b,
        key="p0d-candidate-b",
        root=runtime_data_dir,
    )
    now = datetime.now(UTC)
    with session(client) as database:
        database.add_all(
            [
                _binding(
                    "binding_p0d_a",
                    account_a,
                    workspace_a,
                    browser_a,
                    now,
                ),
                _binding(
                    "binding_p0d_b",
                    account_b,
                    workspace_b,
                    browser_b,
                    now,
                ),
            ]
        )
        database.commit()

    response = client.get(
        f"/api/v1/accounts/{account_a}/connection/candidates"
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    candidate = items[0]
    assert candidate["deviceWorkspace"] == {
        "id": workspace_a,
        "name": "p0d-candidate-a 工作区",
        "status": "ready",
    }
    assert candidate["browserInstance"]["id"] == browser_a
    assert candidate["browserInstance"]["name"] == (
        "p0d-candidate-a 浏览器"
    )
    assert candidate["browserInstance"]["status"] == "running"
    assert candidate["browserInstance"]["lastCheckedAt"] is not None
    assert candidate["executionBinding"] == {
        "id": "binding_p0d_a",
        "status": "active",
        "deviceWorkspaceId": workspace_a,
        "browserInstanceId": browser_a,
    }
    assert candidate["environmentId"] == "binding_p0d_a"
    assert candidate["eligibilityRevision"] == 5
    serialized = response.text
    for forbidden in (
        "root_path",
        "rootPath",
        "profile_path",
        "profilePath",
        "metadata",
        "credential",
        "sessionRef",
        "executable",
    ):
        assert forbidden not in serialized

    with session(client) as database:
        account = database.get(Account, account_a)
        assert account is not None
        assert int(account.revision) == revision_a
        assert account.last_used_at is None

    bound = client.put(
        f"/api/v1/accounts/{account_a}/connection/binding",
        headers=mutation_headers(
            revision=revision_a,
            idempotency_key="idem_p0d_candidates_bind",
        ),
        json={
            "environmentId": candidate["environmentId"],
            "eligibilityRevision": candidate["eligibilityRevision"],
        },
    )
    assert bound.status_code == 200
    assert bound.json()["data"]["executionBinding"]["id"] == (
        candidate["executionBinding"]["id"]
    )

    empty_account, _ = create_account(
        client,
        name="无候选账号",
        idempotency_key="idem_p0d_candidates_empty",
    )
    empty = client.get(
        f"/api/v1/accounts/{empty_account}/connection/candidates"
    )
    assert empty.status_code == 200
    assert empty.json()["data"] == {"items": []}


def _account_item(response: Response, account_id: str) -> dict[str, object]:
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    return next(item for item in items if item["id"] == account_id)


def _binding(
    binding_id: str,
    account_id: str,
    workspace_id: str,
    browser_id: str,
    now: datetime,
) -> ExecutionBinding:
    return ExecutionBinding(
        id=binding_id,
        account_id=account_id,
        device_workspace_id=workspace_id,
        browser_instance_id=browser_id,
        status="active",
        source="runtime-supervisor",
        metadata_json='{"secret":"不得返回"}',
        created_at=now,
        updated_at=now,
    )
