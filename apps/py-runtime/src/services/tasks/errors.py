from __future__ import annotations

from errors import DomainError, ErrorCode, FieldError


class TaskCancellationRequested(Exception):
    """任务执行器用于结束协作式取消。"""


def task_not_found() -> DomainError:
    return DomainError(
        ErrorCode.TASK_NOT_FOUND,
        "任务不存在",
        status_code=404,
    )


def task_scope_mismatch() -> DomainError:
    return DomainError(
        ErrorCode.ACCOUNT_SCOPE_MISMATCH,
        "任务不属于当前作用域",
        status_code=403,
    )


def task_not_cancellable() -> DomainError:
    return DomainError(
        ErrorCode.TASK_NOT_CANCELLABLE,
        "当前任务不能取消",
        status_code=409,
    )


def task_idempotency_conflict() -> DomainError:
    return DomainError(
        ErrorCode.TASK_IDEMPOTENCY_CONFLICT,
        "幂等键已用于不同的任务请求",
        status_code=409,
    )


def task_already_running(
    task_id: str,
    *,
    error_code: ErrorCode | str = ErrorCode.TASK_ALREADY_RUNNING,
) -> DomainError:
    return DomainError(
        error_code,
        "同一作用域已有相同类型任务正在执行",
        status_code=409,
        meta={"taskId": task_id},
    )


def task_handler_not_found(task_type: str) -> DomainError:
    return DomainError(
        ErrorCode.TASK_HANDLER_NOT_FOUND,
        "任务处理器未注册",
        status_code=503,
        loggable=True,
        log_context={"task_type": task_type},
    )


def task_snapshot_invalid(
    message: str,
    *,
    field: str = "payload",
    stored_snapshot: bool = False,
) -> DomainError:
    return DomainError(
        ErrorCode.TASK_SNAPSHOT_INVALID,
        message,
        status_code=500 if stored_snapshot else 422,
        field_errors=None
        if stored_snapshot
        else [
            FieldError(
                field=field,
                code="task_snapshot_invalid",
                message=message,
            )
        ],
        loggable=stored_snapshot,
    )


def task_state_conflict(message: str = "任务状态已变化，请刷新后重试") -> DomainError:
    return DomainError(
        ErrorCode.TASK_STATE_CONFLICT,
        message,
        status_code=409,
    )


def idempotency_key_required() -> DomainError:
    return DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "任务创建必须提供 Idempotency-Key",
        status_code=422,
        field_errors=[
            FieldError(
                field="Idempotency-Key",
                code="required",
                message="必须提供幂等键",
            )
        ],
    )
