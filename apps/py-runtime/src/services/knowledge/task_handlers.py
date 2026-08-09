from __future__ import annotations

import asyncio
from collections.abc import Mapping

from errors import DomainError, ErrorCode
from services.knowledge.index_executor import KnowledgeIndexExecutor
from services.knowledge.index_policy import (
    knowledge_policy_from_snapshot,
)
from services.tasks.errors import task_snapshot_invalid
from services.tasks.types import (
    JsonValue,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskHandler,
)

KNOWLEDGE_INDEX_TASK_TYPE = "knowledge.index"


def build_knowledge_index_handler(
    executor: KnowledgeIndexExecutor,
) -> TaskHandler:
    async def handle(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        account_id = _require_account_id(context)
        source_ids = _parse_source_ids(payload)
        policy = knowledge_policy_from_snapshot(payload.get("policy"))
        plan = await asyncio.to_thread(
            executor.plan,
            account_id,
            source_ids,
        )
        failures: list[DomainError] = []
        total = len(plan.source_ids)
        for index, source_id in enumerate(plan.source_ids):
            context.raise_if_cancelled()
            await context.report_progress(index / total)
            try:
                await asyncio.to_thread(
                    executor.index_source,
                    account_id,
                    source_id,
                    task_id=context.task_id,
                    cancel_check=context.raise_if_cancelled,
                    policy=policy,
                )
            except DomainError as exc:
                failures.append(exc)
        context.raise_if_cancelled()
        await context.report_progress(1.0)
        if failures:
            first = failures[0]
            raise DomainError(
                first.error_code,
                "部分知识来源索引失败，请查看来源状态和诊断日志",
                status_code=first.status_code,
                loggable=True,
                meta={"failedCount": len(failures)},
            )
        return TaskExecutionResult(
            result_ref=(
                f"knowledge://{account_id}/index-jobs/{context.task_id}"
            )
        )

    return handle


def _require_account_id(context: TaskExecutionContext) -> str:
    account_id = context.account_id
    if account_id is None:
        raise DomainError(
            ErrorCode.ACCOUNT_SCOPE_MISMATCH,
            "知识索引任务缺少账号范围",
            status_code=403,
        )
    return account_id


def _parse_source_ids(
    payload: Mapping[str, JsonValue],
) -> tuple[str, ...]:
    raw = payload.get("sourceIds")
    if not isinstance(raw, list) or not raw or len(raw) > 10_000:
        raise task_snapshot_invalid("知识索引任务来源清单无效")
    source_ids = tuple(
        item
        for item in raw
        if isinstance(item, str) and item.strip()
    )
    if (
        len(source_ids) != len(raw)
        or len(set(source_ids)) != len(source_ids)
    ):
        raise task_snapshot_invalid(
            "知识索引任务来源清单包含空值或重复项"
        )
    return source_ids
