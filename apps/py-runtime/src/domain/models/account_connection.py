from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class AccountConnection(Base):
    """保存账号与真实执行环境之间的当前连接状态。"""

    __tablename__ = "account_connections"
    __table_args__ = (
        CheckConstraint(
            "auth_status IN ('unknown','required','valid','expired','failed')",
            name="ck_account_connections_auth_status",
        ),
        CheckConstraint(
            "health_status IN ('unknown','checking','ready','attention','failed')",
            name="ck_account_connections_health_status",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_account_connections_revision",
        ),
        UniqueConstraint(
            "account_id",
            name="uq_account_connections_account",
        ),
        Index(
            "ix_account_connections_account_updated",
            "account_id",
            "updated_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    credential_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_status: Mapped[str] = mapped_column(String, nullable=False)
    health_status: Mapped[str] = mapped_column(String, nullable=False)
    active_execution_binding_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("execution_bindings.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_checked_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
