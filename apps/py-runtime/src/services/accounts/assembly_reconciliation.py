from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from common.identifiers import is_stable_id
from common.pagination import CursorPosition
from errors import DomainError, ErrorCode
from services.accounts.unit_of_work import AccountUnitOfWork
from services.config import ConfigBusService
from services.knowledge import KNOWLEDGE_INDEX_TASK_TYPE
from services.knowledge import KnowledgeContentStore, KnowledgeIndexReconciler
from services.tasks.snapshot import TaskSnapshotPolicy
from services.tasks.types import RuntimeTaskRecord

log = logging.getLogger(__name__)
_RECONCILIATION_PAGE_SIZE = 200


@dataclass(frozen=True, slots=True)
class KnowledgeStartupReconciliationReport:
    checked_account_count: int
    protected_active_source_count: int
    reconciled_source_count: int
    scanned_content_file_count: int
    protected_content_file_count: int
    removed_orphan_content_file_count: int


def active_knowledge_source_ids(
    records: Iterable[RuntimeTaskRecord],
    *,
    snapshot_policy: TaskSnapshotPolicy,
) -> dict[str, frozenset[str]]:
    active: dict[str, set[str]] = {}
    for record in records:
        if record.task_type != KNOWLEDGE_INDEX_TASK_TYPE:
            continue
        try:
            account_id = record.account_id
            if (
                not isinstance(account_id, str)
                or not is_stable_id(account_id)
            ):
                raise ValueError("知识索引任务账号范围无效")
            snapshot = snapshot_policy.load(
                record.config_snapshot_json,
                expected_handler_version=record.handler_version,
            )
            if (
                snapshot.key_hash != record.idempotency_key_hash
                or snapshot.request_hash != record.request_hash
            ):
                raise ValueError("知识索引任务快照摘要不一致")
            source_ids = source_ids_from_snapshot(snapshot.payload)
        except Exception as exc:
            log.exception(
                "解析非终态知识索引任务快照失败",
                extra={
                    "task_id": record.id,
                    "account_id": record.account_id,
                    "task_type": record.task_type,
                },
            )
            raise RuntimeError(
                "非终态知识索引任务快照异常，已停止启动对账"
            ) from exc
        active.setdefault(account_id, set()).update(source_ids)
    return {
        account_id: frozenset(source_ids)
        for account_id, source_ids in active.items()
    }


def source_ids_from_snapshot(
    payload: Mapping[str, object],
) -> tuple[str, ...]:
    raw = payload.get("sourceIds")
    if not isinstance(raw, list) or not raw or len(raw) > 10_000:
        raise ValueError("知识索引任务来源清单无效")
    source_ids = tuple(
        item
        for item in raw
        if isinstance(item, str) and is_stable_id(item)
    )
    if (
        len(source_ids) != len(raw)
        or len(set(source_ids)) != len(source_ids)
    ):
        raise ValueError("知识索引任务来源清单包含空值或重复项")
    return source_ids


def list_text_source_references(
    unit_of_work: AccountUnitOfWork,
    account_ids: Iterable[str],
) -> tuple[tuple[str, str], ...]:
    references: list[tuple[str, str]] = []
    with unit_of_work.read() as transaction:
        for account_id in account_ids:
            references.extend(
                (account_id, reference)
                for reference in (
                    transaction.knowledge.list_text_source_references(
                        account_id,
                        transaction.session,
                    )
                )
            )
    return tuple(references)


def list_account_ids(
    unit_of_work: AccountUnitOfWork,
) -> tuple[str, ...]:
    account_ids: list[str] = []
    cursor: CursorPosition | None = None
    with unit_of_work.read() as transaction:
        while True:
            page = transaction.accounts.list_page(
                transaction.session,
                limit=_RECONCILIATION_PAGE_SIZE,
                cursor=cursor,
                query=None,
                status=None,
            )
            account_ids.extend(account.id for account in page.items)
            cursor = page.next_position
            if cursor is None:
                break
    return tuple(account_ids)


def reconcile_knowledge_index(
    *,
    unit_of_work: AccountUnitOfWork,
    task_repository: object,
    reconciler: KnowledgeIndexReconciler,
    snapshot_policy: TaskSnapshotPolicy,
    content_store: KnowledgeContentStore,
) -> KnowledgeStartupReconciliationReport:
    account_ids = list_account_ids(unit_of_work)
    active_source_ids = active_knowledge_source_ids(
        task_repository.list_non_terminal(),
        snapshot_policy=snapshot_policy,
    )
    referenced_sources = list_text_source_references(
        unit_of_work,
        account_ids,
    )
    content_report = content_store.reconcile_orphaned_text_files(
        referenced_sources
    )
    index_report = reconciler.reconcile(
        account_ids,
        active_source_ids_by_account=active_source_ids,
    )
    report = KnowledgeStartupReconciliationReport(
        checked_account_count=index_report.checked_account_count,
        protected_active_source_count=index_report.protected_active_source_count,
        reconciled_source_count=index_report.reconciled_source_count,
        scanned_content_file_count=content_report.scanned_candidate_count,
        protected_content_file_count=content_report.protected_file_count,
        removed_orphan_content_file_count=content_report.removed_orphan_count,
    )
    log.info(
        "知识索引与正文孤儿状态对账完成",
        extra={
            "checked_account_count": report.checked_account_count,
            "protected_active_source_count": report.protected_active_source_count,
            "reconciled_source_count": report.reconciled_source_count,
            "scanned_content_file_count": report.scanned_content_file_count,
            "protected_content_file_count": report.protected_content_file_count,
            "removed_orphan_content_file_count": report.removed_orphan_content_file_count,
        },
    )
    return report


def task_snapshot_policy(
    config_bus_service: ConfigBusService,
) -> TaskSnapshotPolicy:
    snapshot = config_bus_service.get()
    value = snapshot.values.get("runtime.taskSnapshotMaxBytes")
    if not isinstance(value, int) or isinstance(value, bool):
        raise _task_snapshot_config_error(snapshot.revision)
    try:
        return TaskSnapshotPolicy(max_bytes=value)
    except ValueError as exc:
        raise _task_snapshot_config_error(snapshot.revision) from exc


def _task_snapshot_config_error(config_revision: int) -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        "任务快照大小配置异常，请查看诊断日志",
        status_code=500,
        loggable=True,
        log_context={
            "operation": "tasks.resolve_snapshot_policy",
            "configRevision": config_revision,
        },
    )
