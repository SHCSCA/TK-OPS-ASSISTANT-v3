from __future__ import annotations

from sqlalchemy import (
    Boolean,
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


class AIProviderValidationRun(Base):
    """保存 Provider 四阶段真实验证的脱敏证据。"""

    __tablename__ = "ai_provider_validation_runs"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('network','authentication','model_discovery','real_small_call')",
            name="ck_ai_provider_validation_stage",
        ),
        CheckConstraint(
            "status IN ('queued','running','verified','partial','failed','cancelled')",
            name="ck_ai_provider_validation_status",
        ),
        Index(
            "ix_ai_provider_validation_revision",
            "provider_profile_id",
            "provider_revision",
            "model_profile_id",
            "model_revision",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("provider_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    model_profile_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("model_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    model_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capability_key: Mapped[str | None] = mapped_column(String, nullable=True)
    stage: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("runtime_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    request_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    response_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    response_id_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    usage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    verified_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class AIUsageRecord(Base):
    """保存 Provider 报告或可验证估算的用量与成本。"""

    __tablename__ = "ai_usage_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "execution_id"],
            ["ai_executions.account_id", "ai_executions.id"],
            ondelete="RESTRICT",
            name="fk_ai_usage_execution_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "job_id"],
            ["ai_execution_jobs.account_id", "ai_execution_jobs.id"],
            ondelete="RESTRICT",
            name="fk_ai_usage_job_account",
        ),
        CheckConstraint(
            "cost_source IN ('reported','estimated','unavailable')",
            name="ck_ai_usage_cost_source",
        ),
        UniqueConstraint("account_id", "id", name="uq_ai_usage_account_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    provider_profile_id: Mapped[str] = mapped_column(String, nullable=False)
    model_profile_id: Mapped[str] = mapped_column(String, nullable=False)
    input_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_micros: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    cost_source: Mapped[str] = mapped_column(String, nullable=False)
    pricing_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_usage_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class AIExecutionOutput(Base):
    """保存账号受控输出的引用和安全摘要。"""

    __tablename__ = "ai_execution_outputs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "execution_id"],
            ["ai_executions.account_id", "ai_executions.id"],
            ondelete="RESTRICT",
            name="fk_ai_outputs_execution_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "job_id"],
            ["ai_execution_jobs.account_id", "ai_execution_jobs.id"],
            ondelete="RESTRICT",
            name="fk_ai_outputs_job_account",
        ),
        CheckConstraint("byte_size >= 0", name="ck_ai_outputs_byte_size"),
        UniqueConstraint("account_id", "id", name="uq_ai_outputs_account_id"),
        Index("ix_ai_outputs_account_execution", "account_id", "execution_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    content_ref: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_status: Mapped[str] = mapped_column(String, nullable=False)
    safe_summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    quarantined: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class AIErrorEvidence(Base):
    """保存不含外部正文的稳定错误证据。"""

    __tablename__ = "ai_error_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "execution_id"],
            ["ai_executions.account_id", "ai_executions.id"],
            ondelete="RESTRICT",
            name="fk_ai_errors_execution_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "job_id"],
            ["ai_execution_jobs.account_id", "ai_execution_jobs.id"],
            ondelete="RESTRICT",
            name="fk_ai_errors_job_account",
        ),
        UniqueConstraint("account_id", "id", name="uq_ai_errors_account_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    stage: Mapped[str] = mapped_column(String, nullable=False)
    error_code: Mapped[str] = mapped_column(String, nullable=False)
    provider_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    safe_summary: Mapped[str] = mapped_column(Text, nullable=False)
    provider_request_id_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    response_body_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    log_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


__all__ = [
    "AIErrorEvidence",
    "AIExecutionOutput",
    "AIProviderValidationRun",
    "AIUsageRecord",
]
