from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from domain.models import Base
from domain.models.runtime_event import RuntimeEvent
from domain.models.runtime_task import RuntimeTask
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.runtime_event_repository import RuntimeEventRepository
from repositories.runtime_task_repository import RuntimeTaskRepository
from services.events import RuntimeEventService
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.snapshot import TaskSnapshotPolicy
from services.tasks.task_service import TaskService
from services.tasks.types import (
    TaskHandler,
    TaskHandlerDefinition,
    TaskResumePolicy,
    TaskRuntimePolicy,
)


@dataclass(frozen=True, slots=True)
class RuntimeTaskTestStack:
    engine: Engine
    session_factory: sessionmaker[Session]
    task_repository: RuntimeTaskRepository
    event_repository: RuntimeEventRepository
    event_service: RuntimeEventService
    handler_registry: TaskHandlerRegistry
    snapshot_policy: TaskSnapshotPolicy
    runtime_policy: TaskRuntimePolicy
    task_service: TaskService


def make_runtime_task_stack(
    database_path: Path,
    *,
    handler: TaskHandler,
    task_type: str = "test.operation",
    allowed_fields: frozenset[str] = frozenset({"resourceRef"}),
    resume_policy: TaskResumePolicy = TaskResumePolicy.INTERRUPT,
    cancellable: bool = True,
    single_active_per_scope: bool = False,
    active_conflict_error_code: str = "TASK_ALREADY_RUNNING",
    clock: Callable[[], datetime] | None = None,
) -> RuntimeTaskTestStack:
    for model in (RuntimeEvent, RuntimeTask):
        if model.metadata is not Base.metadata:
            raise AssertionError("Runtime 任务模型必须注册到统一元数据")

    engine = create_runtime_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    task_repository = RuntimeTaskRepository(session_factory=session_factory)
    event_repository = RuntimeEventRepository(session_factory=session_factory)
    event_service = RuntimeEventService(event_repository, replay_limit=100)
    handler_registry = TaskHandlerRegistry()
    handler_registry.register(
        TaskHandlerDefinition(
            task_type=task_type,
            handler=handler,
            allowed_snapshot_fields=allowed_fields,
            resume_policy=resume_policy,
            cancellable=cancellable,
            handler_version=1,
            single_active_per_scope=single_active_per_scope,
            active_conflict_error_code=active_conflict_error_code,
        )
    )
    runtime_policy = TaskRuntimePolicy(
        default_timeout_seconds=60,
        max_timeout_seconds=600,
        max_snapshot_bytes=8192,
        max_concurrency=2,
    )
    snapshot_policy = TaskSnapshotPolicy(
        max_bytes=runtime_policy.max_snapshot_bytes
    )
    task_service = TaskService(
        repository=task_repository,
        handler_registry=handler_registry,
        snapshot_policy=snapshot_policy,
        event_sink=event_service,
        runtime_policy=runtime_policy,
        clock=clock,
    )
    return RuntimeTaskTestStack(
        engine=engine,
        session_factory=session_factory,
        task_repository=task_repository,
        event_repository=event_repository,
        event_service=event_service,
        handler_registry=handler_registry,
        snapshot_policy=snapshot_policy,
        runtime_policy=runtime_policy,
        task_service=task_service,
    )
