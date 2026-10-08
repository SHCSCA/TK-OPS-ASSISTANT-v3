from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class AIExecutionJob(Base):
    """保存一次 Provider 外部调用尝试。"""

    __tablename__ = "ai_execution_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "execution_id"],
            ["ai_executions.account_id", "ai_executions.id"],
            ondelete="RESTRICT",
            name="fk_ai_execution_jobs_execution_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "candidate_snapshot_id"],
            ["ai_execution_candidates.account_id", "ai_execution_candidates.id"],
            ondelete="RESTRICT",
            name="fk_ai_execution_jobs_candidate_account",
        ),
        CheckConstraint(
            "status IN ('queued','running','cancelling','failed','completed')",
            name="ck_ai_execution_jobs_status",
        ),
        CheckConstraint(
            "completion_kind IS NULL OR completion_kind IN ('succeeded','cancelled')",
            name="ck_ai_execution_jobs_completion",
        ),
        CheckConstraint(
            "failure_kind IS NULL OR failure_kind IN "
            "('error','timed_out','restart_interrupted','result_unknown')",
            name="ck_ai_execution_jobs_failure",
        ),
        CheckConstraint(
            "attempt >= 1 AND fallback_index >= 0 AND retry_index >= 0 AND revision >= 1",
            name="ck_ai_execution_jobs_attempt",
        ),
        UniqueConstraint("account_id", "id", name="uq_ai_execution_jobs_account_id"),
        UniqueConstraint(
            "execution_id",
            "attempt",
            name="uq_ai_execution_jobs_execution_attempt",
        ),
        Index("ix_ai_execution_jobs_account_execution", "account_id", "execution_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    candidate_snapshot_id: Mapped[str] = mapped_column(String, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    fallback_index: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    completion_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    provider_request_id_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    request_hash: Mapped[str] = mapped_column(String, nullable=False)
    response_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeout_at: Mapped[str] = mapped_column(Text, nullable=False)
    error_evidence_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class AIExecution(Base):
    """保存账号级 AI 执行聚合和最终状态。"""

    __tablename__ = "ai_executions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "runtime_task_id"],
            ["runtime_tasks.account_id", "runtime_tasks.id"],
            ondelete="RESTRICT",
            name="fk_ai_executions_runtime_task_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "snapshot_id"],
            ["ai_execution_snapshots.account_id", "ai_execution_snapshots.id"],
            ondelete="RESTRICT",
            name="fk_ai_executions_snapshot_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "active_job_id"],
            ["ai_execution_jobs.account_id", "ai_execution_jobs.id"],
            ondelete="RESTRICT",
            name="fk_ai_executions_active_job_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "retry_of_execution_id"],
            ["ai_executions.account_id", "ai_executions.id"],
            ondelete="RESTRICT",
            name="fk_ai_executions_retry_account",
        ),
        CheckConstraint(
            "status IN ('queued','running','cancelling','failed','completed')",
            name="ck_ai_executions_status",
        ),
        CheckConstraint(
            "completion_kind IS NULL OR completion_kind IN ('succeeded','cancelled')",
            name="ck_ai_executions_completion",
        ),
        CheckConstraint(
            "failure_kind IS NULL OR failure_kind IN "
            "('error','timed_out','restart_interrupted','result_unknown')",
            name="ck_ai_executions_failure",
        ),
        CheckConstraint(
            "cost_status IN ('reported','estimated','unavailable')",
            name="ck_ai_executions_cost_status",
        ),
        CheckConstraint(
            "budget_limit_micros >= 0 AND output_count >= 0 AND revision >= 1",
            name="ck_ai_executions_limits",
        ),
        UniqueConstraint("account_id", "id", name="uq_ai_executions_account_id"),
        UniqueConstraint("snapshot_id", name="uq_ai_executions_snapshot"),
        UniqueConstraint(
            "account_id",
            "idempotency_key_hash",
            name="uq_ai_executions_account_idempotency",
        ),
        Index("ix_ai_executions_account_updated", "account_id", "updated_at"),
        Index("ix_ai_executions_account_status", "account_id", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    capability_key: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    completion_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot_id: Mapped[str] = mapped_column(String, nullable=False)
    runtime_task_id: Mapped[str] = mapped_column(String, nullable=False)
    active_job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_of_execution_id: Mapped[str | None] = mapped_column(String, nullable=True)
    input_ref: Mapped[str] = mapped_column(Text, nullable=False)
    input_hash: Mapped[str] = mapped_column(String, nullable=False)
    idempotency_key_hash: Mapped[str] = mapped_column(String, nullable=False)
    request_hash: Mapped[str] = mapped_column(String, nullable=False)
    budget_limit_micros: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    usage_input_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_output_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_cached_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_micros: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_status: Mapped[str] = mapped_column(String, nullable=False)
    output_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


__all__ = ["AIExecution", "AIExecutionJob"]
