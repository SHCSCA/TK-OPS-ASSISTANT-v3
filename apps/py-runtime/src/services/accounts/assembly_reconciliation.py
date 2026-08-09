from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping

from common.identifiers import is_stable_id
from common.pagination import CursorPosition
from services.accounts.unit_of_work import AccountUnitOfWork
from services.knowledge import KNOWLEDGE_INDEX_TASK_TYPE
from services.tasks.snapshot import TaskSnapshotPolicy
from services.tasks.types import RuntimeTaskRecord

log = logging.getLogger(__name__)
_RECONCILIATION_PAGE_SIZE = 200


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
