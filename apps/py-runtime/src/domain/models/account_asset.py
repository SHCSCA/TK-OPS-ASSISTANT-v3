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


class AccountAsset(Base):
    """保存账号受控文件的元数据和授权证据。"""

    __tablename__ = "account_assets"
    __table_args__ = (
        CheckConstraint(
            "source_kind IN ('controlled_file')",
            name="ck_account_assets_source_kind",
        ),
        CheckConstraint(
            "status IN ('pending','ready','metadata_only','failed','stale')",
            name="ck_account_assets_status",
        ),
        CheckConstraint(
            "byte_size >= 0 AND revision >= 1",
            name="ck_account_assets_limits",
        ),
        UniqueConstraint("account_id", "id", name="uq_account_assets_account_id"),
        UniqueConstraint(
            "account_id",
            "controlled_file_ref",
            "revision",
            name="uq_account_assets_file_revision",
        ),
        Index("ix_account_assets_account_updated", "account_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    controlled_file_ref: Mapped[str] = mapped_column(String, nullable=False)
    root_ref: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(String, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    authorization_basis: Mapped[str] = mapped_column(String, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class KnowledgeSourceAsset(Base):
    """绑定同账号 KnowledgeSource 与 AccountAsset。"""

    __tablename__ = "knowledge_source_assets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "knowledge_source_id"],
            ["knowledge_sources.account_id", "knowledge_sources.id"],
            ondelete="RESTRICT",
            name="fk_knowledge_source_assets_source_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "account_asset_id"],
            ["account_assets.account_id", "account_assets.id"],
            ondelete="RESTRICT",
            name="fk_knowledge_source_assets_asset_account",
        ),
    )

    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    knowledge_source_id: Mapped[str] = mapped_column(String, primary_key=True)
    account_asset_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class KnowledgeIndexChunk(Base):
    """保存知识索引派生文本的账号隔离引用。"""

    __tablename__ = "knowledge_index_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "knowledge_source_id"],
            ["knowledge_sources.account_id", "knowledge_sources.id"],
            ondelete="RESTRICT",
            name="fk_knowledge_chunks_source_account",
        ),
        CheckConstraint(
            "source_revision >= 1 AND ordinal >= 0 AND token_count >= 0",
            name="ck_knowledge_index_chunks_limits",
        ),
        UniqueConstraint("account_id", "id", name="uq_knowledge_chunks_account_id"),
        UniqueConstraint(
            "knowledge_source_id",
            "source_revision",
            "ordinal",
            name="uq_knowledge_chunks_source_revision_ordinal",
        ),
        Index(
            "ix_knowledge_chunks_account_source",
            "account_id",
            "knowledge_source_id",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knowledge_source_id: Mapped[str] = mapped_column(String, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content_ref: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    extractor_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


__all__ = ["AccountAsset", "KnowledgeIndexChunk", "KnowledgeSourceAsset"]
