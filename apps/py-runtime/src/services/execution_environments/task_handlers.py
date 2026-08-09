from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping

from errors import DomainError, ErrorCode
from services.execution_environments.actions import (
    ExecutionEnvironmentActionService,
)
from services.execution_environments.provisioning import (
    ExecutionEnvironmentProvisioner,
)
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.types import (
    JsonValue,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskHandler,
    TaskHandlerDefinition,
    TaskResumePolicy,
)

PROVISION_TASK_TYPE = "execution_environment.provision"
START_TASK_TYPE = "execution_environment.start"
STOP_TASK_TYPE = "execution_environment.stop"
CHECK_TASK_TYPE = "execution_environment.check"
DELETE_TASK_TYPE = "execution_environment.delete"


def register_execution_environment_task_handlers(
    registry: TaskHandlerRegistry,
    *,
    provisioner: ExecutionEnvironmentProvisioner,
    action_service: ExecutionEnvironmentActionService,
    timeout_seconds: int = 120,
) -> None:
    async def provision(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        account_id = context.account_id
        environment_id = payload.get("environmentId")
        root_ref = payload.get("rootRef")
        activate = payload.get("activateWhenReady")
        if (
            account_id is None
            or not isinstance(environment_id, str)
            or not isinstance(root_ref, str)
            or not isinstance(activate, bool)
        ):
            raise DomainError(
                ErrorCode.TASK_SNAPSHOT_INVALID,
                "执行环境任务快照无效",
                status_code=409,
            )
        context.raise_if_cancelled()
        await context.report_progress(0.1)
        revision = await asyncio.to_thread(
            provisioner.provision,
            account_id=account_id,
            environment_id=environment_id,
            root_ref=root_ref,
            activate_when_ready=activate,
            task_id=context.task_id,
        )
        context.raise_if_cancelled()
        await context.report_progress(1.0)
        return TaskExecutionResult(
            result_ref=f"execution-environment://{environment_id}?revision={revision}"
        )

    registry.register(
        TaskHandlerDefinition(
            task_type=PROVISION_TASK_TYPE,
            handler=provision,
            allowed_snapshot_fields=frozenset(
                {"environmentId", "rootRef", "activateWhenReady"}
            ),
            resume_policy=TaskResumePolicy.INTERRUPT,
            cancellable=True,
            handler_version=1,
            timeout_seconds=timeout_seconds,
            single_active_per_scope=True,
            active_conflict_error_code="EXECUTION_ENVIRONMENT_TASK_CONFLICT",
        )
    )

    for task_type, action, resume_policy, cancellable in (
        (START_TASK_TYPE, action_service.start, TaskResumePolicy.INTERRUPT, True),
        (STOP_TASK_TYPE, action_service.stop, TaskResumePolicy.RESUME, False),
        (CHECK_TASK_TYPE, action_service.check, TaskResumePolicy.RESUME, True),
        (DELETE_TASK_TYPE, action_service.delete, TaskResumePolicy.RESUME, False),
    ):
        registry.register(
            TaskHandlerDefinition(
                task_type=task_type,
                handler=_build_action_handler(action),
                allowed_snapshot_fields=frozenset(
                    {"environmentId", "expectedRevision"}
                ),
                resume_policy=resume_policy,
                cancellable=cancellable,
                handler_version=1,
                timeout_seconds=timeout_seconds,
                single_active_per_scope=True,
                active_conflict_error_code="EXECUTION_ENVIRONMENT_TASK_CONFLICT",
            )
        )


def _build_action_handler(action: Callable[..., int]) -> TaskHandler:
    async def handle(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        account_id = context.account_id
        environment_id = payload.get("environmentId")
        expected_revision = payload.get("expectedRevision")
        if (
            account_id is None
            or not isinstance(environment_id, str)
            or isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise DomainError(
                ErrorCode.TASK_SNAPSHOT_INVALID,
                "执行环境动作任务快照无效",
                status_code=409,
            )
        context.raise_if_cancelled()
        await context.report_progress(0.1)
        revision = await asyncio.to_thread(
            action,
            account_id=account_id,
            environment_id=environment_id,
            expected_revision=expected_revision,
            task_id=context.task_id,
        )
        context.raise_if_cancelled()
        await context.report_progress(1.0)
        return TaskExecutionResult(
            result_ref=(
                f"execution-environment://{environment_id}?revision={revision}"
            )
        )

    return handle
