from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base, generate_uuid


class DeviceWorkspace(Base):
    __tablename__ = "device_workspaces"
    __table_args__ = (
        Index("ix_device_workspaces_account_updated", "account_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    account_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(
            "accounts.id",
            name="fk_device_workspaces_account_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    root_ref: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    ownership_state: Mapped[str] = mapped_column(
        String, nullable=False, default="legacy_unclaimed"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="offline")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ExecutionBinding(Base):
    __tablename__ = "execution_bindings"
    __table_args__ = (
        Index("ix_execution_bindings_account_updated", "account_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("device_workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    browser_instance_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(
            "browser_instances.id",
            name="fk_execution_bindings_browser_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_retry_of_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DeviceWorkspaceLog(Base):
    __tablename__ = "device_workspace_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("device_workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class BrowserInstance(Base):
    __tablename__ = "browser_instances"
    __table_args__ = (
        Index("ix_browser_instances_account_updated", "account_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    account_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(
            "accounts.id",
            name="fk_browser_instances_account_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("device_workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    profile_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="stopped")
    process_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debug_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debug_host: Mapped[str | None] = mapped_column(String, nullable=True)
    runtime_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    executable_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ownership_state: Mapped[str] = mapped_column(
        String, nullable=False, default="legacy_unclaimed"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
