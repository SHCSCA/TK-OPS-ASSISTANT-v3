from __future__ import annotations

from errors import ErrorCode
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.types import (
    TaskHandler,
    TaskHandlerDefinition,
    TaskResumePolicy,
)

BOOTSTRAP_SELF_CHECK_TASK_TYPE = "bootstrap.self_check"


def register_bootstrap_self_check_handler(
    registry: TaskHandlerRegistry,
    *,
    handler: TaskHandler,
    timeout_seconds: int | None = None,
) -> None:
    """注册真实 Bootstrap 自检处理器，不在任务层伪造检查结果。"""

    registry.register(
        TaskHandlerDefinition(
            task_type=BOOTSTRAP_SELF_CHECK_TASK_TYPE,
            handler=handler,
            allowed_snapshot_fields=frozenset({"checks"}),
            resume_policy=TaskResumePolicy.INTERRUPT,
            cancellable=True,
            handler_version=1,
            timeout_seconds=timeout_seconds,
            single_active_per_scope=True,
            active_conflict_error_code=ErrorCode.SELF_CHECK_ALREADY_RUNNING.value,
        )
    )
