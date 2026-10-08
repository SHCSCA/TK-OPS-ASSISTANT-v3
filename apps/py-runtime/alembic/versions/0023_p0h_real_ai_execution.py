"""新增 P0-H 真实 AI 执行、证据和受控资产模型。

Revision ID: 0023_p0h_real_ai_execution
Revises: 0022_p0g_production_hardening
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, NoReturn

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Connection

revision = "0023_p0h_real_ai_execution"
down_revision = "0022_p0g_production_hardening"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)


def upgrade() -> None:
    connection = op.get_bind()
    _validate_required_tables(connection)
    _add_base_columns()
    _create_dependency_and_revision_tables()
    _backfill_configuration_revisions(connection)
    _link_base_tables()
    _create_validation_and_asset_tables()
    _create_execution_tables()
    _validate_upgrade(connection)


def downgrade() -> None:
    connection = op.get_bind()
    _refuse_data_bearing_downgrade(connection)
    _drop_execution_tables()
    _drop_asset_and_validation_tables()
    _unlink_base_tables()
    _drop_revision_and_dependency_tables()


def _add_base_columns() -> None:
    op.add_column("provider_profiles", sa.Column("extra_params_json", sa.Text()))
    op.add_column("provider_profiles", sa.Column("cost_policy_json", sa.Text()))
    op.add_column("provider_profiles", sa.Column("active_revision_id", sa.String()))
    op.add_column("model_profiles", sa.Column("active_revision_id", sa.String()))
    op.add_column("capability_routes", sa.Column("active_revision_id", sa.String()))
    op.add_column("account_ai_recipes", sa.Column("dependency_snapshot_id", sa.String()))
    op.add_column(
        "composition_template_profiles",
        sa.Column("dependency_snapshot_id", sa.String()),
    )


def _create_dependency_and_revision_tables() -> None:
    op.create_table(
        "ai_dependency_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_type", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("owner_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("graph_json", sa.Text(), nullable=False),
        sa.Column("issues_json", sa.Text(), nullable=False),
        sa.Column("repair_actions_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint("owner_type IN ('route','recipe','composition_template','execution_preflight')", name="ck_ai_dependency_snapshots_owner"),
        sa.CheckConstraint("status IN ('valid','invalid')", name="ck_ai_dependency_snapshots_status"),
        sa.UniqueConstraint("owner_type", "owner_id", "owner_revision", name="uq_ai_dependency_owner"),
    )
    op.create_table(
        "provider_profile_revisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("provider_profile_id", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("adapter_type", sa.String(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("base_url_hash", sa.String(), nullable=False),
        sa.Column("region", sa.String()),
        sa.Column("proxy_ref", sa.Text()),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("extra_params_json", sa.Text(), nullable=False),
        sa.Column("cost_policy_json", sa.Text(), nullable=False),
        sa.Column("credential_ref", sa.Text()),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["provider_profile_id"], ["provider_profiles.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("revision >= 1", name="ck_provider_revisions_revision"),
        sa.UniqueConstraint("provider_profile_id", "revision", name="uq_provider_revisions_profile_revision"),
        sa.UniqueConstraint("provider_profile_id", "id", name="uq_provider_revisions_profile_id"),
    )
    op.create_table(
        "model_profile_revisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("model_profile_id", sa.String(), nullable=False),
        sa.Column("provider_profile_revision_id", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("context_window", sa.Integer()),
        sa.Column("base_limits_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["model_profile_id"], ["model_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_profile_revision_id"], ["provider_profile_revisions.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("revision >= 1", name="ck_model_revisions_revision"),
        sa.UniqueConstraint("model_profile_id", "revision", name="uq_model_revisions_profile_revision"),
        sa.UniqueConstraint("model_profile_id", "id", name="uq_model_revisions_profile_id"),
    )
    op.create_table(
        "capability_route_revisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("capability_route_id", sa.String(), nullable=False),
        sa.Column("capability_key", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("prompt_profile_id", sa.String()),
        sa.Column("candidate_policy_json", sa.Text(), nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("retry_policy_json", sa.Text(), nullable=False),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("max_cost_micros", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("dependency_snapshot_id", sa.String()),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["capability_route_id"], ["capability_routes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["prompt_profile_id"], ["prompt_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dependency_snapshot_id"], ["ai_dependency_snapshots.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('draft','active','archived')", name="ck_route_revisions_status"),
        sa.CheckConstraint("revision >= 1 AND timeout_ms > 0 AND max_retries >= 0 AND max_concurrency > 0 AND max_cost_micros >= 0", name="ck_route_revisions_limits"),
        sa.UniqueConstraint("capability_route_id", "revision", name="uq_route_revisions_route_revision"),
        sa.UniqueConstraint("capability_route_id", "id", name="uq_route_revisions_route_id"),
    )
    op.create_index("uq_route_revisions_one_active", "capability_route_revisions", ["capability_route_id"], unique=True, sqlite_where=sa.text("status = 'active'"))


def _backfill_configuration_revisions(connection: Connection) -> None:
    providers = connection.execute(sa.text("SELECT * FROM provider_profiles")).mappings().all()
    for row in providers:
        extra = {"protocolVariant": "chat_completions"} if row["adapter_type"] == "openai_compatible" else {}
        cost = {"mode": "unavailable"}
        revision_id = _stable_id("provider", row["id"], row["revision"])
        values = {"adapter_type": row["adapter_type"], "base_url": row["base_url"], "region": row["region"], "proxy_ref": row["proxy_ref"], "timeout_ms": row["timeout_ms"], "max_concurrency": row["max_concurrency"], "extra_params": extra, "cost_policy": cost, "credential_ref": row["credential_ref"]}
        connection.execute(sa.text("UPDATE provider_profiles SET extra_params_json=:extra, cost_policy_json=:cost WHERE id=:id"), {"extra": _json(extra), "cost": _json(cost), "id": row["id"]})
        connection.execute(sa.text("INSERT INTO provider_profile_revisions (id,provider_profile_id,revision,adapter_type,base_url,base_url_hash,region,proxy_ref,timeout_ms,max_concurrency,extra_params_json,cost_policy_json,credential_ref,content_hash,created_at) VALUES (:rid,:id,:revision,:adapter_type,:base_url,:base_url_hash,:region,:proxy_ref,:timeout_ms,:max_concurrency,:extra,:cost,:credential_ref,:content_hash,:created_at)"), {**row, "rid": revision_id, "base_url_hash": _hash(row["base_url"]), "extra": _json(extra), "cost": _json(cost), "content_hash": _hash(_json(values))})
        connection.execute(sa.text("UPDATE provider_profiles SET active_revision_id=:rid WHERE id=:id"), {"rid": revision_id, "id": row["id"]})
    models = connection.execute(sa.text("SELECT m.*, p.active_revision_id AS provider_revision_id FROM model_profiles m JOIN provider_profiles p ON p.id=m.provider_profile_id")).mappings().all()
    for row in models:
        revision_id = _stable_id("model", row["id"], row["revision"])
        values = {"provider_revision_id": row["provider_revision_id"], "model_id": row["model_id"], "display_name": row["display_name"], "enabled": bool(row["enabled"]), "context_window": row["context_window"], "base_limits": _safe_json(row["base_limits_json"])}
        connection.execute(sa.text("INSERT INTO model_profile_revisions (id,model_profile_id,provider_profile_revision_id,revision,model_id,display_name,enabled,context_window,base_limits_json,content_hash,created_at) VALUES (:rid,:id,:provider_revision_id,:revision,:model_id,:display_name,:enabled,:context_window,:base_limits_json,:content_hash,:created_at)"), {**row, "rid": revision_id, "content_hash": _hash(_json(values))})
        connection.execute(sa.text("UPDATE model_profiles SET active_revision_id=:rid WHERE id=:id"), {"rid": revision_id, "id": row["id"]})
    routes = connection.execute(sa.text("SELECT * FROM capability_routes")).mappings().all()
    for row in routes:
        revision_id = _stable_id("route", row["id"], row["revision"])
        candidates = [item for item in (row["primary_model_profile_id"], row["fallback_model_profile_id"]) if item]
        policy = {"candidates": [{"modelProfileId": item} for item in candidates]}
        values = {"capability_key": row["capability_key"], "prompt_profile_id": row["prompt_profile_id"], "candidate_policy": policy, "timeout_ms": 60000, "max_retries": 0, "retry_policy": {"retryableCategories": [], "fallbackCategories": []}, "max_concurrency": 1, "max_cost_micros": 0, "currency": "USD", "enabled": bool(row["enabled"])}
        connection.execute(sa.text("INSERT INTO capability_route_revisions (id,capability_route_id,capability_key,revision,status,prompt_profile_id,candidate_policy_json,timeout_ms,max_retries,retry_policy_json,max_concurrency,max_cost_micros,currency,enabled,dependency_snapshot_id,content_hash,created_at) VALUES (:rid,:id,:capability_key,:revision,'draft',:prompt_profile_id,:candidate_policy,60000,0,:retry_policy,1,0,'USD',:enabled,NULL,:content_hash,:created_at)"), {**row, "rid": revision_id, "candidate_policy": _json(policy), "retry_policy": _json(values["retry_policy"]), "content_hash": _hash(_json(values))})


def _link_base_tables() -> None:
    with op.batch_alter_table("provider_profiles", recreate="always") as batch:
        batch.alter_column("extra_params_json", existing_type=sa.Text(), nullable=False)
        batch.alter_column("cost_policy_json", existing_type=sa.Text(), nullable=False)
        batch.create_foreign_key("fk_provider_profiles_active_revision_owner", "provider_profile_revisions", ["id", "active_revision_id"], ["provider_profile_id", "id"], ondelete="RESTRICT")
    with op.batch_alter_table("model_profiles", recreate="always") as batch:
        batch.create_foreign_key("fk_model_profiles_active_revision_owner", "model_profile_revisions", ["id", "active_revision_id"], ["model_profile_id", "id"], ondelete="RESTRICT")
    with op.batch_alter_table("capability_routes", recreate="always") as batch:
        batch.create_foreign_key("fk_capability_routes_active_revision_owner", "capability_route_revisions", ["id", "active_revision_id"], ["capability_route_id", "id"], ondelete="RESTRICT")
    with op.batch_alter_table("account_ai_recipes", recreate="always") as batch:
        batch.create_foreign_key("fk_account_ai_recipes_dependency_snapshot", "ai_dependency_snapshots", ["dependency_snapshot_id"], ["id"], ondelete="RESTRICT")
    with op.batch_alter_table("composition_template_profiles", recreate="always") as batch:
        batch.create_foreign_key("fk_composition_templates_dependency_snapshot", "ai_dependency_snapshots", ["dependency_snapshot_id"], ["id"], ondelete="RESTRICT")
    for name, table in (("uq_runtime_tasks_account_id", "runtime_tasks"), ("uq_positioning_profiles_account_id", "positioning_profiles"), ("uq_knowledge_sources_account_id", "knowledge_sources"), ("uq_knowledge_snapshots_account_id", "knowledge_snapshots"), ("uq_account_ai_recipes_account_id", "account_ai_recipes")):
        op.create_index(name, table, ["account_id", "id"], unique=True)


def _create_validation_and_asset_tables() -> None:
    op.create_table(
        "ai_provider_validation_runs",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("provider_profile_id", sa.String(), nullable=False), sa.Column("provider_revision", sa.Integer(), nullable=False), sa.Column("model_profile_id", sa.String()), sa.Column("model_revision", sa.Integer()), sa.Column("capability_key", sa.String()), sa.Column("stage", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("task_id", sa.String(), nullable=False), sa.Column("request_hash", sa.String()), sa.Column("response_hash", sa.String()), sa.Column("response_id_hash", sa.String()), sa.Column("usage_json", sa.Text()), sa.Column("duration_ms", sa.Integer()), sa.Column("error_code", sa.String()), sa.Column("error_log_id", sa.String()), sa.Column("verified_at", sa.Text()), sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["provider_profile_id"], ["provider_profiles.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["model_profile_id"], ["model_profiles.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["task_id"], ["runtime_tasks.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("stage IN ('network','authentication','model_discovery','real_small_call')", name="ck_ai_provider_validation_stage"), sa.CheckConstraint("status IN ('queued','running','verified','partial','failed','cancelled')", name="ck_ai_provider_validation_status"),
    )
    op.create_index("ix_ai_provider_validation_revision", "ai_provider_validation_runs", ["provider_profile_id", "provider_revision", "model_profile_id", "model_revision"])
    op.create_table(
        "account_assets",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), nullable=False), sa.Column("kind", sa.String(), nullable=False), sa.Column("source_kind", sa.String(), nullable=False), sa.Column("controlled_file_ref", sa.String(), nullable=False), sa.Column("root_ref", sa.String(), nullable=False), sa.Column("display_name", sa.Text(), nullable=False), sa.Column("media_type", sa.String(), nullable=False), sa.Column("byte_size", sa.Integer(), nullable=False), sa.Column("content_hash", sa.String()), sa.Column("status", sa.String(), nullable=False), sa.Column("authorization_basis", sa.String(), nullable=False), sa.Column("error_code", sa.String()), sa.Column("error_log_id", sa.String()), sa.Column("revision", sa.Integer(), nullable=False), sa.Column("created_at", sa.Text(), nullable=False), sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"), sa.CheckConstraint("source_kind IN ('controlled_file')", name="ck_account_assets_source_kind"), sa.CheckConstraint("status IN ('pending','ready','metadata_only','failed','stale')", name="ck_account_assets_status"), sa.CheckConstraint("byte_size >= 0 AND revision >= 1", name="ck_account_assets_limits"), sa.UniqueConstraint("account_id", "id", name="uq_account_assets_account_id"), sa.UniqueConstraint("account_id", "controlled_file_ref", "revision", name="uq_account_assets_file_revision"),
    )
    op.create_index("ix_account_assets_account_updated", "account_assets", ["account_id", "updated_at"])
    op.create_table("knowledge_source_assets", sa.Column("account_id", sa.String(), primary_key=True), sa.Column("knowledge_source_id", sa.String(), primary_key=True), sa.Column("account_asset_id", sa.String(), nullable=False), sa.Column("created_at", sa.Text(), nullable=False), sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["account_id", "knowledge_source_id"], ["knowledge_sources.account_id", "knowledge_sources.id"], ondelete="RESTRICT", name="fk_knowledge_source_assets_source_account"), sa.ForeignKeyConstraint(["account_id", "account_asset_id"], ["account_assets.account_id", "account_assets.id"], ondelete="RESTRICT", name="fk_knowledge_source_assets_asset_account"))
    op.create_table("knowledge_index_chunks", sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), nullable=False), sa.Column("knowledge_source_id", sa.String(), nullable=False), sa.Column("source_revision", sa.Integer(), nullable=False), sa.Column("ordinal", sa.Integer(), nullable=False), sa.Column("content_ref", sa.Text(), nullable=False), sa.Column("content_hash", sa.String(), nullable=False), sa.Column("token_count", sa.Integer(), nullable=False), sa.Column("extractor_version", sa.Integer(), nullable=False), sa.Column("created_at", sa.Text(), nullable=False), sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["account_id", "knowledge_source_id"], ["knowledge_sources.account_id", "knowledge_sources.id"], ondelete="RESTRICT", name="fk_knowledge_chunks_source_account"), sa.CheckConstraint("source_revision >= 1 AND ordinal >= 0 AND token_count >= 0", name="ck_knowledge_index_chunks_limits"), sa.UniqueConstraint("account_id", "id", name="uq_knowledge_chunks_account_id"), sa.UniqueConstraint("knowledge_source_id", "source_revision", "ordinal", name="uq_knowledge_chunks_source_revision_ordinal"))
    op.create_index("ix_knowledge_chunks_account_source", "knowledge_index_chunks", ["account_id", "knowledge_source_id"])


def _create_execution_tables() -> None:
    op.create_table("ai_execution_snapshots", sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), nullable=False), sa.Column("capability_key", sa.String(), nullable=False), sa.Column("account_revision", sa.Integer(), nullable=False), sa.Column("ai_config_revision", sa.Integer(), nullable=False), sa.Column("positioning_profile_id", sa.String()), sa.Column("positioning_version", sa.Integer()), sa.Column("positioning_content_hash", sa.String()), sa.Column("knowledge_snapshot_id", sa.String(), nullable=False), sa.Column("knowledge_snapshot_version", sa.Integer(), nullable=False), sa.Column("knowledge_content_hash", sa.String(), nullable=False), sa.Column("account_recipe_id", sa.String(), nullable=False), sa.Column("recipe_version", sa.Integer(), nullable=False), sa.Column("recipe_revision", sa.Integer(), nullable=False), sa.Column("recipe_content_hash", sa.String(), nullable=False), sa.Column("capability_route_id", sa.String(), nullable=False), sa.Column("route_revision_id", sa.String(), nullable=False), sa.Column("route_content_hash", sa.String(), nullable=False), sa.Column("prompt_profile_id", sa.String(), nullable=False), sa.Column("prompt_version", sa.Integer(), nullable=False), sa.Column("prompt_revision", sa.Integer(), nullable=False), sa.Column("prompt_content_hash", sa.String(), nullable=False), sa.Column("rendered_prompt_hash", sa.String(), nullable=False), sa.Column("dependency_snapshot_id", sa.String(), nullable=False), sa.Column("input_schema_hash", sa.String(), nullable=False), sa.Column("output_schema_hash", sa.String(), nullable=False), sa.Column("policy_json", sa.Text(), nullable=False), sa.Column("snapshot_hash", sa.String(), nullable=False), sa.Column("context_manifest_hash", sa.String(), nullable=False), sa.Column("created_at", sa.Text(), nullable=False), sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["account_id", "positioning_profile_id"], ["positioning_profiles.account_id", "positioning_profiles.id"], ondelete="RESTRICT", name="fk_ai_execution_snapshots_positioning_account"), sa.ForeignKeyConstraint(["account_id", "knowledge_snapshot_id"], ["knowledge_snapshots.account_id", "knowledge_snapshots.id"], ondelete="RESTRICT", name="fk_ai_execution_snapshots_knowledge_account"), sa.ForeignKeyConstraint(["account_id", "account_recipe_id"], ["account_ai_recipes.account_id", "account_ai_recipes.id"], ondelete="RESTRICT", name="fk_ai_execution_snapshots_recipe_account"), sa.ForeignKeyConstraint(["capability_route_id"], ["capability_routes.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["route_revision_id"], ["capability_route_revisions.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["prompt_profile_id"], ["prompt_profiles.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["dependency_snapshot_id"], ["ai_dependency_snapshots.id"], ondelete="RESTRICT"), sa.UniqueConstraint("account_id", "id", name="uq_ai_execution_snapshots_account_id"))
    op.create_table("ai_execution_candidates", sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), nullable=False), sa.Column("execution_snapshot_id", sa.String(), nullable=False), sa.Column("ordinal", sa.Integer(), nullable=False), sa.Column("provider_profile_id", sa.String(), nullable=False), sa.Column("provider_revision_id", sa.String(), nullable=False), sa.Column("adapter_type", sa.String(), nullable=False), sa.Column("credential_ref", sa.Text()), sa.Column("model_profile_id", sa.String(), nullable=False), sa.Column("model_revision_id", sa.String(), nullable=False), sa.Column("model_id", sa.String(), nullable=False), sa.Column("capability_contract_revision", sa.Integer(), nullable=False), sa.Column("validation_run_id", sa.String(), nullable=False), sa.Column("timeout_ms", sa.Integer(), nullable=False), sa.Column("max_retries", sa.Integer(), nullable=False), sa.Column("max_concurrency", sa.Integer(), nullable=False), sa.Column("max_cost_micros", sa.Integer(), nullable=False), sa.Column("retry_policy_json", sa.Text(), nullable=False), sa.Column("extra_params_json", sa.Text(), nullable=False), sa.Column("snapshot_hash", sa.String(), nullable=False), sa.ForeignKeyConstraint(["account_id", "execution_snapshot_id"], ["ai_execution_snapshots.account_id", "ai_execution_snapshots.id"], ondelete="RESTRICT", name="fk_ai_execution_candidates_snapshot_account"), sa.ForeignKeyConstraint(["provider_profile_id"], ["provider_profiles.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["provider_revision_id"], ["provider_profile_revisions.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["model_profile_id"], ["model_profiles.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["model_revision_id"], ["model_profile_revisions.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["validation_run_id"], ["ai_provider_validation_runs.id"], ondelete="RESTRICT"), sa.CheckConstraint("ordinal >= 0", name="ck_ai_execution_candidates_ordinal"), sa.UniqueConstraint("account_id", "id", name="uq_ai_execution_candidates_account_id"), sa.UniqueConstraint("execution_snapshot_id", "ordinal", name="uq_ai_execution_candidates_snapshot_ordinal"))
    op.create_table("ai_executions", sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), nullable=False), sa.Column("capability_key", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("completion_kind", sa.String()), sa.Column("failure_kind", sa.String()), sa.Column("snapshot_id", sa.String(), nullable=False), sa.Column("runtime_task_id", sa.String(), nullable=False), sa.Column("active_job_id", sa.String()), sa.Column("retry_of_execution_id", sa.String()), sa.Column("input_ref", sa.Text(), nullable=False), sa.Column("input_hash", sa.String(), nullable=False), sa.Column("idempotency_key_hash", sa.String(), nullable=False), sa.Column("request_hash", sa.String(), nullable=False), sa.Column("budget_limit_micros", sa.Integer(), nullable=False), sa.Column("currency", sa.String(), nullable=False), sa.Column("usage_input_units", sa.Integer()), sa.Column("usage_output_units", sa.Integer()), sa.Column("usage_cached_units", sa.Integer()), sa.Column("cost_micros", sa.Integer()), sa.Column("cost_status", sa.String(), nullable=False), sa.Column("output_count", sa.Integer(), nullable=False), sa.Column("error_code", sa.String()), sa.Column("error_log_id", sa.String()), sa.Column("revision", sa.Integer(), nullable=False), sa.Column("created_at", sa.Text(), nullable=False), sa.Column("started_at", sa.Text()), sa.Column("completed_at", sa.Text()), sa.Column("updated_at", sa.Text(), nullable=False), sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["account_id", "runtime_task_id"], ["runtime_tasks.account_id", "runtime_tasks.id"], ondelete="RESTRICT", name="fk_ai_executions_runtime_task_account"), sa.ForeignKeyConstraint(["account_id", "snapshot_id"], ["ai_execution_snapshots.account_id", "ai_execution_snapshots.id"], ondelete="RESTRICT", name="fk_ai_executions_snapshot_account"), sa.ForeignKeyConstraint(["account_id", "active_job_id"], ["ai_execution_jobs.account_id", "ai_execution_jobs.id"], ondelete="RESTRICT", name="fk_ai_executions_active_job_account"), sa.ForeignKeyConstraint(["account_id", "retry_of_execution_id"], ["ai_executions.account_id", "ai_executions.id"], ondelete="RESTRICT", name="fk_ai_executions_retry_account"), sa.CheckConstraint("status IN ('queued','running','cancelling','failed','completed')", name="ck_ai_executions_status"), sa.CheckConstraint("completion_kind IS NULL OR completion_kind IN ('succeeded','cancelled')", name="ck_ai_executions_completion"), sa.CheckConstraint("failure_kind IS NULL OR failure_kind IN ('error','timed_out','restart_interrupted','result_unknown')", name="ck_ai_executions_failure"), sa.CheckConstraint("cost_status IN ('reported','estimated','unavailable')", name="ck_ai_executions_cost_status"), sa.CheckConstraint("budget_limit_micros >= 0 AND output_count >= 0 AND revision >= 1", name="ck_ai_executions_limits"), sa.UniqueConstraint("account_id", "id", name="uq_ai_executions_account_id"), sa.UniqueConstraint("snapshot_id", name="uq_ai_executions_snapshot"), sa.UniqueConstraint("account_id", "idempotency_key_hash", name="uq_ai_executions_account_idempotency"))
    op.create_index("ix_ai_executions_account_updated", "ai_executions", ["account_id", "updated_at"]); op.create_index("ix_ai_executions_account_status", "ai_executions", ["account_id", "status"])
    op.create_table("ai_execution_jobs", sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), nullable=False), sa.Column("execution_id", sa.String(), nullable=False), sa.Column("candidate_snapshot_id", sa.String(), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("fallback_index", sa.Integer(), nullable=False), sa.Column("retry_index", sa.Integer(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("completion_kind", sa.String()), sa.Column("failure_kind", sa.String()), sa.Column("provider_request_id_hash", sa.String()), sa.Column("request_hash", sa.String(), nullable=False), sa.Column("response_hash", sa.String()), sa.Column("duration_ms", sa.Integer()), sa.Column("timeout_at", sa.Text(), nullable=False), sa.Column("error_evidence_id", sa.String()), sa.Column("revision", sa.Integer(), nullable=False), sa.Column("created_at", sa.Text(), nullable=False), sa.Column("started_at", sa.Text()), sa.Column("completed_at", sa.Text()), sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["account_id", "execution_id"], ["ai_executions.account_id", "ai_executions.id"], ondelete="RESTRICT", name="fk_ai_execution_jobs_execution_account"), sa.ForeignKeyConstraint(["account_id", "candidate_snapshot_id"], ["ai_execution_candidates.account_id", "ai_execution_candidates.id"], ondelete="RESTRICT", name="fk_ai_execution_jobs_candidate_account"), sa.CheckConstraint("status IN ('queued','running','cancelling','failed','completed')", name="ck_ai_execution_jobs_status"), sa.CheckConstraint("completion_kind IS NULL OR completion_kind IN ('succeeded','cancelled')", name="ck_ai_execution_jobs_completion"), sa.CheckConstraint("failure_kind IS NULL OR failure_kind IN ('error','timed_out','restart_interrupted','result_unknown')", name="ck_ai_execution_jobs_failure"), sa.CheckConstraint("attempt >= 1 AND fallback_index >= 0 AND retry_index >= 0 AND revision >= 1", name="ck_ai_execution_jobs_attempt"), sa.UniqueConstraint("account_id", "id", name="uq_ai_execution_jobs_account_id"), sa.UniqueConstraint("execution_id", "attempt", name="uq_ai_execution_jobs_execution_attempt"))
    op.create_index("ix_ai_execution_jobs_account_execution", "ai_execution_jobs", ["account_id", "execution_id"])
    _create_execution_evidence_tables()


def _create_execution_evidence_tables() -> None:
    common_execution_fk = lambda name: sa.ForeignKeyConstraint(["account_id", "execution_id"], ["ai_executions.account_id", "ai_executions.id"], ondelete="RESTRICT", name=name)
    common_job_fk = lambda name: sa.ForeignKeyConstraint(["account_id", "job_id"], ["ai_execution_jobs.account_id", "ai_execution_jobs.id"], ondelete="RESTRICT", name=name)
    op.create_table("ai_usage_records", sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), nullable=False), sa.Column("execution_id", sa.String(), nullable=False), sa.Column("job_id", sa.String(), nullable=False), sa.Column("provider_profile_id", sa.String(), nullable=False), sa.Column("model_profile_id", sa.String(), nullable=False), sa.Column("input_units", sa.Integer()), sa.Column("output_units", sa.Integer()), sa.Column("cached_units", sa.Integer()), sa.Column("total_units", sa.Integer()), sa.Column("cost_micros", sa.Integer()), sa.Column("currency", sa.String(), nullable=False), sa.Column("cost_source", sa.String(), nullable=False), sa.Column("pricing_revision", sa.Integer()), sa.Column("raw_usage_hash", sa.String()), sa.Column("created_at", sa.Text(), nullable=False), common_execution_fk("fk_ai_usage_execution_account"), common_job_fk("fk_ai_usage_job_account"), sa.CheckConstraint("cost_source IN ('reported','estimated','unavailable')", name="ck_ai_usage_cost_source"), sa.UniqueConstraint("account_id", "id", name="uq_ai_usage_account_id"))
    op.create_table("ai_execution_outputs", sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), nullable=False), sa.Column("execution_id", sa.String(), nullable=False), sa.Column("job_id", sa.String(), nullable=False), sa.Column("kind", sa.String(), nullable=False), sa.Column("mime_type", sa.String(), nullable=False), sa.Column("content_ref", sa.Text(), nullable=False), sa.Column("content_hash", sa.String(), nullable=False), sa.Column("byte_size", sa.Integer(), nullable=False), sa.Column("schema_status", sa.String(), nullable=False), sa.Column("safe_summary_json", sa.Text(), nullable=False), sa.Column("quarantined", sa.Boolean(), nullable=False), sa.Column("created_at", sa.Text(), nullable=False), common_execution_fk("fk_ai_outputs_execution_account"), common_job_fk("fk_ai_outputs_job_account"), sa.CheckConstraint("byte_size >= 0", name="ck_ai_outputs_byte_size"), sa.UniqueConstraint("account_id", "id", name="uq_ai_outputs_account_id"))
    op.create_index("ix_ai_outputs_account_execution", "ai_execution_outputs", ["account_id", "execution_id"])
    op.create_table("ai_error_evidence", sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), nullable=False), sa.Column("execution_id", sa.String(), nullable=False), sa.Column("job_id", sa.String()), sa.Column("stage", sa.String(), nullable=False), sa.Column("error_code", sa.String(), nullable=False), sa.Column("provider_status_code", sa.Integer()), sa.Column("retryable", sa.Boolean(), nullable=False), sa.Column("safe_summary", sa.Text(), nullable=False), sa.Column("provider_request_id_hash", sa.String()), sa.Column("response_body_hash", sa.String()), sa.Column("log_id", sa.String(), nullable=False), sa.Column("created_at", sa.Text(), nullable=False), common_execution_fk("fk_ai_errors_execution_account"), common_job_fk("fk_ai_errors_job_account"), sa.UniqueConstraint("account_id", "id", name="uq_ai_errors_account_id"))


def _drop_execution_tables() -> None:
    for table in ("ai_error_evidence", "ai_execution_outputs", "ai_usage_records", "ai_execution_jobs", "ai_executions", "ai_execution_candidates", "ai_execution_snapshots"):
        op.drop_table(table)


def _drop_asset_and_validation_tables() -> None:
    for table in ("knowledge_index_chunks", "knowledge_source_assets", "account_assets", "ai_provider_validation_runs"):
        op.drop_table(table)


def _unlink_base_tables() -> None:
    for name, table in (("uq_account_ai_recipes_account_id", "account_ai_recipes"), ("uq_knowledge_snapshots_account_id", "knowledge_snapshots"), ("uq_knowledge_sources_account_id", "knowledge_sources"), ("uq_positioning_profiles_account_id", "positioning_profiles"), ("uq_runtime_tasks_account_id", "runtime_tasks")):
        op.drop_index(name, table_name=table)
    with op.batch_alter_table("composition_template_profiles", recreate="always") as batch:
        batch.drop_constraint("fk_composition_templates_dependency_snapshot", type_="foreignkey"); batch.drop_column("dependency_snapshot_id")
    with op.batch_alter_table("account_ai_recipes", recreate="always") as batch:
        batch.drop_constraint("fk_account_ai_recipes_dependency_snapshot", type_="foreignkey"); batch.drop_column("dependency_snapshot_id")
    with op.batch_alter_table("capability_routes", recreate="always") as batch:
        batch.drop_constraint("fk_capability_routes_active_revision_owner", type_="foreignkey"); batch.drop_column("active_revision_id")
    with op.batch_alter_table("model_profiles", recreate="always") as batch:
        batch.drop_constraint("fk_model_profiles_active_revision_owner", type_="foreignkey"); batch.drop_column("active_revision_id")
    with op.batch_alter_table("provider_profiles", recreate="always") as batch:
        batch.drop_constraint("fk_provider_profiles_active_revision_owner", type_="foreignkey"); batch.drop_column("active_revision_id"); batch.drop_column("cost_policy_json"); batch.drop_column("extra_params_json")


def _drop_revision_and_dependency_tables() -> None:
    op.drop_table("capability_route_revisions"); op.drop_table("model_profile_revisions"); op.drop_table("provider_profile_revisions"); op.drop_table("ai_dependency_snapshots")


def _refuse_data_bearing_downgrade(connection: Connection) -> None:
    tables = ("ai_executions", "account_assets", "ai_provider_validation_runs", "ai_dependency_snapshots", "capability_route_revisions", "model_profile_revisions", "provider_profile_revisions")
    blockers = [table for table in tables if connection.execute(sa.text(f'SELECT 1 FROM "{table}" LIMIT 1')).first()]
    if blockers:
        log.error("P0-H 迁移拒绝有数据降级", extra={"downgrade_blockers": ",".join(blockers)})
        raise RuntimeError("P0H_DOWNGRADE_REQUIRES_BACKUP: 已存在真实 AI 配置、资产或执行证据，禁止自动降级；请恢复迁移前备份")


def _validate_required_tables(connection: Connection) -> None:
    required = {"accounts", "runtime_tasks", "provider_profiles", "model_profiles", "capability_routes", "prompt_profiles", "account_ai_recipes", "composition_template_profiles", "positioning_profiles", "knowledge_sources", "knowledge_snapshots"}
    present = {row[0] for row in connection.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'"))}
    missing = sorted(required - present)
    if missing:
        _fail(f"缺少 P0-H 依赖表：{', '.join(missing)}")


def _validate_upgrade(connection: Connection) -> None:
    missing_provider = connection.execute(sa.text("SELECT 1 FROM provider_profiles WHERE extra_params_json IS NULL OR cost_policy_json IS NULL OR active_revision_id IS NULL LIMIT 1")).first()
    missing_model = connection.execute(sa.text("SELECT 1 FROM model_profiles WHERE active_revision_id IS NULL LIMIT 1")).first()
    violations = connection.execute(sa.text("PRAGMA foreign_key_check")).all()
    if missing_provider or missing_model or violations:
        _fail("配置 revision 回填或外键完整性校验失败")


def _safe_json(raw: Any) -> Any:
    try:
        return json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"unparseable": True}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _stable_id(kind: str, resource_id: Any, resource_revision: Any) -> str:
    return f"p0h-{kind}-{_hash(f'{resource_id}:{resource_revision}')[:24]}"


def _fail(message: str) -> NoReturn:
    log.error("P0-H 迁移校验失败", extra={"validation_issue": message})
    raise RuntimeError(f"P0H_MIGRATION_VALIDATION_FAILED: {message}")
