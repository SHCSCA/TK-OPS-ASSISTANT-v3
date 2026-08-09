from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session, sessionmaker

from api.websocket import RuntimeWebSocketManager
from app.websocket_security import build_account_subscription_authorizer
from repositories.account_repository import AccountRepository
from repositories.runtime_event_repository import RuntimeEventRepository
from repositories.runtime_task_repository import RuntimeTaskRepository
from services.bootstrap_v1.self_check import (
    build_bootstrap_self_check_handler,
)
from services.config import ConfigBusService
from services.diagnostics import RuntimeDiagnosticsService
from services.events import RuntimeEventPublisher, RuntimeEventService
from services.tasks.bootstrap_registration import (
    register_bootstrap_self_check_handler,
)
from services.tasks.coordinator import TaskCoordinator
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.recovery import TaskRecoveryService
from services.tasks.snapshot import TaskSnapshotPolicy
from services.tasks.task_runner import TaskRunner
from services.tasks.task_service import TaskService
from services.tasks.types import TaskRecoveryPlan, TaskRuntimePolicy

log = logging.getLogger(__name__)
StartupReconciler = Callable[[], object]


@dataclass(frozen=True, slots=True)
class RuntimeKernelPolicy:
    event_publish_interval_seconds: float
    shutdown_grace_seconds: float
    websocket_subscribe_timeout_seconds: float
    websocket_send_timeout_seconds: float
    websocket_close_timeout_seconds: float
    websocket_max_message_bytes: int
    legacy_websocket_max_message_bytes: int


@dataclass(frozen=True, slots=True)
class RuntimeKernel:
    event_service: RuntimeEventService
    event_publisher: RuntimeEventPublisher
    websocket_manager: RuntimeWebSocketManager
    task_coordinator: TaskCoordinator
    task_runner: TaskRunner
    task_handler_registry: TaskHandlerRegistry
    policy: RuntimeKernelPolicy
    _startup_reconcilers: list[StartupReconciler] = field(
        default_factory=list,
        repr=False,
    )

    def register_startup_reconciler(
        self,
        reconciler: StartupReconciler,
    ) -> None:
        if not callable(reconciler):
            raise ValueError("Runtime 启动对账器必须可调用")
        self._startup_reconcilers.append(reconciler)


class _RuntimeRecoveryService(TaskRecoveryService):
    def __init__(
        self,
        *,
        task_service: TaskService,
        handler_registry: TaskHandlerRegistry,
        snapshot_policy: TaskSnapshotPolicy,
        scheduler: TaskRunner,
        startup_reconcilers: list[StartupReconciler],
    ) -> None:
        super().__init__(
            task_service=task_service,
            handler_registry=handler_registry,
            snapshot_policy=snapshot_policy,
            scheduler=scheduler,
        )
        self._startup_reconcilers = startup_reconcilers

    async def recover(self) -> TaskRecoveryPlan:
        plan = await self.prepare_recovery()
        for reconciler in tuple(self._startup_reconcilers):
            try:
                await asyncio.to_thread(reconciler)
            except Exception:
                log.exception(
                    "Runtime 持久任务恢复后的启动对账失败",
                    extra={
                        "reconciler": getattr(
                            reconciler,
                            "__qualname__",
                            type(reconciler).__name__,
                        )
                    },
                )
                raise
        self.schedule_recovery(plan)
        return plan


def build_runtime_kernel(
    *,
    session_factory: sessionmaker[Session],
    account_repository: AccountRepository,
    task_repository: RuntimeTaskRepository,
    event_repository: RuntimeEventRepository,
    config_bus_service: ConfigBusService,
    diagnostics_service: RuntimeDiagnosticsService,
) -> RuntimeKernel:
    values = config_bus_service.get().values
    task_policy = TaskRuntimePolicy(
        default_timeout_seconds=_required_int(
            values,
            "runtime.taskTimeoutSeconds",
        ),
        max_timeout_seconds=_required_int(
            values,
            "runtime.taskMaxTimeoutSeconds",
        ),
        max_snapshot_bytes=_required_int(
            values,
            "runtime.taskSnapshotMaxBytes",
        ),
        max_concurrency=_required_int(
            values,
            "runtime.taskMaxConcurrency",
        ),
    )
    event_service = RuntimeEventService(
        event_repository,
        replay_limit=_required_int(values, "websocket.replayLimit"),
    )
    websocket_send_timeout_seconds = float(
        _required_int(values, "websocket.sendTimeoutSeconds")
    )
    websocket_close_timeout_seconds = float(
        _required_int(values, "websocket.closeTimeoutSeconds")
    )
    event_publish_interval_seconds = (
        _required_int(values, "websocket.publishIntervalMs") / 1_000
    )
    shutdown_grace_seconds = max(
        1.0,
        event_publish_interval_seconds
        + websocket_send_timeout_seconds
        + websocket_close_timeout_seconds,
    )
    websocket_manager = RuntimeWebSocketManager(
        event_service,
        authorize_account=build_account_subscription_authorizer(
            account_repository
        ),
        send_timeout_seconds=websocket_send_timeout_seconds,
        close_timeout_seconds=websocket_close_timeout_seconds,
    )
    event_publisher = RuntimeEventPublisher(
        event_repository,
        event_service,
        websocket_manager.publish,
        batch_size=_required_int(values, "websocket.publishBatchSize"),
        blocking_cancel_grace_seconds=min(1.0, shutdown_grace_seconds),
    )

    handler_registry = TaskHandlerRegistry()
    register_bootstrap_self_check_handler(
        handler_registry,
        handler=build_bootstrap_self_check_handler(
            diagnostics_service=diagnostics_service,
            session_factory=session_factory,
        ),
        timeout_seconds=task_policy.default_timeout_seconds,
    )
    snapshot_policy = TaskSnapshotPolicy(
        max_bytes=task_policy.max_snapshot_bytes
    )
    task_service = TaskService(
        repository=task_repository,
        handler_registry=handler_registry,
        snapshot_policy=snapshot_policy,
        event_sink=event_service,
        runtime_policy=task_policy,
    )
    task_runner = TaskRunner(
        task_service=task_service,
        handler_registry=handler_registry,
        snapshot_policy=snapshot_policy,
        runtime_policy=task_policy,
        shutdown_grace_seconds=shutdown_grace_seconds,
    )
    startup_reconcilers: list[StartupReconciler] = []
    recovery_service = _RuntimeRecoveryService(
        task_service=task_service,
        handler_registry=handler_registry,
        snapshot_policy=snapshot_policy,
        scheduler=task_runner,
        startup_reconcilers=startup_reconcilers,
    )
    task_coordinator = TaskCoordinator(
        task_service=task_service,
        task_runner=task_runner,
        recovery_service=recovery_service,
    )
    policy = RuntimeKernelPolicy(
        event_publish_interval_seconds=event_publish_interval_seconds,
        shutdown_grace_seconds=shutdown_grace_seconds,
        websocket_subscribe_timeout_seconds=float(
            _required_int(values, "websocket.subscribeTimeoutSeconds")
        ),
        websocket_send_timeout_seconds=websocket_send_timeout_seconds,
        websocket_close_timeout_seconds=websocket_close_timeout_seconds,
        websocket_max_message_bytes=_required_int(
            values,
            "websocket.maxMessageBytes",
        ),
        legacy_websocket_max_message_bytes=_required_int(
            values,
            "websocket.legacyMaxMessageBytes",
        ),
    )
    return RuntimeKernel(
        event_service=event_service,
        event_publisher=event_publisher,
        websocket_manager=websocket_manager,
        task_coordinator=task_coordinator,
        task_runner=task_runner,
        task_handler_registry=handler_registry,
        policy=policy,
        _startup_reconcilers=startup_reconcilers,
    )


def _required_int(values: dict[str, object], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"配置总线缺少有效整数配置：{key}")
    return value
