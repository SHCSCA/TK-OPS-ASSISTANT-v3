from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base, generate_uuid


class AccountLoginSession(Base):
    __tablename__ = "account_login_sessions"
    __table_args__ = (
        Index(
            "ix_account_login_sessions_account_updated",
            "account_id",
            "updated_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_binding_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("execution_bindings.id", ondelete="CASCADE"),
        nullable=False,
    )
    browser_instance_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("browser_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String, nullable=False)
    prepare_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    probe_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    expected_identity: Mapped[str] = mapped_column(Text, nullable=False)
    detected_identity: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
