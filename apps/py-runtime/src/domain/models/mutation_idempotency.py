from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class RuntimeMutationIdempotency(Base):
    """保存普通写操作的作用域幂等结果，不复用长任务表。"""

    __tablename__ = "runtime_mutation_idempotency"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('system','account')",
            name="ck_runtime_mutation_scope",
        ),
        CheckConstraint(
            "(scope = 'system' AND account_id IS NULL) OR "
            "(scope = 'account' AND account_id IS NOT NULL "
            "AND length(trim(account_id)) > 0)",
            name="ck_runtime_mutation_account_scope",
        ),
        CheckConstraint(
            "length(trim(operation_name)) > 0 "
            "AND operation_name = trim(operation_name)",
            name="ck_runtime_mutation_operation",
        ),
        CheckConstraint(
            "length(idempotency_key_hash) = 64 "
            "AND idempotency_key_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_runtime_mutation_idempotency_hash",
        ),
        CheckConstraint(
            "length(request_hash) = 64 "
            "AND request_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_runtime_mutation_request_hash",
        ),
        CheckConstraint(
            "length(trim(response_json)) > 0",
            name="ck_runtime_mutation_response",
        ),
        CheckConstraint(
            "(resource_type IS NULL AND resource_id IS NULL) OR "
            "(resource_type IS NOT NULL AND resource_id IS NOT NULL "
            "AND length(trim(resource_type)) > 0 "
            "AND resource_type = trim(resource_type) "
            "AND length(trim(resource_id)) > 0 "
            "AND resource_id = trim(resource_id))",
            name="ck_runtime_mutation_resource",
        ),
        CheckConstraint(
            "length(trim(created_at)) > 0 "
            "AND length(trim(expires_at)) > 0 "
            "AND expires_at > created_at",
            name="ck_runtime_mutation_retention",
        ),
        Index(
            "uq_runtime_mutation_system_idempotency",
            "operation_name",
            "idempotency_key_hash",
            unique=True,
            sqlite_where=text("scope = 'system' AND account_id IS NULL"),
        ),
        Index(
            "uq_runtime_mutation_account_idempotency",
            "account_id",
            "operation_name",
            "idempotency_key_hash",
            unique=True,
            sqlite_where=text("scope = 'account' AND account_id IS NOT NULL"),
        ),
        Index(
            "ix_runtime_mutation_expires_at",
            "expires_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    account_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(
            "accounts.id",
            name="fk_runtime_mutation_account_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    operation_name: Mapped[str] = mapped_column(String, nullable=False)
    idempotency_key_hash: Mapped[str] = mapped_column(String, nullable=False)
    request_hash: Mapped[str] = mapped_column(String, nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
