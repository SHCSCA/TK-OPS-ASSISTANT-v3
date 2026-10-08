from __future__ import annotations

from collections.abc import Mapping

from errors import DomainError, ErrorCode
from services.tasks.errors import task_snapshot_invalid
from services.tasks.types import (
    JsonValue,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskHandler,
)

from .creation import AI_EXECUTION_TASK_TYPE
from .executor import AIExecutionExecutor


def build_ai_execution_handler(executor: AIExecutionExecutor) -> TaskHandler:
    async def handle(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        account_id = _require_account_id(context)
        execution_id = _require_text(payload, "executionId")
        snapshot_hash = _require_hash(payload, "snapshotHash")
        await executor.execute(
            context,
            account_id=account_id,
            execution_id=execution_id,
            expected_snapshot_hash=snapshot_hash,
        )
        return TaskExecutionResult(
            result_ref=f"ai-execution://{account_id}/{execution_id}"
        )

    return handle


def _require_account_id(context: TaskExecutionContext) -> str:
    if context.account_id is None:
        raise DomainError(
            ErrorCode.ACCOUNT_SCOPE_MISMATCH,
            "AI 执行任务缺少账号范围",
            status_code=403,
        )
    return context.account_id


def _require_text(payload: Mapping[str, JsonValue], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise task_snapshot_invalid(
            f"AI 执行任务字段 {field} 无效",
            stored_snapshot=True,
        )
    return value


def _require_hash(payload: Mapping[str, JsonValue], field: str) -> str:
    value = _require_text(payload, field)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise task_snapshot_invalid(
            f"AI 执行任务字段 {field} 不是有效摘要",
            stored_snapshot=True,
        )
    return value


__all__ = ["AI_EXECUTION_TASK_TYPE", "build_ai_execution_handler"]
