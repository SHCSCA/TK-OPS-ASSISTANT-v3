from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from services.tasks.types import RuntimeTaskRecord

TaskScopeValue = Literal["system", "account"]
TaskStatusValue = Literal[
    "queued",
    "running",
    "cancelling",
    "failed",
    "completed",
]
TaskCompletionKindValue = Literal["succeeded", "cancelled"]
TaskFailureKindValue = Literal["error", "timed_out", "restart_interrupted"]


class V1TaskModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskAcceptedDto(V1TaskModel):
    taskId: str
    scope: TaskScopeValue
    accountId: str | None
    taskType: str
    status: Literal["queued"]
    cancellable: bool
    createdAt: str

    @classmethod
    def from_record(cls, record: RuntimeTaskRecord) -> TaskAcceptedDto:
        return cls(
            taskId=record.id,
            scope=record.scope.value,
            accountId=record.account_id,
            taskType=record.task_type,
            status="queued",
            cancellable=record.cancellable,
            createdAt=record.created_at,
        )


class TaskDto(V1TaskModel):
    taskId: str
    scope: TaskScopeValue
    accountId: str | None
    taskType: str
    status: TaskStatusValue
    cancellable: bool
    createdAt: str
    completionKind: TaskCompletionKindValue | None
    failureKind: TaskFailureKindValue | None
    progress: float
    resultRef: str | None
    errorCode: str | None
    logId: str | None
    revision: int

    @classmethod
    def from_record(cls, record: RuntimeTaskRecord) -> TaskDto:
        return cls(
            taskId=record.id,
            scope=record.scope.value,
            accountId=record.account_id,
            taskType=record.task_type,
            status=record.status.value,
            cancellable=record.cancellable,
            createdAt=record.created_at,
            completionKind=(
                record.completion_kind.value
                if record.completion_kind is not None
                else None
            ),
            failureKind=(
                record.failure_kind.value
                if record.failure_kind is not None
                else None
            ),
            progress=record.progress,
            resultRef=record.result_ref,
            errorCode=record.error_code,
            logId=record.error_log_id,
            revision=record.revision,
        )


class TaskListDto(V1TaskModel):
    items: list[TaskDto]
