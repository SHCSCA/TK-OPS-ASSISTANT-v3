from __future__ import annotations

import asyncio
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from errors import DomainError, ErrorCode
from repositories.knowledge_v1_repository import KnowledgeV1Repository
from schemas.v1.knowledge import KnowledgeIndexInput
from services.knowledge.content_store import KnowledgeContentStore
from services.knowledge.index_policy import KnowledgeIndexPolicy
from services.knowledge.index_types import KnowledgeIndexPlan
from services.knowledge.reconciliation import KnowledgeIndexReconciler
from services.knowledge.source_validation import normalize_public_https_url
from services.knowledge.task_handlers import KNOWLEDGE_INDEX_TASK_TYPE
from services.knowledge.task_registration import (
    register_knowledge_index_handler,
)
from services.knowledge.task_submission import (
    KnowledgeIndexSubmissionService,
)
from services.knowledge.support import (
    knowledge_invalidations,
    knowledge_status_from_source_counts,
)
from services.knowledge.url_fetcher import SecureKnowledgeUrlFetcher
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.types import TaskResumePolicy


def test_inline_content_uses_account_knowledge_root_and_real_hash(
    tmp_path: Path,
) -> None:
    store = KnowledgeContentStore(tmp_path / "accounts")
    stored = store.store_text("acc_a", "ksrc_a", "真实知识正文")

    assert stored.content_hash == hashlib.sha256(
        "真实知识正文".encode("utf-8")
    ).hexdigest()
    assert store.read_bytes("acc_a", stored.reference) == (
        "真实知识正文".encode("utf-8")
    )
    assert (
        tmp_path
        / "accounts"
        / "acc_a"
        / "knowledge"
        / "ksrc_a.txt"
    ).is_file()

    with pytest.raises(DomainError) as exc_info:
        store.read_bytes("acc_b", stored.reference)
    assert exc_info.value.error_code == ErrorCode.CONTROLLED_FILE_REF_INVALID


def test_content_reconciliation_only_removes_strict_unreferenced_text(
    tmp_path: Path,
) -> None:
    root = tmp_path / "accounts"
    store = KnowledgeContentStore(root)
    protected = store.store_text("acc_a", "ksrc_protected", "保留正文")
    store.store_text("acc_a", "ksrc_orphaned", "孤儿正文")
    unsafe_name = root / "acc_a" / "knowledge" / "unsafe name.txt"
    unsafe_name.write_text("不符合命名规则", encoding="utf-8")
    nested = root / "acc_a" / "knowledge" / "nested"
    nested.mkdir()
    nested_file = nested / "ksrc_nested.txt"
    nested_file.write_text("不在生成层级", encoding="utf-8")

    report = store.reconcile_orphaned_text_files(
        [("acc_a", protected.reference)]
    )

    assert report.scanned_candidate_count == 2
    assert report.protected_file_count == 1
    assert report.removed_orphan_count == 1
    assert store.read_bytes("acc_a", protected.reference) == (
        "保留正文".encode("utf-8")
    )
    assert not (
        root / "acc_a" / "knowledge" / "ksrc_orphaned.txt"
    ).exists()
    assert unsafe_name.is_file()
    assert nested_file.is_file()


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/source",
        "https://127.0.0.1/source",
        "https://10.0.0.8/source",
        "https://user:secret@example.com/source",
    ],
)
def test_url_source_rejects_unsafe_input(url: str) -> None:
    with pytest.raises(DomainError):
        normalize_public_https_url(url)


def test_url_fetcher_rejects_private_dns_result_before_request() -> None:
    fetcher = SecureKnowledgeUrlFetcher(
        address_resolver=lambda _host, _port: ("192.168.1.5",)
    )
    with pytest.raises(DomainError) as exc_info:
        fetcher.fetch(
            "https://example.com/source",
            policy=_policy(),
        )
    assert exc_info.value.error_code == ErrorCode.KNOWLEDGE_INDEX_FAILED


def test_knowledge_index_handler_is_resumable_and_account_singleton() -> None:
    registry = TaskHandlerRegistry()
    register_knowledge_index_handler(
        registry,
        executor=SimpleNamespace(),
        timeout_seconds=30,
    )

    definition = registry.require(KNOWLEDGE_INDEX_TASK_TYPE)
    assert definition.allowed_snapshot_fields == frozenset(
        {"sourceIds", "policy"}
    )
    assert definition.resume_policy is TaskResumePolicy.RESUME
    assert definition.cancellable is True
    assert definition.single_active_per_scope is True


def test_submission_freezes_exact_sources_and_safe_policy() -> None:
    coordinator = _Coordinator()
    service = KnowledgeIndexSubmissionService(
        SimpleNamespace(),
        coordinator=coordinator,
        policy_provider=_policy,
    )
    service._state = _PlanState()  # type: ignore[attr-defined]

    accepted = asyncio.run(
        service.submit(
            "acc_a",
            KnowledgeIndexInput(sourceIds=["ksrc_1", "ksrc_2"]),
            idempotency_key="idem-knowledge-index",
            request_id="req_knowledge_index",
            operation_id="op_knowledge_index",
        )
    )

    assert accepted.accountId == "acc_a"
    assert coordinator.payload == {
        "sourceIds": ["ksrc_1", "ksrc_2"],
        "policy": {
            "maxSourceBytes": 1024 * 1024,
            "urlTimeoutSeconds": 5,
            "maxRedirects": 2,
            "configRevision": 7,
        },
    }
    serialized = repr(coordinator.payload)
    assert "正文" not in serialized
    assert "sourceUrl" not in serialized
    assert "controlledFileRef" not in serialized


def test_repository_source_access_has_explicit_account_predicate() -> None:
    for method_name in (
        "get_source",
        "get_sources",
        "list_sources",
        "list_sources_for_index",
        "list_sources_with_status",
        "list_text_source_references",
        "first_source_with_status",
        "source_state_counts",
        "set_source_index_state",
    ):
        source = inspect.getsource(
            getattr(KnowledgeV1Repository, method_name)
        )
        assert "account_id" in source
        if method_name not in {"set_source_index_state"}:
            assert "KnowledgeSource.account_id == account_id" in source
    reference_source = inspect.getsource(
        KnowledgeV1Repository.list_text_source_references
    )
    assert 'KnowledgeSource.source_mode == "text"' in reference_source
    assert "deleted_at" not in reference_source


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ({}, "empty"),
        ({"ready": 1}, "ready"),
        ({"pending": 1}, "stale"),
        ({"stale": 1, "ready": 1}, "stale"),
        ({"failed": 1, "ready": 1}, "attention"),
        ({"indexing": 1, "failed": 1}, "indexing"),
    ],
)
def test_knowledge_base_status_tracks_active_source_states(
    counts: dict[str, int],
    expected: str,
) -> None:
    assert knowledge_status_from_source_counts(counts) == expected


def test_knowledge_source_state_uses_complete_shared_invalidations() -> None:
    from services.knowledge.index_events import (
        append_knowledge_index_event,
    )
    from services.knowledge.sources import KnowledgeSourceService

    account_id = "acc_invalidation_contract"
    assert knowledge_invalidations(account_id) == [
        "accounts:list",
        f"account:{account_id}:knowledge",
        f"account:{account_id}:knowledge:sources",
        f"account:{account_id}:workspace",
        f"account:{account_id}:readiness",
    ]
    assert "knowledge_invalidations(account_id)" in inspect.getsource(
        KnowledgeSourceService._remove
    )
    assert "knowledge_invalidations(account_id)" in inspect.getsource(
        append_knowledge_index_event
    )


def test_source_commands_update_knowledge_base_in_same_module() -> None:
    from services.knowledge.sources import KnowledgeSourceService

    source = inspect.getsource(KnowledgeSourceService)
    assert source.count("set_base_index_state") >= 2
    assert "knowledgeStatus" in source
    assert source.count("self._lifecycle.update") >= 2


def test_index_state_changes_synchronize_account_lifecycle() -> None:
    from services.knowledge.index_state import KnowledgeIndexStateStore

    source = inspect.getsource(KnowledgeIndexStateStore)
    assert "self._lifecycle.update" in source
    assert "知识索引生命周期同步器尚未装配" in source


def test_active_source_subset_does_not_hide_same_account_orphan() -> None:
    reconciler = KnowledgeIndexReconciler(
        SimpleNamespace(),
        policy_provider=_policy,
        lifecycle_synchronizer=Mock(),
    )
    state = _ReconciliationState()
    setattr(reconciler, "_state", state)
    setattr(
        reconciler,
        "_orphan_source_ids",
        lambda account_id: (
            "ksrc_active",
            "ksrc_orphaned",
        ),
    )

    report = reconciler.reconcile(
        ["acc_a"],
        active_source_ids_by_account={
            "acc_a": {"ksrc_active"},
        },
    )

    assert state.marked == [("acc_a", "ksrc_orphaned", 7)]
    assert report.checked_account_count == 1
    assert report.protected_active_source_count == 1
    assert report.reconciled_source_count == 1


def _policy() -> KnowledgeIndexPolicy:
    return KnowledgeIndexPolicy(
        max_source_bytes=1024 * 1024,
        url_timeout_seconds=5,
        max_redirects=2,
        config_revision=7,
    )


class _PlanState:
    def plan(
        self,
        account_id: str,
        source_ids: tuple[str, ...] | None,
    ) -> KnowledgeIndexPlan:
        assert account_id == "acc_a"
        assert source_ids == ("ksrc_1", "ksrc_2")
        return KnowledgeIndexPlan(
            account_id=account_id,
            source_ids=source_ids,
        )


class _Coordinator:
    payload: dict[str, object] | None = None

    async def submit_account_task(
        self,
        account_id: str,
        *,
        task_type: str,
        payload: dict[str, object],
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> SimpleNamespace:
        assert account_id == "acc_a"
        assert task_type == KNOWLEDGE_INDEX_TASK_TYPE
        assert idempotency_key
        assert request_id
        assert operation_id
        self.payload = payload
        return SimpleNamespace(
            id="task_knowledge_index",
            task_type=task_type,
            cancellable=True,
            created_at="2026-07-26T00:00:00Z",
        )


class _ReconciliationState:
    def __init__(self) -> None:
        self.marked: list[tuple[str, str, int]] = []

    def mark_orphaned(
        self,
        account_id: str,
        source_id: str,
        *,
        config_revision: int,
    ) -> object:
        self.marked.append(
            (account_id, source_id, config_revision)
        )
        return object()
