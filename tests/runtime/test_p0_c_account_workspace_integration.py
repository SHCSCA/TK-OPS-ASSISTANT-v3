from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from domain.models.account import Account
from domain.models.account_configuration import AccountPublishDefaults
from domain.models.account_connection import AccountConnection
from domain.models.device_workspace import (
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
)
from domain.models.knowledge import AccountKnowledgeBase
from domain.models.mutation_idempotency import RuntimeMutationIdempotency
from domain.models.runtime_event import RuntimeEvent
from domain.models.runtime_task import RuntimeTask
from errors import ErrorCode
from tests.runtime.p0c_account_integration_support import (
    account_revision,
    create_account,
    error_code,
    mutation_headers,
    seed_workspace_and_browser,
    session,
    wait_account_task,
)


def test_account_creation_backfills_defaults_outbox_and_idempotency(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    body = {
        "name": "知识型创作者",
        "username": "creator.one",
        "platform": "tiktok",
    }
    headers = mutation_headers(idempotency_key="idem_create_creator_one")

    first = client.post("/api/v1/accounts", headers=headers, json=body)
    replay = client.post("/api/v1/accounts", headers=headers, json=body)
    conflict = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={**body, "name": "不同请求"},
    )

    assert first.status_code == 201
    assert replay.status_code == 201
    assert first.json()["data"]["id"] == replay.json()["data"]["id"]
    assert first.json()["meta"]["idempotentReplay"] is False
    assert replay.json()["meta"]["idempotentReplay"] is True
    assert conflict.status_code == 409
    assert error_code(conflict) == ErrorCode.REQUEST_CONFLICT.value
    account_id = str(first.json()["data"]["id"])

    with session(client) as database:
        account = database.get(Account, account_id)
        knowledge = database.scalar(
            select(AccountKnowledgeBase).where(
                AccountKnowledgeBase.account_id == account_id
            )
        )
        defaults = database.get(AccountPublishDefaults, account_id)
        created_events = database.scalars(
            select(RuntimeEvent).where(
                RuntimeEvent.account_id == account_id,
                RuntimeEvent.event_type == "account.created",
            )
        ).all()
        idempotency_rows = database.scalars(
            select(RuntimeMutationIdempotency).where(
                RuntimeMutationIdempotency.operation_name
                == "account.create"
            )
        ).all()

        assert account is not None
        assert knowledge is not None
        assert knowledge.status == "empty"
        assert defaults is not None
        assert (
            defaults.timezone,
            defaults.privacy_level,
            defaults.allow_comments,
            defaults.allow_duet,
            defaults.allow_stitch,
            defaults.caption_rules_json,
        ) == ("UTC", "private", False, False, False, "{}")
        assert len(created_events) == 1
        assert created_events[0].topic == f"account:{account_id}:workspace"
        assert created_events[0].revision == 1
        assert len(idempotency_rows) == 1


def test_publish_defaults_dto_uses_account_aggregate_revision(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    account_id, revision = create_account(
        client,
        name="发布修订账号",
        idempotency_key="idem_publish_revision_account",
    )
    patched = client.patch(
        f"/api/v1/accounts/{account_id}",
        headers=mutation_headers(revision=revision),
        json={"name": "发布修订账号二"},
    )
    assert patched.status_code == 200
    aggregate_revision = int(patched.json()["meta"]["revision"])

    current = client.get(
        f"/api/v1/accounts/{account_id}/publish-defaults"
    )

    assert current.status_code == 200
    assert current.json()["data"]["revision"] == aggregate_revision
    with session(client) as database:
        stored = database.get(AccountPublishDefaults, account_id)
        assert stored is not None
        assert int(stored.revision) == 1
        assert int(stored.revision) != aggregate_revision

    updated = client.put(
        f"/api/v1/accounts/{account_id}/publish-defaults",
        headers=mutation_headers(revision=aggregate_revision),
        json={
            "timezone": "Asia/Shanghai",
            "privacyLevel": "public",
            "allowComments": True,
            "allowDuet": True,
            "allowStitch": True,
            "captionRules": {"suffix": "#知识分享"},
        },
    )

    assert updated.status_code == 200
    assert updated.json()["data"]["revision"] == aggregate_revision + 1
    assert updated.json()["meta"]["revision"] == aggregate_revision + 1
    assert account_revision(client, account_id) == aggregate_revision + 1


def test_connection_binding_requires_complete_account_evidence_chain(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_a, revision_a = create_account(
        client,
        name="连接账号 A",
        idempotency_key="idem_connection_account_a",
    )
    account_b, _ = create_account(
        client,
        name="连接账号 B",
        idempotency_key="idem_connection_account_b",
    )
    workspace_a, browser_a = seed_workspace_and_browser(
        client,
        account_id=account_a,
        key="a",
        root=runtime_data_dir,
    )
    workspace_b, browser_b = seed_workspace_and_browser(
        client,
        account_id=account_b,
        key="b",
        root=runtime_data_dir,
    )
    observed_at = datetime.now(UTC)
    binding_a = ExecutionBinding(
        id=f"binding_{account_a}",
        account_id=account_a,
        device_workspace_id=workspace_a,
        browser_instance_id=browser_a,
        status="inactive",
        source="runtime-supervisor",
        metadata_json='{"owner":"supervisor"}',
        revision=2,
        created_at=observed_at,
        updated_at=observed_at,
    )
    binding_b = ExecutionBinding(
        id=f"binding_{account_b}",
        account_id=account_b,
        device_workspace_id=workspace_b,
        browser_instance_id=browser_b,
        status="inactive",
        source="runtime-supervisor",
        metadata_json='{"owner":"supervisor"}',
        revision=2,
        created_at=observed_at,
        updated_at=observed_at,
    )
    with session(client) as database:
        database.add_all([binding_a, binding_b])
        database.commit()

    cross_account = client.put(
        f"/api/v1/accounts/{account_a}/connection/binding",
        headers=mutation_headers(
            revision=revision_a,
            idempotency_key="idem_cross_account_environment",
        ),
        json={
            "environmentId": binding_b.id,
            "eligibilityRevision": 6,
        },
    )
    missing_environment = client.put(
        f"/api/v1/accounts/{account_a}/connection/binding",
        headers=mutation_headers(
            revision=revision_a,
            idempotency_key="idem_missing_environment",
        ),
        json={
            "environmentId": "environment_missing",
            "eligibilityRevision": 1,
        },
    )
    stale_evidence = client.put(
        f"/api/v1/accounts/{account_a}/connection/binding",
        headers=mutation_headers(
            revision=revision_a,
            idempotency_key="idem_stale_environment_evidence",
        ),
        json={
            "environmentId": binding_a.id,
            "eligibilityRevision": 5,
        },
    )

    assert cross_account.status_code == 409
    assert error_code(cross_account) == ErrorCode.EXECUTION_ENVIRONMENT_NOT_FOUND
    assert missing_environment.status_code == 409
    assert (
        error_code(missing_environment)
        == ErrorCode.EXECUTION_ENVIRONMENT_NOT_FOUND
    )
    assert stale_evidence.status_code == 409
    assert (
        error_code(stale_evidence)
        == ErrorCode.EXECUTION_ENVIRONMENT_NOT_ELIGIBLE
    )
    with session(client) as database:
        stored_bindings = database.scalars(
            select(ExecutionBinding).where(
                ExecutionBinding.account_id == account_a
            )
        ).all()
        assert [item.status for item in stored_bindings] == ["inactive"]

    bound = client.put(
        f"/api/v1/accounts/{account_a}/connection/binding",
        headers=mutation_headers(
            revision=revision_a,
            idempotency_key="idem_valid_existing_binding",
        ),
        json={
            "environmentId": binding_a.id,
            "eligibilityRevision": 6,
        },
    )

    assert bound.status_code == 200
    connection = bound.json()["data"]
    assert connection["accountId"] == account_a
    assert connection["deviceWorkspace"]["id"] == workspace_a
    assert connection["browserInstance"]["id"] == browser_a
    assert connection["executionBinding"]["deviceWorkspaceId"] == workspace_a
    assert connection["executionBinding"]["browserInstanceId"] == browser_a
    assert bound.json()["meta"]["invalidations"] == [
        "accounts:list",
        f"account:{account_a}:connection",
        f"account:{account_a}:readiness",
        f"account:{account_a}:workspace",
    ]

    with session(client) as database:
        stored_connection = database.scalar(
            select(AccountConnection).where(
                AccountConnection.account_id == account_a
            )
        )
        assert stored_connection is not None
        binding = database.get(
            ExecutionBinding,
            stored_connection.active_execution_binding_id,
        )
        workspace = database.get(DeviceWorkspace, workspace_a)
        browser = database.get(BrowserInstance, browser_a)
        assert binding is not None
        assert binding.id == binding_a.id
        assert binding.source == "runtime-supervisor"
        assert binding.metadata_json == '{"owner":"supervisor"}'
        assert workspace is not None
        assert browser is not None
        assert {
            binding.account_id,
            workspace.account_id,
            browser.account_id,
        } == {account_a}
        assert binding.device_workspace_id == workspace.id
        assert binding.browser_instance_id == browser.id
        assert browser.workspace_id == workspace.id

    unbound = client.delete(
        f"/api/v1/accounts/{account_a}/connection/binding",
        headers=mutation_headers(
            revision=int(bound.json()["meta"]["revision"]),
            idempotency_key="idem_unbind_existing_binding",
        ),
    )

    assert unbound.status_code == 200
    assert unbound.json()["meta"]["invalidations"] == [
        "accounts:list",
        f"account:{account_a}:connection",
        f"account:{account_a}:readiness",
        f"account:{account_a}:workspace",
    ]
    with session(client) as database:
        stored_connection = database.scalar(
            select(AccountConnection).where(
                AccountConnection.account_id == account_a
            )
        )
        assert stored_connection is not None
        assert stored_connection.active_execution_binding_id is None
        assert database.get(ExecutionBinding, binding_a.id) is not None


@pytest.mark.parametrize(
    "path_suffix",
    [
        "/workspace-context",
        "/connection",
        "/positioning",
        "/knowledge",
        "/brand-kit",
        "/publish-defaults",
    ],
)
def test_archived_account_blocks_every_workspace_read_surface(
    licensed_runtime_client: TestClient,
    path_suffix: str,
) -> None:
    client = licensed_runtime_client
    account_id, revision = create_account(
        client,
        name=f"归档限制 {path_suffix}",
        idempotency_key=f"idem_archive_{path_suffix.replace('/', '_')}",
    )
    archive_headers = mutation_headers(
        revision=revision,
        idempotency_key=f"idem_archive_action_{account_id}",
    )
    archive_payload = {"reason": "验证工作区归档门禁"}
    archived = client.post(
        f"/api/v1/accounts/{account_id}/archive",
        headers=archive_headers,
        json=archive_payload,
    )
    assert archived.status_code == 202
    task_id = str(archived.json()["data"]["taskId"])
    completed = wait_account_task(
        client,
        account_id=account_id,
        task_id=task_id,
    )
    assert completed["status"] == "completed"
    assert completed["completionKind"] == "succeeded"
    blocked = client.get(f"/api/v1/accounts/{account_id}{path_suffix}")

    assert blocked.status_code == 409
    assert error_code(blocked) == ErrorCode.ACCOUNT_ARCHIVED


def test_archived_account_restore_requires_current_revision(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    account_id, revision = create_account(
        client,
        name="恢复修订账号",
        idempotency_key="idem_restore_revision_account",
    )
    archived = client.post(
        f"/api/v1/accounts/{account_id}/archive",
        headers=mutation_headers(
            revision=revision,
            idempotency_key="idem_archive_before_restore",
        ),
        json={"reason": "恢复测试"},
    )
    assert archived.status_code == 202
    archive_task = wait_account_task(
        client,
        account_id=account_id,
        task_id=str(archived.json()["data"]["taskId"]),
    )
    assert archive_task["completionKind"] == "succeeded"
    archived_revision = account_revision(client, account_id)
    assert client.get(f"/api/v1/accounts/{account_id}").status_code == 200
    assert client.get(
        f"/api/v1/accounts/{account_id}/health"
    ).status_code == 200
    blocked_mutations = (
        client.post(
            f"/api/v1/accounts/{account_id}/health-checks",
            headers=mutation_headers(
                idempotency_key="idem_archived_health_check"
            ),
            json={},
        ),
        client.post(
            f"/api/v1/accounts/{account_id}/knowledge/sources",
            headers=mutation_headers(
                idempotency_key="idem_archived_knowledge_source"
            ),
            json={
                "kind": "text",
                "sourceMode": "text",
                "title": "归档后禁止写入",
                "text": "不得持久化",
            },
        ),
        client.put(
            f"/api/v1/accounts/{account_id}/connection/binding",
            headers=mutation_headers(
                revision=archived_revision,
                idempotency_key="idem_archived_connection_binding",
            ),
            json={
                "deviceWorkspaceId": "workspace_archived",
                "browserInstanceId": "browser_archived",
            },
        ),
        client.put(
            f"/api/v1/accounts/{account_id}/publish-defaults",
            headers=mutation_headers(revision=archived_revision),
            json={
                "timezone": "UTC",
                "privacyLevel": "private",
                "allowComments": False,
                "allowDuet": False,
                "allowStitch": False,
                "captionRules": {},
            },
        ),
    )
    assert all(item.status_code == 409 for item in blocked_mutations)
    assert all(
        error_code(item) == ErrorCode.ACCOUNT_ARCHIVED
        for item in blocked_mutations
    )

    stale = client.post(
        f"/api/v1/accounts/{account_id}/restore",
        headers=mutation_headers(
            revision=revision,
            idempotency_key="idem_stale_restore",
        ),
        json={"checks": ["connection"]},
    )
    accepted = client.post(
        f"/api/v1/accounts/{account_id}/restore",
        headers=mutation_headers(
            revision=archived_revision,
            idempotency_key="idem_current_restore",
        ),
        json={"checks": ["connection"]},
    )

    assert stale.status_code == 412
    assert error_code(stale) == ErrorCode.REVISION_CONFLICT
    assert accepted.status_code == 202
    task_id = accepted.json()["data"]["taskId"]
    with session(client) as database:
        task = database.get(RuntimeTask, task_id)
        assert task is not None
        snapshot = json.loads(task.config_snapshot_json)
        assert snapshot["payload"]["expectedRevision"] == archived_revision

    draft_id, draft_revision = create_account(
        client,
        name="未归档账号",
        idempotency_key="idem_non_archived_restore_account",
    )
    rejected = client.post(
        f"/api/v1/accounts/{draft_id}/restore",
        headers=mutation_headers(
            revision=draft_revision,
            idempotency_key="idem_non_archived_restore",
        ),
        json={},
    )
    assert rejected.status_code == 409
    assert error_code(rejected) == ErrorCode.ACCOUNT_STATE_TRANSITION_INVALID
