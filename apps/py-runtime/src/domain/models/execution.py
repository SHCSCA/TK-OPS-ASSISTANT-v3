from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    handle: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    group_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class DeviceWorkspace(Base):
    __tablename__ = "device_workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    device_type: Mapped[str] = mapped_column(String, nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    browser_profile: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    health_json: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ExecutionBinding(Base):
    __tablename__ = "execution_bindings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
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
    status: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class AutomationTask(Base):
    __tablename__ = "automation_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    binding_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("execution_bindings.id", ondelete="SET NULL"),
        nullable=True,
    )
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    schedule_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class PublishPlan(Base):
    __tablename__ = "publish_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    binding_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("execution_bindings.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    scheduled_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
