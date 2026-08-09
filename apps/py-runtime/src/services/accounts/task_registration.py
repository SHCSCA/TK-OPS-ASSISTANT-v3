from __future__ import annotations

from services.accounts.health_execution import AccountHealthExecutor
from services.accounts.archive_cleanup import AccountArchiveCleanupService
from services.accounts.task_handlers import (
    ACCOUNT_CONNECTION_CHECK_TASK_TYPE,
    ACCOUNT_ARCHIVE_CLEANUP_TASK_TYPE,
    ACCOUNT_HEALTH_TASK_TYPE,
    ACCOUNT_RESTORE_HEALTH_TASK_TYPE,
    build_account_health_handler,
    build_account_archive_cleanup_handler,
)
from services.tasks.coordinator import TaskCoordinator
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.types import (
    TaskHandler,
    TaskHandlerDefinition,
    TaskResumePolicy,
)


def register_account_task_handlers(
    registry: TaskHandlerRegistry,
    *,
    executor: AccountHealthExecutor,
    archive_cleanup_service: AccountArchiveCleanupService,
    coordinator: TaskCoordinator,
    timeout_seconds: int | None = None,
) -> None:
    registry.register(
        TaskHandlerDefinition(
            task_type=ACCOUNT_ARCHIVE_CLEANUP_TASK_TYPE,
            handler=build_account_archive_cleanup_handler(
                archive_cleanup_service,
                coordinator=coordinator,
            ),
            allowed_snapshot_fields=frozenset(
                {"expectedRevision", "reasonProvided"}
            ),
            resume_policy=TaskResumePolicy.RESUME,
            cancellable=False,
            handler_version=1,
            timeout_seconds=timeout_seconds or 120,
            single_active_per_scope=True,
        )
    )
    _register(
        registry,
        task_type=ACCOUNT_HEALTH_TASK_TYPE,
        handler=build_account_health_handler(executor),
        allowed_fields=frozenset({"checks"}),
        timeout_seconds=timeout_seconds,
    )
    _register(
        registry,
        task_type=ACCOUNT_RESTORE_HEALTH_TASK_TYPE,
        handler=build_account_health_handler(executor, restore=True),
        allowed_fields=frozenset({"checks", "expectedRevision"}),
        timeout_seconds=timeout_seconds,
    )
    _register(
        registry,
        task_type=ACCOUNT_CONNECTION_CHECK_TASK_TYPE,
        handler=build_account_health_handler(
            executor,
            connection_only=True,
        ),
        allowed_fields=frozenset({"checks"}),
        timeout_seconds=timeout_seconds,
    )


def _register(
    registry: TaskHandlerRegistry,
    *,
    task_type: str,
    handler: TaskHandler,
    allowed_fields: frozenset[str],
    timeout_seconds: int | None,
) -> None:
    registry.register(
        TaskHandlerDefinition(
            task_type=task_type,
            handler=handler,
            allowed_snapshot_fields=allowed_fields,
            resume_policy=TaskResumePolicy.INTERRUPT,
            cancellable=True,
            handler_version=1,
            timeout_seconds=timeout_seconds,
            single_active_per_scope=True,
        )
    )
