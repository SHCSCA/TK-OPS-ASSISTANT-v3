from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from domain.models.account import Account
from domain.models.knowledge import AccountKnowledgeBase, KnowledgeSource
from domain.models.runtime_event import RuntimeEvent
from domain.models.runtime_task import RuntimeTask
from errors import DomainError, ErrorCode
from services.events import AccountScopeMismatchError, TopicCursor
from tests.runtime.p0c_account_integration_support import (
    account_revision,
    create_account,
    error_code,
    mark_source_ready,
    mutation_headers,
    session,
)


def test_source_mutations_sync_aggregate_and_keep_task_snapshot_safe(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_id, initial_revision = create_account(
        client,
        name="知识事务账号",
        idempotency_key="idem_knowledge_transaction_account",
    )
    removable = _create_text_source(
        client,
        account_id=account_id,
        title="待移除来源",
        text="待移除知识正文",
        idempotency_key="idem_removable_source",
    )
    created_revision = int(removable["meta"]["revision"])
    source_id = str(removable["data"]["id"])
    assert created_revision == initial_revision + 1

    with session(client) as database:
        account = database.get(Account, account_id)
        knowledge = database.scalar(
            select(AccountKnowledgeBase).where(
                AccountKnowledgeBase.account_id == account_id
            )
        )
        created_event = database.scalar(
            select(RuntimeEvent).where(
                RuntimeEvent.account_id == account_id,
                RuntimeEvent.event_type == "knowledge.source.created",
                RuntimeEvent.aggregate_id == source_id,
            )
        )
        assert account is not None
        assert knowledge is not None
        assert created_event is not None
        assert int(account.revision) == created_revision
        assert knowledge.status == "stale"
        assert int(knowledge.revision) == 2
        assert created_event.revision == created_revision

    removed = client.delete(
        f"/api/v1/accounts/{account_id}/knowledge/sources/{source_id}",
        headers=mutation_headers(
            revision=created_revision,
            idempotency_key="idem_remove_source",
        ),
    )

    assert removed.status_code == 200
    removed_payload = removed.json()
    removed_revision = int(removed_payload["meta"]["revision"])
    assert removed_payload["data"]["status"] == "removed"
    assert removed_revision == created_revision + 1
    with session(client) as database:
        account = database.get(Account, account_id)
        source = database.get(KnowledgeSource, source_id)
        knowledge = database.scalar(
            select(AccountKnowledgeBase).where(
                AccountKnowledgeBase.account_id == account_id
            )
        )
        removed_event = database.scalar(
            select(RuntimeEvent).where(
                RuntimeEvent.account_id == account_id,
                RuntimeEvent.event_type == "knowledge.source.removed",
                RuntimeEvent.aggregate_id == source_id,
            )
        )
        assert account is not None
        assert source is not None
        assert knowledge is not None
        assert removed_event is not None
        assert int(account.revision) == removed_revision
        assert source.deleted_at is not None
        assert knowledge.status == "empty"
        assert int(knowledge.revision) == 3
        assert removed_event.revision == removed_revision

    private_text = "账号私有知识正文：只用于验证真实文件与摘要"
    indexed = _create_text_source(
        client,
        account_id=account_id,
        title="真实内联知识",
        text=private_text,
        idempotency_key="idem_private_text_source",
    )
    indexed_source_id = str(indexed["data"]["id"])
    content_path = (
        runtime_data_dir
        / "accounts"
        / account_id
        / "knowledge"
        / f"{indexed_source_id}.txt"
    )
    content_bytes = content_path.read_bytes()
    expected_hash = hashlib.sha256(private_text.encode("utf-8")).hexdigest()
    assert content_bytes == private_text.encode("utf-8")

    with session(client) as database:
        stored_source = database.get(KnowledgeSource, indexed_source_id)
        assert stored_source is not None
        metadata = json.loads(stored_source.metadata_json)
        assert metadata["expectedContentHash"] == expected_hash

    submitted = client.post(
        f"/api/v1/accounts/{account_id}/knowledge/index-jobs",
        headers=mutation_headers(idempotency_key="idem_private_text_index"),
        json={"sourceIds": [indexed_source_id]},
    )

    assert submitted.status_code == 202
    task_id = str(submitted.json()["data"]["taskId"])
    with session(client) as database:
        task = database.get(RuntimeTask, task_id)
        assert task is not None
        snapshot = json.loads(task.config_snapshot_json)
        assert snapshot["payload"]["sourceIds"] == [indexed_source_id]
        serialized = task.config_snapshot_json
        assert private_text not in serialized
        assert str(content_path) not in serialized
        assert "knowledge-content://" not in serialized
        assert "sourceUrl" not in serialized
        assert "controlledFileRef" not in serialized
        account_events = database.scalars(
            select(RuntimeEvent).where(
                RuntimeEvent.account_id == account_id
            )
        ).all()
        assert private_text not in repr(
            [event.payload_json for event in account_events]
        )


def test_cross_account_sources_snapshots_cursors_tasks_and_events_are_hidden(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    account_a, _ = create_account(
        client,
        name="知识隔离 A",
        idempotency_key="idem_knowledge_scope_a",
    )
    account_b, _ = create_account(
        client,
        name="知识隔离 B",
        idempotency_key="idem_knowledge_scope_b",
    )
    source_a1 = _create_text_source(
        client,
        account_id=account_a,
        title="A 来源一",
        text="A 私有正文一",
        idempotency_key="idem_scope_a_source_one",
    )
    _create_text_source(
        client,
        account_id=account_a,
        title="A 来源二",
        text="A 私有正文二",
        idempotency_key="idem_scope_a_source_two",
    )
    source_b = _create_text_source(
        client,
        account_id=account_b,
        title="B 来源",
        text="B 私有正文",
        idempotency_key="idem_scope_b_source",
    )
    source_a_id = str(source_a1["data"]["id"])
    source_b_id = str(source_b["data"]["id"])

    first_page = client.get(
        f"/api/v1/accounts/{account_a}/knowledge/sources",
        params={"limit": 1},
    )
    cursor = first_page.json()["meta"]["nextCursor"]
    assert isinstance(cursor, str)
    cross_cursor = client.get(
        f"/api/v1/accounts/{account_b}/knowledge/sources",
        params={"limit": 1, "cursor": cursor},
    )
    assert cross_cursor.status_code == 422
    assert error_code(cross_cursor) == ErrorCode.REQUEST_VALIDATION_FAILED
    assert cross_cursor.json()["fieldErrors"] == [
        {
            "field": "cursor",
            "code": "invalid_scoped_cursor",
            "message": "请重新从当前资源与筛选条件的第一页加载",
        }
    ]

    cross_remove = client.delete(
        (
            f"/api/v1/accounts/{account_b}/knowledge/"
            f"sources/{source_a_id}"
        ),
        headers=mutation_headers(
            revision=account_revision(client, account_b),
            idempotency_key="idem_cross_account_remove",
        ),
    )
    cross_index = client.post(
        f"/api/v1/accounts/{account_b}/knowledge/index-jobs",
        headers=mutation_headers(idempotency_key="idem_cross_account_index"),
        json={"sourceIds": [source_a_id]},
    )
    assert cross_remove.status_code == 404
    assert error_code(cross_remove) == ErrorCode.KNOWLEDGE_SOURCE_NOT_FOUND
    assert cross_index.status_code == 422
    assert error_code(cross_index) == ErrorCode.KNOWLEDGE_SOURCE_INVALID

    mark_source_ready(
        client,
        account_id=account_a,
        source_id=source_a_id,
        content="A 私有正文一",
    )
    snapshot = client.post(
        f"/api/v1/accounts/{account_a}/knowledge/snapshots",
        headers=mutation_headers(idempotency_key="idem_scope_a_snapshot"),
        json={"sourceIds": [source_a_id], "label": "A 私有快照"},
    )
    assert snapshot.status_code == 201
    snapshot_id = str(snapshot.json()["data"]["id"])
    hidden_snapshot = client.get(
        (
            f"/api/v1/accounts/{account_b}/knowledge/"
            f"snapshots/{snapshot_id}"
        )
    )
    assert hidden_snapshot.status_code == 404
    assert error_code(
        hidden_snapshot
    ) == ErrorCode.KNOWLEDGE_SNAPSHOT_NOT_FOUND
    listed_b = client.get(
        f"/api/v1/accounts/{account_b}/knowledge/sources"
    )
    assert {
        item["id"] for item in listed_b.json()["data"]["items"]
    } == {source_b_id}

    index_b = client.post(
        f"/api/v1/accounts/{account_b}/knowledge/index-jobs",
        headers=mutation_headers(idempotency_key="idem_scope_b_index"),
        json={"sourceIds": [source_b_id]},
    )
    assert index_b.status_code == 202
    task_id = str(index_b.json()["data"]["taskId"])
    task_service = (
        client.app.state.runtime_container.kernel.task_coordinator._task_service
    )
    with pytest.raises(DomainError) as task_error:
        task_service.get_account_task(account_a, task_id)
    assert task_error.value.error_code == ErrorCode.ACCOUNT_SCOPE_MISMATCH

    with session(client) as database:
        queued_event = database.scalar(
            select(RuntimeEvent).where(
                RuntimeEvent.task_id == task_id,
                RuntimeEvent.event_type == "task.queued",
            )
        )
        assert queued_event is not None
        assert queued_event.account_id == account_b
        assert queued_event.topic == f"account:{account_b}:tasks"
        queued_event_id = queued_event.event_id
        queued_sequence = int(queued_event.sequence)
    event_service = client.app.state.runtime_event_service
    with pytest.raises(AccountScopeMismatchError):
        event_service.resolve_replay(
            TopicCursor(
                topic=f"account:{account_a}:tasks",
                last_event_id=queued_event_id,
                after_sequence=queued_sequence,
            )
        )


def _create_text_source(
    client: TestClient,
    *,
    account_id: str,
    title: str,
    text: str,
    idempotency_key: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/accounts/{account_id}/knowledge/sources",
        headers=mutation_headers(idempotency_key=idempotency_key),
        json={
            "kind": "text",
            "sourceMode": "text",
            "title": title,
            "text": text,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
