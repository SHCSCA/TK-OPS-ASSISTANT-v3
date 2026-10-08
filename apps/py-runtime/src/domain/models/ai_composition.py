from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class CompositionTemplateProfile(Base):
    """保存受控 CompositionSpec 模板的不可覆盖版本。"""

    __tablename__ = "composition_template_profiles"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','archived')",
            name="ck_composition_templates_status",
        ),
        CheckConstraint(
            "template_type IN "
            "('slideshow','talking_head','product_showcase','mixed_media')",
            name="ck_composition_templates_type",
        ),
        CheckConstraint(
            "version >= 1 AND revision >= 1",
            name="ck_composition_templates_version",
        ),
        UniqueConstraint(
            "template_key",
            "version",
            name="uq_composition_templates_key_version",
        ),
        Index(
            "uq_composition_templates_one_active",
            "template_key",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_key: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    template_type: Mapped[str] = mapped_column(String, nullable=False)
    aspect_ratios_json: Mapped[str] = mapped_column(Text, nullable=False)
    parameter_schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    composition_spec_template_json: Mapped[str] = mapped_column(Text, nullable=False)
    compatible_capabilities_json: Mapped[str] = mapped_column(Text, nullable=False)
    preview_asset_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    dependency_snapshot_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("ai_dependency_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
    )
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_from_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("composition_template_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[str | None] = mapped_column(Text, nullable=True)
