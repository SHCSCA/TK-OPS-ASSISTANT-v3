"""扩展 P0 账号与 AI 配置基础结构。"""

from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa


revision = "0015_p0_expand"
down_revision = "0014_magic_cut_suggestion_drafts"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)


_P0_TABLES = (
    "account_connections",
    "positioning_profiles",
    "account_knowledge_bases",
    "knowledge_sources",
    "knowledge_snapshots",
    "brand_kits",
    "account_publish_defaults",
    "account_config_copy_runs",
    "provider_profiles",
    "model_profiles",
    "model_capabilities",
    "prompt_profiles",
    "capability_routes",
    "composition_template_profiles",
    "account_ai_recipes",
    "runtime_tasks",
    "runtime_events",
)
_ORM_ONLY_TABLES = (
    "asset_groups",
    "device_workspace_logs",
    "export_profiles",
    "publish_receipts",
)
_DOWNGRADE_COLUMN_DATA_CHECKS = (
    ("system_config", "ai_config_revision", "ai_config_revision IS NOT NULL AND ai_config_revision <> 0"),
    (
        "execution_bindings",
        "browser_instance_id",
        "browser_instance_id IS NOT NULL AND trim(browser_instance_id) <> ''",
    ),
    (
        "browser_instances",
        "account_id",
        "account_id IS NOT NULL AND trim(account_id) <> ''",
    ),
    (
        "device_workspaces",
        "account_id",
        "account_id IS NOT NULL AND trim(account_id) <> ''",
    ),
    ("accounts", "revision", "revision IS NOT NULL AND revision <> 1"),
    ("accounts", "archived_at", "archived_at IS NOT NULL AND trim(archived_at) <> ''"),
    (
        "accounts",
        "last_health_checked_at",
        "last_health_checked_at IS NOT NULL AND trim(last_health_checked_at) <> ''",
    ),
    ("accounts", "last_used_at", "last_used_at IS NOT NULL AND trim(last_used_at) <> ''"),
    (
        "accounts",
        "status_reason_code",
        "status_reason_code IS NOT NULL AND trim(status_reason_code) <> ''",
    ),
    (
        "accounts",
        "wizard_completed_at",
        "wizard_completed_at IS NOT NULL AND trim(wizard_completed_at) <> ''",
    ),
    (
        "accounts",
        "platform_account_id",
        "platform_account_id IS NOT NULL AND trim(platform_account_id) <> ''",
    ),
    (
        "accounts",
        "last_validated_at",
        "last_validated_at IS NOT NULL AND trim(last_validated_at) <> ''",
    ),
    (
        "subtitle_tracks",
        "updated_at",
        "updated_at IS NOT NULL AND trim(updated_at) <> ''",
    ),
    (
        "subtitle_tracks",
        "metadata_json",
        "metadata_json IS NOT NULL AND trim(metadata_json) NOT IN ('', '{}')",
    ),
    (
        "voice_tracks",
        "updated_at",
        "updated_at IS NOT NULL AND trim(updated_at) <> ''",
    ),
    (
        "voice_tracks",
        "config_json",
        "config_json IS NOT NULL AND trim(config_json) NOT IN ('', '{}')",
    ),
    ("voice_tracks", "version", "version IS NOT NULL AND version <> 1"),
    (
        "assets",
        "thumbnail_generated_at",
        "thumbnail_generated_at IS NOT NULL AND trim(thumbnail_generated_at) <> ''",
    ),
    ("assets", "group_id", "group_id IS NOT NULL AND trim(group_id) <> ''"),
    ("projects", "deleted_at", "deleted_at IS NOT NULL AND trim(deleted_at) <> ''"),
)


def upgrade() -> None:
    _reconcile_0014_schema()
    _extend_existing_aggregates()
    _create_account_configuration_tables()
    _create_ai_configuration_tables()
    _create_runtime_audit_tables()


def _reconcile_0014_schema() -> None:
    _create_table(
        "asset_groups",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["asset_groups.id"], ondelete="SET NULL"),
    )
    _create_table(
        "device_workspace_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["device_workspaces.id"], ondelete="CASCADE"
        ),
    )
    _create_table(
        "export_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("resolution", sa.String(), nullable=False),
        sa.Column("fps", sa.Integer(), nullable=False),
        sa.Column("video_bitrate", sa.String(), nullable=False),
        sa.Column("audio_policy", sa.String(), nullable=False),
        sa.Column("subtitle_policy", sa.String(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("name", name="uq_export_profiles_name"),
    )
    _create_table(
        "publish_receipts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("platform_response_json", sa.Text(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["publish_plans.id"], ondelete="CASCADE"),
    )
    _ensure_column("projects", sa.Column("deleted_at", sa.Text(), nullable=True))
    _ensure_column("accounts", sa.Column("last_validated_at", sa.Text(), nullable=True))
    _ensure_column("assets", sa.Column("group_id", sa.String(), nullable=True))
    _ensure_column("assets", sa.Column("thumbnail_generated_at", sa.Text(), nullable=True))
    _ensure_column(
        "voice_tracks",
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    _ensure_column(
        "voice_tracks",
        sa.Column(
            "config_json",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    _ensure_track_updated_at("voice_tracks")
    _ensure_column(
        "subtitle_tracks",
        sa.Column(
            "metadata_json",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    _ensure_track_updated_at("subtitle_tracks")


def _extend_existing_aggregates() -> None:
    for column in (
        sa.Column("platform_account_id", sa.Text(), nullable=True),
        sa.Column("wizard_completed_at", sa.Text(), nullable=True),
        sa.Column("status_reason_code", sa.String(), nullable=True),
        sa.Column("last_used_at", sa.Text(), nullable=True),
        sa.Column("last_health_checked_at", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=True, server_default=sa.text("1")),
    ):
        _ensure_column("accounts", column)
    _ensure_column("device_workspaces", sa.Column("account_id", sa.String(), nullable=True))
    _ensure_column("browser_instances", sa.Column("account_id", sa.String(), nullable=True))
    _ensure_column(
        "execution_bindings", sa.Column("browser_instance_id", sa.String(), nullable=True)
    )
    _ensure_column(
        "system_config",
        sa.Column("ai_config_revision", sa.Integer(), nullable=True, server_default=sa.text("0")),
    )


def _create_account_configuration_tables() -> None:
    account_fk = "accounts.id"
    _create_table(
        "account_connections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("credential_ref", sa.Text(), nullable=True),
        sa.Column("session_ref", sa.Text(), nullable=True),
        sa.Column("auth_status", sa.String(), nullable=False),
        sa.Column("health_status", sa.String(), nullable=False),
        sa.Column("active_execution_binding_id", sa.String(), nullable=True),
        sa.Column("last_checked_at", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_log_id", sa.String(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], [account_fk], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["active_execution_binding_id"], ["execution_bindings.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("account_id", name="uq_account_connections_account"),
    )
    _create_versioned_account_table(
        "positioning_profiles",
        sa.Column("audience_json", sa.Text(), nullable=False),
        sa.Column("content_pillars_json", sa.Text(), nullable=False),
        sa.Column("voice_style_json", sa.Text(), nullable=False),
        sa.Column("prohibited_terms_json", sa.Text(), nullable=False),
        sa.Column("publishing_constraints_json", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
    )
    _create_table(
        "account_knowledge_bases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("rules_json", sa.Text(), nullable=False),
        sa.Column("rules_version", sa.Integer(), nullable=False),
        sa.Column("index_revision", sa.Integer(), nullable=False),
        sa.Column("last_indexed_at", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_log_id", sa.String(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], [account_fk], ondelete="RESTRICT"),
        sa.UniqueConstraint("account_id", name="uq_account_knowledge_bases_account"),
    )
    _create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_log_id", sa.String(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], [account_fk], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"], ["account_knowledge_bases.id"], ondelete="RESTRICT"
        ),
    )
    _create_table(
        "knowledge_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("positioning_profile_id", sa.String(), nullable=True),
        sa.Column("rules_version", sa.Integer(), nullable=False),
        sa.Column("index_revision", sa.Integer(), nullable=False),
        sa.Column("source_manifest_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], [account_fk], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"], ["account_knowledge_bases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["positioning_profile_id"], ["positioning_profiles.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "account_id", "snapshot_version", name="uq_knowledge_snapshots_account_version"
        ),
    )
    _create_versioned_account_table(
        "brand_kits",
        sa.Column("visual_style_json", sa.Text(), nullable=False),
        sa.Column("colors_json", sa.Text(), nullable=False),
        sa.Column("fonts_json", sa.Text(), nullable=False),
        sa.Column("logo_asset_refs_json", sa.Text(), nullable=False),
        sa.Column("voice_rules_json", sa.Text(), nullable=False),
    )
    _create_table(
        "account_publish_defaults",
        sa.Column("account_id", sa.String(), primary_key=True),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("privacy_level", sa.String(), nullable=False),
        sa.Column("allow_comments", sa.Boolean(), nullable=False),
        sa.Column("allow_duet", sa.Boolean(), nullable=False),
        sa.Column("allow_stitch", sa.Boolean(), nullable=False),
        sa.Column("caption_rules_json", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], [account_fk], ondelete="RESTRICT"),
    )
    _create_table(
        "account_config_copy_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source_account_id", sa.String(), nullable=False),
        sa.Column("target_account_id", sa.String(), nullable=False),
        sa.Column("requested_sections_json", sa.Text(), nullable=False),
        sa.Column("copied_sections_json", sa.Text(), nullable=False),
        sa.Column("skipped_sections_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("operation_id", sa.String(), nullable=False),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_log_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_account_id"], [account_fk], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_account_id"], [account_fk], ondelete="RESTRICT"),
        sa.UniqueConstraint("operation_id", name="uq_account_config_copy_runs_operation"),
    )


def _create_versioned_account_table(table_name: str, *payload: sa.Column) -> None:
    _create_table(
        table_name,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        *payload,
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("activated_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "account_id", "version", name=f"uq_{table_name}_account_version"
        ),
    )


def _create_ai_configuration_tables() -> None:
    _create_table(
        "provider_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("adapter_type", sa.String(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("credential_ref", sa.Text(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("proxy_ref", sa.Text(), nullable=True),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("health_status", sa.String(), nullable=False),
        sa.Column("last_checked_at", sa.Text(), nullable=True),
        sa.Column("last_error_code", sa.String(), nullable=True),
        sa.Column("last_error_log_id", sa.String(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    _create_table(
        "model_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("provider_profile_id", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("discovery_source", sa.String(), nullable=False),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("base_limits_json", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_profile_id"], ["provider_profiles.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "provider_profile_id", "model_id", name="uq_model_profiles_provider_model"
        ),
    )
    _create_table(
        "model_capabilities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("model_profile_id", sa.String(), nullable=False),
        sa.Column("capability_key", sa.String(), nullable=False),
        sa.Column("declared_supported", sa.Boolean(), nullable=False),
        sa.Column("adapter_supported", sa.Boolean(), nullable=False),
        sa.Column("contract_verified", sa.Boolean(), nullable=False),
        sa.Column("input_modalities_json", sa.Text(), nullable=False),
        sa.Column("output_modalities_json", sa.Text(), nullable=False),
        sa.Column("parameter_schema_json", sa.Text(), nullable=False),
        sa.Column("source_urls_json", sa.Text(), nullable=False),
        sa.Column("known_limits_json", sa.Text(), nullable=False),
        sa.Column("verified_at", sa.Text(), nullable=True),
        sa.Column("contract_revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_profile_id"], ["model_profiles.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "model_profile_id", "capability_key", name="uq_model_capabilities_model_key"
        ),
    )
    _create_table(
        "prompt_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("profile_key", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("capability_key", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("task_template", sa.Text(), nullable=False),
        sa.Column("variables_schema_json", sa.Text(), nullable=False),
        sa.Column("output_schema_json", sa.Text(), nullable=False),
        sa.Column("visual_style_prefix", sa.Text(), nullable=True),
        sa.Column("safety_constraints_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("created_from_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("activated_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_from_id"], ["prompt_profiles.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("profile_key", "version", name="uq_prompt_profiles_key_version"),
    )
    _create_table(
        "capability_routes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("capability_key", sa.String(), nullable=False),
        sa.Column("primary_model_profile_id", sa.String(), nullable=True),
        sa.Column("fallback_model_profile_id", sa.String(), nullable=True),
        sa.Column("prompt_profile_id", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("validation_issues_json", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["primary_model_profile_id"], ["model_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["fallback_model_profile_id"], ["model_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["prompt_profile_id"], ["prompt_profiles.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("capability_key", name="uq_capability_routes_key"),
    )
    _create_table(
        "composition_template_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_key", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("template_type", sa.String(), nullable=False),
        sa.Column("aspect_ratios_json", sa.Text(), nullable=False),
        sa.Column("parameter_schema_json", sa.Text(), nullable=False),
        sa.Column("composition_spec_template_json", sa.Text(), nullable=False),
        sa.Column("compatible_capabilities_json", sa.Text(), nullable=False),
        sa.Column("preview_asset_ref", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_from_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("activated_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_from_id"], ["composition_template_profiles.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "template_key", "version", name="uq_composition_templates_key_version"
        ),
    )
    _create_table(
        "account_ai_recipes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("route_overrides_json", sa.Text(), nullable=False),
        sa.Column("visual_style_json", sa.Text(), nullable=False),
        sa.Column("voice_profile_ref", sa.Text(), nullable=True),
        sa.Column("composition_template_ref", sa.String(), nullable=True),
        sa.Column("cost_policy_json", sa.Text(), nullable=False),
        sa.Column("fallback_policy_json", sa.Text(), nullable=False),
        sa.Column("source_ai_config_revision", sa.Integer(), nullable=False),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("validation_issues_json", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_from_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("activated_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["composition_template_ref"], ["composition_template_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_from_id"], ["account_ai_recipes.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("account_id", "version", name="uq_account_ai_recipes_version"),
    )


def _create_runtime_audit_tables() -> None:
    _create_table(
        "runtime_tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("completion_kind", sa.String(), nullable=True),
        sa.Column("failure_kind", sa.String(), nullable=True),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("cancellable", sa.Boolean(), nullable=False),
        sa.Column("timeout_at", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("retry_of_task_id", sa.String(), nullable=True),
        sa.Column("config_snapshot_json", sa.Text(), nullable=False),
        sa.Column("result_ref", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_log_id", sa.String(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["retry_of_task_id"], ["runtime_tasks.id"], ondelete="SET NULL"
        ),
    )
    _create_table(
        "runtime_events",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("aggregate_type", sa.String(), nullable=True),
        sa.Column("aggregate_id", sa.String(), nullable=True),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("log_id", sa.String(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.Text(), nullable=False),
        sa.Column("published_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["runtime_tasks.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("topic", "sequence", name="uq_runtime_events_topic_sequence"),
    )


def downgrade() -> None:
    _refuse_lossy_downgrade()
    for table_name in reversed(_P0_TABLES):
        _drop_table_if_exists(table_name)
    for table_name, columns in _downgrade_columns().items():
        _drop_columns_if_exist(table_name, columns)
    for table_name in reversed(_ORM_ONLY_TABLES):
        _drop_table_if_exists(table_name)


def _create_table(table_name: str, *elements: sa.SchemaItem) -> None:
    if table_name not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(table_name, *elements)


def _ensure_column(table_name: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        log.error("P0 扩展迁移缺少前置表", extra={"table_name": table_name})
        raise RuntimeError(f"P0_MIGRATION_SCHEMA_MISSING: 缺少表 {table_name}")
    if column.name not in {item["name"] for item in inspector.get_columns(table_name)}:
        op.add_column(table_name, column)


def _ensure_track_updated_at(table_name: str) -> None:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        log.error("P0 扩展迁移缺少前置表", extra={"table_name": table_name})
        raise RuntimeError(f"P0_MIGRATION_SCHEMA_MISSING: 缺少表 {table_name}")
    columns = {item["name"]: item for item in inspector.get_columns(table_name)}
    updated_at = columns.get("updated_at")
    default_sql = str((updated_at or {}).get("default") or "").lower().replace(" ", "")
    if updated_at is not None and "datetime('now')" in default_sql:
        return
    with op.batch_alter_table(table_name, recreate="always") as batch:
        if updated_at is None:
            batch.add_column(
                sa.Column(
                    "updated_at",
                    sa.Text(),
                    nullable=False,
                    server_default=sa.text("datetime('now')"),
                )
            )
        else:
            batch.alter_column(
                "updated_at",
                existing_type=sa.Text(),
                existing_nullable=False,
                server_default=sa.text("datetime('now')"),
            )


def _drop_columns_if_exist(table_name: str, column_names: tuple[str, ...]) -> None:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return
    existing = {item["name"] for item in inspector.get_columns(table_name)}
    removable = [column_name for column_name in column_names if column_name in existing]
    if not removable:
        return
    if op.get_bind().dialect.name == "sqlite":
        # SQLite 需重建表，才能同时移除依赖待删字段的匿名外键。
        with op.batch_alter_table(table_name, recreate="always") as batch:
            for column_name in removable:
                batch.drop_column(column_name)
        return
    for column_name in removable:
        op.drop_column(table_name, column_name)


def _downgrade_columns() -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for table_name, column_name, _ in _DOWNGRADE_COLUMN_DATA_CHECKS:
        grouped.setdefault(table_name, []).append(column_name)
    return {table_name: tuple(columns) for table_name, columns in grouped.items()}


def _drop_table_if_exists(table_name: str) -> None:
    if table_name in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table(table_name)


def _refuse_lossy_downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    populated: list[str] = []
    for table_name in (*_P0_TABLES, *_ORM_ONLY_TABLES):
        if table_name not in inspector.get_table_names():
            continue
        if bind.execute(sa.text(f'SELECT 1 FROM "{table_name}" LIMIT 1')).first():
            populated.append(table_name)
    populated_columns: list[str] = []
    table_names = set(inspector.get_table_names())
    for table_name, column_name, condition in _DOWNGRADE_COLUMN_DATA_CHECKS:
        if table_name not in table_names:
            continue
        columns = {item["name"] for item in inspector.get_columns(table_name)}
        if column_name not in columns:
            continue
        query = sa.text(
            f'SELECT 1 FROM "{table_name}" WHERE {condition} LIMIT 1'
        )
        if bind.execute(query).first():
            populated_columns.append(f"{table_name}.{column_name}")
    if populated or populated_columns:
        names = ", ".join(sorted(populated)) or "无"
        column_names = ", ".join(sorted(populated_columns)) or "无"
        log.error(
            "P0 扩展迁移拒绝有数据降级",
            extra={"table_names": names, "column_names": column_names},
        )
        raise RuntimeError(
            "P0_DOWNGRADE_REQUIRES_BACKUP: 新结构已有数据，无法无损降级；"
            f"请恢复迁移前备份。涉及表：{names}；涉及字段：{column_names}"
        )
