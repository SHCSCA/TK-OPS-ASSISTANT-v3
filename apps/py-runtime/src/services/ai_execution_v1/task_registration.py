from __future__ import annotations

from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.types import TaskHandlerDefinition, TaskResumePolicy

from .creation import AI_EXECUTION_TASK_TYPE
from .executor import AIExecutionExecutor
from .task_handlers import build_ai_execution_handler


def register_ai_execution_handler(
    registry: TaskHandlerRegistry,
    *,
    executor: AIExecutionExecutor,
    timeout_seconds: int | None = None,
) -> None:
    registry.register(
        TaskHandlerDefinition(
            task_type=AI_EXECUTION_TASK_TYPE,
            handler=build_ai_execution_handler(executor),
            allowed_snapshot_fields=frozenset(
                {"executionId", "snapshotHash"}
            ),
            resume_policy=TaskResumePolicy.INTERRUPT,
            cancellable=True,
            handler_version=1,
            timeout_seconds=timeout_seconds,
        )
    )


__all__ = ["register_ai_execution_handler"]
