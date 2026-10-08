from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class AIDependencySnapshot(Base):
    """保存配置激活和执行预检的不可变依赖图。"""

    __tablename__ = "ai_dependency_snapshots"
    __table_args__ = (
        CheckConstraint(
            "owner_type IN ('route','recipe','composition_template','execution_preflight')",
            name="ck_ai_dependency_snapshots_owner",
        ),
        CheckConstraint(
            "status IN ('valid','invalid')",
            name="ck_ai_dependency_snapshots_status",
        ),
        UniqueConstraint("owner_type", "owner_id", "owner_revision", name="uq_ai_dependency_owner"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_type: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[str] = mapped_column(String, nullable=False)
    owner_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    graph_json: Mapped[str] = mapped_column(Text, nullable=False)
    issues_json: Mapped[str] = mapped_column(Text, nullable=False)
    repair_actions_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class AIExecutionSnapshot(Base):
    """保存一次 AI 执行的不可变解析结果。"""

    __tablename__ = "ai_execution_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "positioning_profile_id"],
            ["positioning_profiles.account_id", "positioning_profiles.id"],
            ondelete="RESTRICT",
            name="fk_ai_execution_snapshots_positioning_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "knowledge_snapshot_id"],
            ["knowledge_snapshots.account_id", "knowledge_snapshots.id"],
            ondelete="RESTRICT",
            name="fk_ai_execution_snapshots_knowledge_account",
        ),
        ForeignKeyConstraint(
            ["account_id", "account_recipe_id"],
            ["account_ai_recipes.account_id", "account_ai_recipes.id"],
            ondelete="RESTRICT",
            name="fk_ai_execution_snapshots_recipe_account",
        ),
        UniqueConstraint("account_id", "id", name="uq_ai_execution_snapshots_account_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    capability_key: Mapped[str] = mapped_column(String, nullable=False)
    account_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_config_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    positioning_profile_id: Mapped[str | None] = mapped_column(String, nullable=True)
    positioning_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    positioning_content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    knowledge_snapshot_id: Mapped[str] = mapped_column(String, nullable=False)
    knowledge_snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_content_hash: Mapped[str] = mapped_column(String, nullable=False)
    account_recipe_id: Mapped[str] = mapped_column(String, nullable=False)
    recipe_version: Mapped[int] = mapped_column(Integer, nullable=False)
    recipe_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    recipe_content_hash: Mapped[str] = mapped_column(String, nullable=False)
    capability_route_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("capability_routes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    route_revision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("capability_route_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    route_content_hash: Mapped[str] = mapped_column(String, nullable=False)
    prompt_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("prompt_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    prompt_version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_content_hash: Mapped[str] = mapped_column(String, nullable=False)
    rendered_prompt_hash: Mapped[str] = mapped_column(String, nullable=False)
    dependency_snapshot_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("ai_dependency_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    input_schema_hash: Mapped[str] = mapped_column(String, nullable=False)
    output_schema_hash: Mapped[str] = mapped_column(String, nullable=False)
    policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String, nullable=False)
    context_manifest_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class AIExecutionCandidate(Base):
    """保存执行创建时冻结的候选顺序与限制。"""

    __tablename__ = "ai_execution_candidates"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "execution_snapshot_id"],
            ["ai_execution_snapshots.account_id", "ai_execution_snapshots.id"],
            ondelete="RESTRICT",
            name="fk_ai_execution_candidates_snapshot_account",
        ),
        CheckConstraint("ordinal >= 0", name="ck_ai_execution_candidates_ordinal"),
        UniqueConstraint("account_id", "id", name="uq_ai_execution_candidates_account_id"),
        UniqueConstraint(
            "execution_snapshot_id",
            "ordinal",
            name="uq_ai_execution_candidates_snapshot_ordinal",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False)
    execution_snapshot_id: Mapped[str] = mapped_column(String, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("provider_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_revision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("provider_profile_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    adapter_type: Mapped[str] = mapped_column(String, nullable=False)
    credential_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("model_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_revision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("model_profile_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    capability_contract_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("ai_provider_validation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    max_cost_micros: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    extra_params_json: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String, nullable=False)


__all__ = [
    "AIDependencySnapshot",
    "AIExecutionCandidate",
    "AIExecutionSnapshot",
]
