from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import TypeVar

from errors import DomainError, ErrorCode
from services.accounts.health_execution import AccountHealthExecutor
from services.accounts.archive_cleanup import AccountArchiveCleanupService
from services.tasks.coordinator import TaskCoordinator
from services.tasks.errors import TaskCancellationRequested
from services.tasks.types import (
    JsonValue,
    TaskCommitCoordinator,
    TaskCommitDecision,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskHandler,
)

ACCOUNT_HEALTH_TASK_TYPE = "account.health_check"
ACCOUNT_RESTORE_HEALTH_TASK_TYPE = "account.restore_health_check"
ACCOUNT_CONNECTION_CHECK_TASK_TYPE = "account.connection_check"
ACCOUNT_ARCHIVE_CLEANUP_TASK_TYPE = "account.archive_cleanup"

_SUPPORTED_CHECKS = frozenset({"connection", "knowledge", "ai"})

log = logging.getLogger(__name__)
_T = TypeVar("_T")


def build_account_health_handler(
    executor: AccountHealthExecutor,
    *,
    restore: bool = False,
    connection_only: bool = False,
) -> TaskHandler:
    async def handle(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        account_id = _require_account_id(context)
        commit_coordinator = context.enable_commit_coordination()
        checks = _parse_checks(payload, connection_only=connection_only)
        expected_revision = _parse_expected_revision(
            payload,
            required=restore,
        )
        context.raise_if_cancelled()
        await context.report_progress(0.1)
        worker = asyncio.create_task(
            asyncio.to_thread(
                executor.run,
                account_id,
                checks=checks,
                restore=restore,
                expected_revision=expected_revision,
                require_connection=connection_only,
                commit_coordinator=commit_coordinator,
            )
        )
        try:
            revision = await asyncio.shield(worker)
            context.raise_if_cancelled()
            await context.report_progress(1.0)
        except (asyncio.CancelledError, TaskCancellationRequested):
            decision = await _request_termination(commit_coordinator)
            if decision is TaskCommitDecision.TERMINATION_WON:
                worker.add_done_callback(_consume_terminated_worker)
                log.info(
                    "账号健康任务终止先于业务提交生效",
                    extra={
                        "task_id": context.task_id,
                        "account_id": account_id,
                    },
                )
                raise
            revision = await _await_commit_winner(worker)
            log.info(
                "账号健康任务业务提交先于终止请求生效",
                extra={
                    "task_id": context.task_id,
                    "account_id": account_id,
                },
            )
        return TaskExecutionResult(
            result_ref=(
                f"account://{account_id}/health?revision={revision}"
            )
        )

    return handle


def build_account_archive_cleanup_handler(
    cleanup_service: AccountArchiveCleanupService,
    *,
    coordinator: TaskCoordinator,
) -> TaskHandler:
    async def handle(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        account_id = _require_account_id(context)
        expected_revision = _parse_expected_revision(payload, required=True)
        reason_provided = payload.get("reasonProvided")
        if expected_revision is None or not isinstance(reason_provided, bool):
            raise DomainError(
                ErrorCode.TASK_SNAPSHOT_INVALID,
                "账号归档任务快照无效",
                status_code=409,
            )
        await context.report_progress(0.1)
        await coordinator.cancel_other_account_tasks(
            account_id,
            excluded_task_id=context.task_id,
        )
        await context.report_progress(0.25)
        revision = await asyncio.to_thread(
            cleanup_service.cleanup,
            account_id=account_id,
            expected_revision=expected_revision,
            reason_provided=reason_provided,
            task_id=context.task_id,
        )
        await context.report_progress(1.0)
        return TaskExecutionResult(
            result_ref=f"account://{account_id}/archive?revision={revision}"
        )

    return handle


async def _request_termination(
    coordinator: TaskCommitCoordinator,
) -> TaskCommitDecision:
    decision = asyncio.create_task(
        asyncio.to_thread(coordinator.request_termination)
    )
    return await _await_commit_winner(decision)


async def _await_commit_winner(
    worker: asyncio.Task[_T],
) -> _T:
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
        log.exception("读取已终止账号健康任务线程结果失败")
        return
    if error is not None and not isinstance(
        error,
        TaskCancellationRequested,
    ):
        log.error(
            "已终止账号健康任务线程收尾失败",
            exc_info=(type(error), error, error.__traceback__),
        )


def _require_account_id(context: TaskExecutionContext) -> str:
    account_id = context.account_id
    if account_id is None:
        raise DomainError(
            ErrorCode.ACCOUNT_SCOPE_MISMATCH,
            "账号任务缺少账号范围",
            status_code=403,
        )
    return account_id


def _parse_checks(
    payload: Mapping[str, JsonValue],
    *,
    connection_only: bool,
) -> tuple[str, ...]:
    raw_checks = payload.get("checks")
    if not isinstance(raw_checks, list):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "账号健康检查项格式无效",
            status_code=422,
        )
    checks = tuple(
        value
        for value in raw_checks
        if isinstance(value, str) and value in _SUPPORTED_CHECKS
    )
    if (
        not checks
        or len(checks) != len(raw_checks)
        or len(set(checks)) != len(checks)
    ):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "账号健康检查项包含重复或不受支持的值",
            status_code=422,
        )
    if connection_only and checks != ("connection",):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "连接诊断任务只能检查真实连接",
            status_code=422,
        )
    return checks


def _parse_expected_revision(
    payload: Mapping[str, JsonValue],
    *,
    required: bool,
) -> int | None:
    value = payload.get("expectedRevision")
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "恢复账号的预期修订号无效",
            status_code=422,
        )
    return value
