from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import TypeVar

from errors import DomainError, ErrorCode
from services.ai_execution_v1.types import CancellationToken
from services.tasks.errors import (
    TaskCancellationRequested,
    task_snapshot_invalid,
)
from services.tasks.types import (
    JsonValue,
    TaskCommitCoordinator,
    TaskCommitDecision,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskHandler,
)

from .constants import CAPABILITY_KEYS
from .task_execution import AIConfigurationTaskExecutor

log = logging.getLogger(__name__)
_T = TypeVar("_T")


def build_provider_health_handler(
    executor: AIConfigurationTaskExecutor,
) -> TaskHandler:
    async def handle(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        _require_system_scope(context)
        provider_id = _require_id(payload, "providerId")
        provider_revision = _require_revision(
            payload,
            "providerRevision",
        )
        force = _require_bool(payload, "force")
        stages = _require_stages(payload)
        return await _run_coordinated(
            context,
            resource_id=provider_id,
            operation=lambda coordinator, token: executor.check_provider_health(
                provider_id,
                expected_revision=provider_revision,
                force=force,
                stages=stages,
                cancel_token=token,
                task_id=context.task_id,
                commit_coordinator=coordinator,
            ),
        )

    return handle


def build_provider_model_discovery_handler(
    executor: AIConfigurationTaskExecutor,
) -> TaskHandler:
    async def handle(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        _require_system_scope(context)
        provider_id = _require_id(payload, "providerId")
        provider_revision = _require_revision(
            payload,
            "providerRevision",
        )
        replace_missing = _require_bool(payload, "replaceMissing")
        if replace_missing:
            raise task_snapshot_invalid(
                "P0 模型发现快照不允许替换缺失模型",
                stored_snapshot=True,
            )
        return await _run_coordinated(
            context,
            resource_id=provider_id,
            operation=lambda coordinator, token: (
                executor.discover_provider_models(
                    provider_id,
                    expected_revision=provider_revision,
                    replace_missing=replace_missing,
                    cancel_token=token,
                    task_id=context.task_id,
                    commit_coordinator=coordinator,
                )
            ),
        )

    return handle


def build_model_capability_handler(
    executor: AIConfigurationTaskExecutor,
) -> TaskHandler:
    async def handle(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        _require_system_scope(context)
        model_id = _require_id(payload, "modelProfileId")
        model_revision = _require_revision(payload, "modelRevision")
        provider_revision = _require_revision(
            payload,
            "providerRevision",
        )
        capability_keys = _require_capability_keys(payload)
        force = _require_bool(payload, "force")
        mode = _require_mode(payload)
        return await _run_coordinated(
            context,
            resource_id=model_id,
            operation=lambda coordinator, token: (
                executor.check_model_capabilities(
                    model_id,
                    expected_model_revision=model_revision,
                    expected_provider_revision=provider_revision,
                    capability_keys=capability_keys,
                    force=force,
                    mode=mode,
                    cancel_token=token,
                    task_id=context.task_id,
                    commit_coordinator=coordinator,
                )
            ),
        )

    return handle


async def _run_coordinated(
    context: TaskExecutionContext,
    *,
    resource_id: str,
    operation: Callable[[TaskCommitCoordinator, CancellationToken], str],
) -> TaskExecutionResult:
    coordinator = context.enable_commit_coordination()
    cancel_token = CancellationToken()
    context.raise_if_cancelled()
    await context.report_progress(0.1)
    worker = asyncio.create_task(
        asyncio.to_thread(operation, coordinator, cancel_token)
    )
    try:
        result_ref = await asyncio.shield(worker)
        context.raise_if_cancelled()
        await context.report_progress(1.0)
    except (asyncio.CancelledError, TaskCancellationRequested):
        cancel_token.cancel()
        decision = await _request_termination(coordinator)
        if decision is TaskCommitDecision.TERMINATION_WON:
            worker.add_done_callback(_consume_terminated_worker)
            log.info(
                "AI 配置任务终止先于业务提交生效",
                extra={
                    "task_id": context.task_id,
                    "resource_id": resource_id,
                },
            )
            raise
        result_ref = await _await_commit_winner(worker)
        log.info(
            "AI 配置任务业务提交先于终止请求生效",
            extra={
                "task_id": context.task_id,
                "resource_id": resource_id,
            },
        )
    return TaskExecutionResult(result_ref=result_ref)


async def _request_termination(
    coordinator: TaskCommitCoordinator,
) -> TaskCommitDecision:
    decision = asyncio.create_task(
        asyncio.to_thread(coordinator.request_termination)
    )
    return await _await_commit_winner(decision)


async def _await_commit_winner(worker: asyncio.Task[_T]) -> _T:
    while True:
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            continue


def _consume_terminated_worker(worker: asyncio.Task[object]) -> None:
    if worker.cancelled():
        return
    try:
        error = worker.exception()
    except Exception:
        log.exception("读取已终止 AI 配置任务线程结果失败")
        return
    if error is not None and not isinstance(
        error,
        TaskCancellationRequested,
    ):
        try:
            raise RuntimeError("已终止 AI 配置任务线程收尾失败")
        except RuntimeError:
            log.exception(
                "已终止 AI 配置任务线程收尾失败",
                extra={"error_code": _safe_error_code(error)},
            )


def _require_system_scope(context: TaskExecutionContext) -> None:
    if context.account_id is not None:
        raise DomainError(
            ErrorCode.ACCOUNT_SCOPE_MISMATCH,
            "系统 AI 配置任务不能携带账号范围",
            status_code=403,
        )


def _require_id(
    payload: Mapping[str, JsonValue],
    field: str,
) -> str:
    value = payload.get(field)
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 256
    ):
        raise task_snapshot_invalid(
            f"AI 配置任务快照字段 {field} 无效",
            stored_snapshot=True,
        )
    return value


def _require_revision(
    payload: Mapping[str, JsonValue],
    field: str,
) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise task_snapshot_invalid(
            f"AI 配置任务快照字段 {field} 无效",
            stored_snapshot=True,
        )
    return value


def _require_bool(
    payload: Mapping[str, JsonValue],
    field: str,
) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        raise task_snapshot_invalid(
            f"AI 配置任务快照字段 {field} 无效",
            stored_snapshot=True,
        )
    return value


def _require_capability_keys(
    payload: Mapping[str, JsonValue],
) -> tuple[str, ...]:
    value = payload.get("capabilityKeys")
    if not isinstance(value, list) or len(value) > len(CAPABILITY_KEYS):
        raise task_snapshot_invalid(
            "AI 配置任务能力键快照无效",
            stored_snapshot=True,
        )
    keys = tuple(item for item in value if isinstance(item, str))
    if (
        len(keys) != len(value)
        or len(set(keys)) != len(keys)
        or any(key not in CAPABILITY_KEYS for key in keys)
    ):
        raise task_snapshot_invalid(
            "AI 配置任务能力键快照包含重复或未知值",
            stored_snapshot=True,
        )
    return keys


def _require_stages(
    payload: Mapping[str, JsonValue],
) -> tuple[str, ...]:
    value = payload.get("stages")
    allowed = {"network", "authentication"}
    if not isinstance(value, list) or not value or len(value) > len(allowed):
        raise task_snapshot_invalid(
            "Provider 检查阶段快照无效",
            stored_snapshot=True,
        )
    stages = tuple(item for item in value if isinstance(item, str))
    if len(stages) != len(value) or len(set(stages)) != len(stages):
        raise task_snapshot_invalid(
            "Provider 检查阶段快照包含重复或无效值",
            stored_snapshot=True,
        )
    if any(stage not in allowed for stage in stages):
        raise task_snapshot_invalid(
            "Provider 检查阶段快照包含未知值",
            stored_snapshot=True,
        )
    return stages


def _require_mode(payload: Mapping[str, JsonValue]) -> str:
    value = payload.get("mode")
    if value not in {"contract_only", "real_small_call"}:
        raise task_snapshot_invalid(
            "模型能力检查模式快照无效",
            stored_snapshot=True,
        )
    return str(value)


def _safe_error_code(error: BaseException) -> str:
    if isinstance(error, DomainError):
        return error.error_code
    return ErrorCode.INTERNAL_ERROR.value
