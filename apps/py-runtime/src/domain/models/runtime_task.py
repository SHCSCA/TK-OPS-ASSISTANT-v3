from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class RuntimeTask(Base):
    """持久化 Runtime 长任务及其可恢复状态。"""

    __tablename__ = "runtime_tasks"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('system','account')",
            name="ck_runtime_tasks_scope",
        ),
        CheckConstraint(
            "(scope = 'system' AND account_id IS NULL) OR "
            "(scope = 'account' AND account_id IS NOT NULL "
            "AND length(trim(account_id)) > 0)",
            name="ck_runtime_tasks_account_scope",
        ),
        CheckConstraint(
            "length(trim(task_type)) > 0 AND task_type = trim(task_type)",
            name="ck_runtime_tasks_task_type",
        ),
        CheckConstraint(
            "status IN ('queued','running','cancelling','failed','completed')",
            name="ck_runtime_tasks_status",
        ),
        CheckConstraint(
            "completion_kind IS NULL OR completion_kind IN ('succeeded','cancelled')",
            name="ck_runtime_tasks_completion_kind",
        ),
        CheckConstraint(
            "failure_kind IS NULL OR failure_kind IN "
            "('error','timed_out','restart_interrupted')",
            name="ck_runtime_tasks_failure_kind",
        ),
        CheckConstraint(
            "(status = 'completed' AND completion_kind IS NOT NULL "
            "AND failure_kind IS NULL AND completed_at IS NOT NULL) "
            "OR (status = 'failed' AND failure_kind IS NOT NULL "
            "AND completion_kind IS NULL AND completed_at IS NOT NULL) "
            "OR (status IN ('queued','running','cancelling') "
            "AND completion_kind IS NULL AND failure_kind IS NULL "
            "AND completed_at IS NULL)",
            name="ck_runtime_tasks_terminal_kind",
        ),
        CheckConstraint(
            "progress BETWEEN 0 AND 1",
            name="ck_runtime_tasks_progress",
        ),
        CheckConstraint(
            "attempt >= 1 AND revision >= 1",
            name="ck_runtime_tasks_attempt_revision",
        ),
        CheckConstraint(
            "length(idempotency_key_hash) = 64 "
            "AND idempotency_key_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_runtime_tasks_idempotency_hash",
        ),
        CheckConstraint(
            "length(request_hash) = 64 "
            "AND request_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_runtime_tasks_request_hash",
        ),
        CheckConstraint(
            "handler_version >= 1",
            name="ck_runtime_tasks_handler_version",
        ),
        Index("ix_runtime_tasks_account_updated", "account_id", "updated_at"),
        Index("ix_runtime_tasks_status_updated", "status", "updated_at"),
        Index(
            "uq_runtime_tasks_account_id",
            "account_id",
            "id",
            unique=True,
        ),
        Index(
            "uq_runtime_tasks_system_idempotency",
            "task_type",
            "idempotency_key_hash",
            unique=True,
            sqlite_where=text("scope = 'system' AND account_id IS NULL"),
        ),
        Index(
            "uq_runtime_tasks_account_idempotency",
            "account_id",
            "task_type",
            "idempotency_key_hash",
            unique=True,
            sqlite_where=text("scope = 'account' AND account_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    account_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    completion_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    progress: Mapped[float] = mapped_column(Float, nullable=False)
    cancellable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timeout_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_of_task_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("runtime_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    config_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key_hash: Mapped[str] = mapped_column(String, nullable=False)
    request_hash: Mapped[str] = mapped_column(String, nullable=False)
    handler_version: Mapped[int] = mapped_column(Integer, nullable=False)
