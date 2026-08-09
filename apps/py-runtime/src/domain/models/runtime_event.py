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


class RuntimeEvent(Base):
    __tablename__ = "runtime_events"
    __table_args__ = (
        CheckConstraint(
            "length(trim(topic)) > 0",
            name="ck_runtime_events_topic",
        ),
        CheckConstraint(
            "(account_id IS NULL AND topic LIKE 'system:%' "
            "AND length(topic) > length('system:')) OR "
            "(account_id IS NOT NULL AND length(trim(account_id)) > 0 "
            "AND substr(topic, 1, length('account:' || account_id || ':')) = "
            "'account:' || account_id || ':' "
            "AND length(topic) > length('account:' || account_id || ':'))",
            name="ck_runtime_events_account_topic",
        ),
        CheckConstraint(
            "sequence >= 1",
            name="ck_runtime_events_sequence",
        ),
        UniqueConstraint("topic", "sequence", name="uq_runtime_events_topic_sequence"),
        Index("ix_runtime_events_account_occurred", "account_id", "occurred_at"),
        Index("ix_runtime_events_unpublished", "published_at", "occurred_at"),
    )

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    account_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    aggregate_type: Mapped[str | None] = mapped_column(String, nullable=True)
    aggregate_id: Mapped[str | None] = mapped_column(String, nullable=True)
    task_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("runtime_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[str | None] = mapped_column(Text, nullable=True)
