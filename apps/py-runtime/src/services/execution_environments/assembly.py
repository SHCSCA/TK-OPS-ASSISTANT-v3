from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentV1Repository,
)
from services.browser_runtime import BrowserRuntime
from services.events import RuntimeEventService
from services.execution_environments.actions import (
    ExecutionEnvironmentActionService,
)
from services.execution_environments.browser_process import (
    BrowserProcessOwnershipService,
)
from services.execution_environments.provisioning import (
    ExecutionEnvironmentProvisioner,
)
from services.execution_environments.service import ExecutionEnvironmentService
from services.execution_environments.task_handlers import (
    register_execution_environment_task_handlers,
)
from services.execution_environments.workspace_root_resolver import (
    WorkspaceRootResolver,
)
from services.tasks.coordinator import TaskCoordinator
from services.tasks.handler_registry import TaskHandlerRegistry


def build_execution_environment_service(
    *,
    session_factory: sessionmaker[Session],
    registry_path: Path,
    browser_runtime: BrowserRuntime,
    task_coordinator: TaskCoordinator,
    task_handler_registry: TaskHandlerRegistry,
    event_service: RuntimeEventService,
    provision_timeout_seconds: int,
    recovery_timeout_seconds: int,
) -> ExecutionEnvironmentService:
    repository = ExecutionEnvironmentV1Repository(session_factory)
    root_resolver = WorkspaceRootResolver(registry_path)
    runtime_generation = (
        os.getenv("TK_OPS_RUNTIME_ARTIFACT_BUILD_ID", "").strip()
        or f"runtime-{uuid4().hex}"
    )
    ownership_service = BrowserProcessOwnershipService(
        runtime_generation=runtime_generation
    )
    provisioner = ExecutionEnvironmentProvisioner(
        repository=repository,
        root_resolver=root_resolver,
        browser_runtime=browser_runtime,
        ownership_service=ownership_service,
        event_service=event_service,
    )
    action_service = ExecutionEnvironmentActionService(
        repository=repository,
        browser_runtime=browser_runtime,
        ownership_service=ownership_service,
        provisioner=provisioner,
        event_service=event_service,
    )
    register_execution_environment_task_handlers(
        task_handler_registry,
        provisioner=provisioner,
        action_service=action_service,
        timeout_seconds=provision_timeout_seconds,
    )
    return ExecutionEnvironmentService(
        repository=repository,
        root_resolver=root_resolver,
        task_coordinator=task_coordinator,
        task_timeout_seconds=max(
            provision_timeout_seconds,
            recovery_timeout_seconds,
        ),
    )
