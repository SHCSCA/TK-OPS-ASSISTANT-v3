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


class AccountKnowledgeBase(Base):
    """保存账号知识规则、索引修订和健康状态。"""

    __tablename__ = "account_knowledge_bases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('empty','indexing','ready','stale','attention')",
            name="ck_knowledge_bases_status",
        ),
        CheckConstraint(
            "rules_version >= 0 AND index_revision >= 0 AND revision >= 1",
            name="ck_knowledge_bases_revision",
        ),
        UniqueConstraint(
            "account_id",
            name="uq_account_knowledge_bases_account",
        ),
        Index(
            "ix_knowledge_bases_account_updated",
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
    status: Mapped[str] = mapped_column(String, nullable=False)
    rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    rules_version: Mapped[int] = mapped_column(Integer, nullable=False)
    index_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    last_indexed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class KnowledgeSource(Base):
    """保存账号知识来源及其可审计索引状态。"""

    __tablename__ = "knowledge_sources"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('document','image','video','audio','text','reference')",
            name="ck_knowledge_sources_kind",
        ),
        CheckConstraint(
            "status IN ('pending','indexing','ready','failed','stale')",
            name="ck_knowledge_sources_status",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_knowledge_sources_revision",
        ),
        CheckConstraint(
            "source_mode IN ('file','url','text')",
            name="ck_knowledge_sources_source_mode",
        ),
        CheckConstraint(
            "(source_mode = 'url' AND source_url IS NOT NULL "
            "AND length(trim(source_url)) > 0 "
            "AND source_url = trim(source_url) "
            "AND (lower(source_url) LIKE 'http://%' "
            "OR lower(source_url) LIKE 'https://%')) "
            "OR (source_mode IN ('file','text') AND source_url IS NULL)",
            name="ck_knowledge_sources_source_url",
        ),
        Index(
            "ix_knowledge_sources_account_updated",
            "account_id",
            "updated_at",
        ),
        Index(
            "ix_knowledge_sources_account_mode_updated",
            "account_id",
            "source_mode",
            "updated_at",
        ),
        Index(
            "uq_knowledge_sources_account_id",
            "account_id",
            "id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("account_knowledge_bases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_mode: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class KnowledgeSnapshot(Base):
    """保存生成任务可引用的不可变知识快照。"""

    __tablename__ = "knowledge_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "snapshot_version",
            name="uq_knowledge_snapshots_account_version",
        ),
        Index(
            "ix_knowledge_snapshots_account_created",
            "account_id",
            "created_at",
        ),
        Index(
            "uq_knowledge_snapshots_account_id",
            "account_id",
            "id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("account_knowledge_bases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False)
    positioning_profile_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("positioning_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    rules_version: Mapped[int] = mapped_column(Integer, nullable=False)
    index_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
