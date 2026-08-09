from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeAlias, TypeVar

from services.tasks.errors import TaskCancellationRequested

_R = TypeVar("_R")

JsonValue: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)


class TaskScope(StrEnum):
    SYSTEM = "system"
    ACCOUNT = "account"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    FAILED = "failed"
    COMPLETED = "completed"


class TaskCompletionKind(StrEnum):
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"


class TaskFailureKind(StrEnum):
    ERROR = "error"
    TIMED_OUT = "timed_out"
    RESTART_INTERRUPTED = "restart_interrupted"


class TaskResumePolicy(StrEnum):
    RESUME = "resume"
    INTERRUPT = "interrupt"


class TaskCommitDecision(StrEnum):
    TERMINATION_WON = "termination_won"
    COMMIT_WON = "commit_won"


class TaskCommitCoordinator:
    """在线程提交与异步终止之间提供单一线性化裁决。"""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._enabled = False
        self._state = "open"
        self._termination_pending = False

    @property
    def enabled(self) -> bool:
        with self._condition:
            return self._enabled

    def enable(self) -> TaskCommitCoordinator:
        with self._condition:
            self._enabled = True
        return self

    def request_termination(self) -> TaskCommitDecision:
        with self._condition:
            self._termination_pending = True
            while self._state == "committing":
                self._condition.wait()
            if self._state == "committed":
                return TaskCommitDecision.COMMIT_WON
            self._state = "termination_won"
            return TaskCommitDecision.TERMINATION_WON

    def raise_if_termination_won(self) -> None:
        with self._condition:
            if self._state == "termination_won":
                raise TaskCancellationRequested()

    def commit(self, callback: Callable[[], _R]) -> _R:
        with self._condition:
            if self._state == "termination_won":
                raise TaskCancellationRequested()
            if self._state == "committed":
                raise RuntimeError("任务业务事务不能重复提交")
            self._state = "committing"
        try:
            result = callback()
        except BaseException:
            with self._condition:
                self._state = (
                    "termination_won"
                    if self._termination_pending
                    else "open"
                )
                self._condition.notify_all()
            raise
        with self._condition:
            self._state = "committed"
            self._condition.notify_all()
        return result


NON_TERMINAL_STATUSES = frozenset(
    {
        TaskStatus.QUEUED,
        TaskStatus.RUNNING,
        TaskStatus.CANCELLING,
    }
)
TERMINAL_STATUSES = frozenset({TaskStatus.FAILED, TaskStatus.COMPLETED})


@dataclass(frozen=True, slots=True)
class TaskRuntimePolicy:
    default_timeout_seconds: int
    max_timeout_seconds: int
    max_snapshot_bytes: int
    max_concurrency: int

    def __post_init__(self) -> None:
        if self.default_timeout_seconds <= 0:
            raise ValueError("默认任务超时必须大于零")
        if self.max_timeout_seconds < self.default_timeout_seconds:
            raise ValueError("最大任务超时不得小于默认超时")
        if self.max_snapshot_bytes <= 0:
            raise ValueError("任务快照上限必须大于零")
        if self.max_concurrency <= 0:
            raise ValueError("任务并发上限必须大于零")


@dataclass(frozen=True, slots=True)
class RuntimeTaskRecord:
    id: str
    scope: TaskScope
    account_id: str | None
    task_type: str
    status: TaskStatus
    completion_kind: TaskCompletionKind | None
    failure_kind: TaskFailureKind | None
    progress: float
    cancellable: bool
    timeout_at: str | None
    attempt: int
    retry_of_task_id: str | None
    config_snapshot_json: str
    result_ref: str | None
    error_code: str | None
    error_log_id: str | None
    revision: int
    created_at: str
    started_at: str | None
    completed_at: str | None
    updated_at: str
    idempotency_key_hash: str
    request_hash: str
    handler_version: int

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES


@dataclass(frozen=True, slots=True)
class CreateTaskCommand:
    scope: TaskScope
    account_id: str | None
    task_type: str
    payload: Mapping[str, JsonValue]
    idempotency_key: str
    request_id: str
    operation_id: str
    timeout_seconds: int | None = None
    retry_of_task_id: str | None = None
    attempt: int = 1


@dataclass(frozen=True, slots=True)
class TaskExecutionResult:
    result_ref: str | None = None


class TaskExecutionContext(Protocol):
    task_id: str
    account_id: str | None
    attempt: int

    async def report_progress(self, progress: float) -> None: ...

    def raise_if_cancelled(self) -> None: ...

    def enable_commit_coordination(self) -> TaskCommitCoordinator: ...


class TaskHandler(Protocol):
    async def __call__(
        self,
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult | None: ...


@dataclass(frozen=True, slots=True)
class TaskHandlerDefinition:
    task_type: str
    handler: TaskHandler
    allowed_snapshot_fields: frozenset[str]
    resume_policy: TaskResumePolicy
    cancellable: bool
    handler_version: int
    timeout_seconds: int | None = None
    single_active_per_scope: bool = False
    active_conflict_error_code: str = "TASK_ALREADY_RUNNING"

    def __post_init__(self) -> None:
        if not self.task_type.strip():
            raise ValueError("任务类型不能为空")
        if isinstance(self.handler_version, bool) or self.handler_version < 1:
            raise ValueError("任务处理器版本必须大于零")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("任务处理器超时必须大于零")
        if not self.active_conflict_error_code.strip():
            raise ValueError("任务活动态冲突错误码不能为空")


@dataclass(frozen=True, slots=True)
class FrozenTaskSnapshot:
    serialized: str
    key_hash: str
    request_hash: str
    handler_version: int
    payload: Mapping[str, JsonValue]
    creation_attempt: int
    retry_of_task_id: str | None
    requested_timeout_seconds: int | None


@dataclass(frozen=True, slots=True)
class TaskRecoveryPlan:
    resumable_task_ids: tuple[str, ...]
    interrupted_task_ids: tuple[str, ...]
    timed_out_task_ids: tuple[str, ...]
    cancelled_task_ids: tuple[str, ...]
