from __future__ import annotations

import domain.models as models
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from domain.models import (
    Account,
    AccountConfigCopyRun,
    AccountConnection,
    AccountKnowledgeBase,
    AccountPublishDefaults,
    Base,
    BrandKit,
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
    KnowledgeSnapshot,
    KnowledgeSource,
    PositioningProfile,
    RuntimeMutationIdempotency,
)


_NEW_TABLE_COLUMNS = {
    "account_connections": (
        "id",
        "account_id",
        "credential_ref",
        "session_ref",
        "auth_status",
        "health_status",
        "active_execution_binding_id",
        "last_checked_at",
        "error_code",
        "error_log_id",
        "revision",
        "created_at",
        "updated_at",
    ),
    "positioning_profiles": (
        "id",
        "account_id",
        "version",
        "status",
        "audience_json",
        "content_pillars_json",
        "voice_style_json",
        "prohibited_terms_json",
        "publishing_constraints_json",
        "summary",
        "revision",
        "created_at",
        "activated_at",
    ),
    "account_knowledge_bases": (
        "id",
        "account_id",
        "status",
        "rules_json",
        "rules_version",
        "index_revision",
        "last_indexed_at",
        "error_code",
        "error_log_id",
        "revision",
        "created_at",
        "updated_at",
    ),
    "knowledge_sources": (
        "id",
        "account_id",
        "knowledge_base_id",
        "kind",
        "name",
        "source_ref",
        "status",
        "content_hash",
        "metadata_json",
        "error_code",
        "error_log_id",
        "revision",
        "created_at",
        "updated_at",
        "deleted_at",
        "source_mode",
        "source_url",
    ),
    "knowledge_snapshots": (
        "id",
        "account_id",
        "knowledge_base_id",
        "snapshot_version",
        "positioning_profile_id",
        "rules_version",
        "index_revision",
        "source_manifest_json",
        "content_hash",
        "created_at",
        "label",
    ),
    "brand_kits": (
        "id",
        "account_id",
        "version",
        "status",
        "visual_style_json",
        "colors_json",
        "fonts_json",
        "logo_asset_refs_json",
        "voice_rules_json",
        "revision",
        "created_at",
        "activated_at",
    ),
    "account_publish_defaults": (
        "account_id",
        "timezone",
        "privacy_level",
        "allow_comments",
        "allow_duet",
        "allow_stitch",
        "caption_rules_json",
        "revision",
        "created_at",
        "updated_at",
    ),
    "account_config_copy_runs": (
        "id",
        "source_account_id",
        "target_account_id",
        "requested_sections_json",
        "copied_sections_json",
        "skipped_sections_json",
        "status",
        "operation_id",
        "error_code",
        "error_log_id",
        "created_at",
        "completed_at",
    ),
    "runtime_mutation_idempotency": (
        "id",
        "scope",
        "account_id",
        "operation_name",
        "idempotency_key_hash",
        "request_hash",
        "response_json",
        "resource_type",
        "resource_id",
        "created_at",
        "expires_at",
    ),
}


def test_p0_c_models_register_every_new_column_once() -> None:
    for table_name, columns in _NEW_TABLE_COLUMNS.items():
        assert tuple(Base.metadata.tables[table_name].columns.keys()) == columns

    assert KnowledgeSnapshot.__table__.c.label.nullable is True
    assert KnowledgeSource.__table__.c.source_mode.nullable is False
    assert KnowledgeSource.__table__.c.source_url.nullable is True
    assert BrandKit.__table__.c.voice_rules_json.nullable is False


def test_account_and_execution_models_expose_p0_scope_columns() -> None:
    assert Account.__table__.c.status.default.arg == "draft"
    assert Account.__table__.c.platform.default.arg == "tiktok"
    assert {
        "platform_account_id",
        "wizard_completed_at",
        "status_reason_code",
        "last_used_at",
        "last_health_checked_at",
        "archived_at",
        "revision",
    } <= set(Account.__table__.columns.keys())

    assert DeviceWorkspace.__table__.c.account_id.nullable is True
    assert BrowserInstance.__table__.c.account_id.nullable is True
    assert ExecutionBinding.__table__.c.account_id.nullable is False
    assert ExecutionBinding.__table__.c.browser_instance_id.nullable is True
    assert DeviceWorkspace.__module__ == "domain.models.device_workspace"
    assert BrowserInstance.__module__ == "domain.models.device_workspace"
    assert ExecutionBinding.__module__ == "domain.models.device_workspace"


def test_p0_c_named_checks_and_indexes_match_the_schema_contract() -> None:
    expected_checks = {
        "accounts": {
            "ck_accounts_stable_id",
            "ck_accounts_status",
            "ck_accounts_revision",
        },
        "account_connections": {
            "ck_account_connections_auth_status",
            "ck_account_connections_health_status",
            "ck_account_connections_revision",
        },
        "positioning_profiles": {
            "ck_positioning_profiles_status",
            "ck_positioning_profiles_version",
        },
        "account_knowledge_bases": {
            "ck_knowledge_bases_status",
            "ck_knowledge_bases_revision",
        },
        "knowledge_sources": {
            "ck_knowledge_sources_kind",
            "ck_knowledge_sources_status",
            "ck_knowledge_sources_revision",
            "ck_knowledge_sources_source_mode",
            "ck_knowledge_sources_source_url",
        },
        "brand_kits": {"ck_brand_kits_status", "ck_brand_kits_version"},
        "account_config_copy_runs": {"ck_copy_runs_status", "ck_copy_runs_accounts"},
        "runtime_mutation_idempotency": {
            "ck_runtime_mutation_scope",
            "ck_runtime_mutation_account_scope",
            "ck_runtime_mutation_operation",
            "ck_runtime_mutation_idempotency_hash",
            "ck_runtime_mutation_request_hash",
            "ck_runtime_mutation_response",
            "ck_runtime_mutation_resource",
            "ck_runtime_mutation_retention",
        },
    }
    expected_indexes = {
        "accounts": {"ix_accounts_status_last_used"},
        "device_workspaces": {"ix_device_workspaces_account_updated"},
        "browser_instances": {"ix_browser_instances_account_updated"},
        "execution_bindings": {"ix_execution_bindings_account_updated"},
        "account_connections": {"ix_account_connections_account_updated"},
        "positioning_profiles": {
            "ix_positioning_profiles_account_created",
            "uq_positioning_profiles_one_active",
        },
        "account_knowledge_bases": {"ix_knowledge_bases_account_updated"},
        "knowledge_sources": {
            "ix_knowledge_sources_account_updated",
            "ix_knowledge_sources_account_mode_updated",
        },
        "knowledge_snapshots": {"ix_knowledge_snapshots_account_created"},
        "brand_kits": {
            "ix_brand_kits_account_created",
            "uq_brand_kits_one_active",
        },
        "account_publish_defaults": {"ix_publish_defaults_account_updated"},
        "account_config_copy_runs": {
            "ix_copy_runs_source_created",
            "ix_copy_runs_target_created",
        },
        "runtime_mutation_idempotency": {
            "ix_runtime_mutation_expires_at",
            "uq_runtime_mutation_system_idempotency",
            "uq_runtime_mutation_account_idempotency",
        },
    }

    for table_name, names in expected_checks.items():
        table = Base.metadata.tables[table_name]
        actual = {
            constraint.name
            for constraint in table.constraints
            if isinstance(constraint, CheckConstraint)
        }
        assert actual == names

    expected_uniques = {
        "account_connections": {"uq_account_connections_account"},
        "positioning_profiles": {"uq_positioning_profiles_account_version"},
        "account_knowledge_bases": {"uq_account_knowledge_bases_account"},
        "knowledge_snapshots": {"uq_knowledge_snapshots_account_version"},
        "brand_kits": {"uq_brand_kits_account_version"},
        "account_config_copy_runs": {"uq_account_config_copy_runs_operation"},
    }
    for table_name, names in expected_uniques.items():
        actual = {
            constraint.name
            for constraint in Base.metadata.tables[table_name].constraints
            if isinstance(constraint, UniqueConstraint)
        }
        assert actual == names

    for table_name, names in expected_indexes.items():
        actual = {index.name for index in Base.metadata.tables[table_name].indexes}
        assert actual == names

    index_contracts = {
        "ix_accounts_status_last_used": ("accounts", ("status", "last_used_at"), False, None),
        "ix_device_workspaces_account_updated": ("device_workspaces", ("account_id", "updated_at"), False, None),
        "ix_browser_instances_account_updated": ("browser_instances", ("account_id", "updated_at"), False, None),
        "ix_execution_bindings_account_updated": ("execution_bindings", ("account_id", "updated_at"), False, None),
        "ix_account_connections_account_updated": ("account_connections", ("account_id", "updated_at"), False, None),
        "ix_positioning_profiles_account_created": ("positioning_profiles", ("account_id", "created_at"), False, None),
        "uq_positioning_profiles_one_active": ("positioning_profiles", ("account_id",), True, "status = 'active'"),
        "ix_knowledge_bases_account_updated": ("account_knowledge_bases", ("account_id", "updated_at"), False, None),
        "ix_knowledge_sources_account_updated": ("knowledge_sources", ("account_id", "updated_at"), False, None),
        "ix_knowledge_sources_account_mode_updated": ("knowledge_sources", ("account_id", "source_mode", "updated_at"), False, None),
        "ix_knowledge_snapshots_account_created": ("knowledge_snapshots", ("account_id", "created_at"), False, None),
        "ix_brand_kits_account_created": ("brand_kits", ("account_id", "created_at"), False, None),
        "uq_brand_kits_one_active": ("brand_kits", ("account_id",), True, "status = 'active'"),
        "ix_publish_defaults_account_updated": ("account_publish_defaults", ("account_id", "updated_at"), False, None),
        "ix_copy_runs_source_created": ("account_config_copy_runs", ("source_account_id", "created_at"), False, None),
        "ix_copy_runs_target_created": ("account_config_copy_runs", ("target_account_id", "created_at"), False, None),
        "ix_runtime_mutation_expires_at": ("runtime_mutation_idempotency", ("expires_at",), False, None),
        "uq_runtime_mutation_system_idempotency": ("runtime_mutation_idempotency", ("operation_name", "idempotency_key_hash"), True, "scope = 'system' AND account_id IS NULL"),
        "uq_runtime_mutation_account_idempotency": ("runtime_mutation_idempotency", ("account_id", "operation_name", "idempotency_key_hash"), True, "scope = 'account' AND account_id IS NOT NULL"),
    }
    for index_name, (table_name, columns, unique, where) in index_contracts.items():
        index = next(
            item
            for item in Base.metadata.tables[table_name].indexes
            if item.name == index_name
        )
        sqlite_where = index.dialect_options["sqlite"]["where"]
        assert tuple(index.columns.keys()) == columns
        assert index.unique is unique
        assert (str(sqlite_where) if sqlite_where is not None else None) == where


def test_p0_c_foreign_keys_preserve_scope_and_delete_policy() -> None:
    expected = {
        ("account_connections", "account_id"): ("accounts.id", "RESTRICT", None),
        ("account_connections", "active_execution_binding_id"): (
            "execution_bindings.id",
            "SET NULL",
            None,
        ),
        ("positioning_profiles", "account_id"): (
            "accounts.id",
            "RESTRICT",
            None,
        ),
        ("account_knowledge_bases", "account_id"): (
            "accounts.id",
            "RESTRICT",
            None,
        ),
        ("knowledge_sources", "account_id"): (
            "accounts.id",
            "RESTRICT",
            None,
        ),
        ("knowledge_sources", "knowledge_base_id"): (
            "account_knowledge_bases.id",
            "RESTRICT",
            None,
        ),
        ("knowledge_snapshots", "account_id"): (
            "accounts.id",
            "RESTRICT",
            None,
        ),
        ("knowledge_snapshots", "knowledge_base_id"): (
            "account_knowledge_bases.id",
            "RESTRICT",
            None,
        ),
        ("knowledge_snapshots", "positioning_profile_id"): (
            "positioning_profiles.id",
            "RESTRICT",
            None,
        ),
        ("brand_kits", "account_id"): ("accounts.id", "RESTRICT", None),
        ("account_publish_defaults", "account_id"): (
            "accounts.id",
            "RESTRICT",
            None,
        ),
        ("account_config_copy_runs", "source_account_id"): (
            "accounts.id",
            "RESTRICT",
            None,
        ),
        ("account_config_copy_runs", "target_account_id"): (
            "accounts.id",
            "RESTRICT",
            None,
        ),
        ("device_workspaces", "account_id"): (
            "accounts.id",
            "RESTRICT",
            "fk_device_workspaces_account_id",
        ),
        ("browser_instances", "account_id"): (
            "accounts.id",
            "RESTRICT",
            "fk_browser_instances_account_id",
        ),
        ("browser_instances", "workspace_id"): (
            "device_workspaces.id",
            "CASCADE",
            None,
        ),
        ("execution_bindings", "account_id"): (
            "accounts.id",
            "CASCADE",
            None,
        ),
        ("execution_bindings", "device_workspace_id"): (
            "device_workspaces.id",
            "CASCADE",
            None,
        ),
        ("execution_bindings", "browser_instance_id"): (
            "browser_instances.id",
            "SET NULL",
            "fk_execution_bindings_browser_id",
        ),
        ("runtime_mutation_idempotency", "account_id"): (
            "accounts.id",
            "RESTRICT",
            "fk_runtime_mutation_account_id",
        ),
    }

    for (table_name, column_name), contract in expected.items():
        foreign_key = next(iter(Base.metadata.tables[table_name].c[column_name].foreign_keys))
        assert (
            foreign_key.target_fullname,
            foreign_key.ondelete,
            foreign_key.constraint.name,
        ) == contract
    scoped_tables = {
        "account_connections",
        "positioning_profiles",
        "account_knowledge_bases",
        "knowledge_sources",
        "knowledge_snapshots",
        "brand_kits",
        "account_publish_defaults",
        "account_config_copy_runs",
        "device_workspaces",
        "browser_instances",
        "execution_bindings",
        "runtime_mutation_idempotency",
    }
    actual_keys = {
        (table_name, foreign_key.parent.name)
        for table_name in scoped_tables
        for foreign_key in Base.metadata.tables[table_name].foreign_keys
    }
    assert actual_keys == set(expected)

    named_mutation_foreign_keys = {
        constraint.name
        for constraint in RuntimeMutationIdempotency.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert named_mutation_foreign_keys == {"fk_runtime_mutation_account_id"}


def test_p0_c_models_are_exported_from_the_canonical_package() -> None:
    expected = {
        "AccountConfigCopyRun": AccountConfigCopyRun,
        "AccountConnection": AccountConnection,
        "AccountKnowledgeBase": AccountKnowledgeBase,
        "AccountPublishDefaults": AccountPublishDefaults,
        "BrandKit": BrandKit,
        "KnowledgeSnapshot": KnowledgeSnapshot,
        "KnowledgeSource": KnowledgeSource,
        "PositioningProfile": PositioningProfile,
        "RuntimeMutationIdempotency": RuntimeMutationIdempotency,
    }

    assert expected.keys() <= set(models.__all__)
    for name, model in expected.items():
        assert getattr(models, name) is model
