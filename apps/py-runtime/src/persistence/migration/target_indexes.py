from __future__ import annotations

IndexContract = tuple[str, tuple[str, ...], bool, bool]

P0_REQUIRED_INDEXES: dict[str, IndexContract] = {
    "uq_runtime_tasks_account_id": (
        "runtime_tasks",
        ("account_id", "id"),
        True,
        False,
    ),
    "uq_positioning_profiles_account_id": (
        "positioning_profiles",
        ("account_id", "id"),
        True,
        False,
    ),
    "uq_knowledge_sources_account_id": (
        "knowledge_sources",
        ("account_id", "id"),
        True,
        False,
    ),
    "uq_knowledge_snapshots_account_id": (
        "knowledge_snapshots",
        ("account_id", "id"),
        True,
        False,
    ),
    "uq_account_ai_recipes_account_id": (
        "account_ai_recipes",
        ("account_id", "id"),
        True,
        False,
    ),
    "uq_route_revisions_one_active": (
        "capability_route_revisions",
        ("capability_route_id",),
        True,
        True,
    ),
    "ix_ai_provider_validation_revision": (
        "ai_provider_validation_runs",
        (
            "provider_profile_id",
            "provider_revision",
            "model_profile_id",
            "model_revision",
        ),
        False,
        False,
    ),
    "ix_account_assets_account_updated": (
        "account_assets",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_knowledge_chunks_account_source": (
        "knowledge_index_chunks",
        ("account_id", "knowledge_source_id"),
        False,
        False,
    ),
    "ix_ai_executions_account_updated": (
        "ai_executions",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_ai_executions_account_status": (
        "ai_executions",
        ("account_id", "status"),
        False,
        False,
    ),
    "ix_ai_execution_jobs_account_execution": (
        "ai_execution_jobs",
        ("account_id", "execution_id"),
        False,
        False,
    ),
    "ix_ai_outputs_account_execution": (
        "ai_execution_outputs",
        ("account_id", "execution_id"),
        False,
        False,
    ),
    "uq_device_workspaces_root_ref": (
        "device_workspaces",
        ("root_ref",),
        True,
        True,
    ),
    "uq_execution_bindings_active_account": (
        "execution_bindings",
        ("account_id",),
        True,
        True,
    ),
    "ix_account_login_sessions_account_updated": (
        "account_login_sessions",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "uq_account_login_sessions_active": (
        "account_login_sessions",
        ("account_id",),
        True,
        True,
    ),
    "ix_accounts_status_last_used": (
        "accounts",
        ("status", "last_used_at"),
        False,
        False,
    ),
    "ix_device_workspaces_account_updated": (
        "device_workspaces",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_browser_instances_account_updated": (
        "browser_instances",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_execution_bindings_account_updated": (
        "execution_bindings",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_account_connections_account_updated": (
        "account_connections",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_positioning_profiles_account_created": (
        "positioning_profiles",
        ("account_id", "created_at"),
        False,
        False,
    ),
    "ix_knowledge_bases_account_updated": (
        "account_knowledge_bases",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_knowledge_sources_account_updated": (
        "knowledge_sources",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_knowledge_sources_account_mode_updated": (
        "knowledge_sources",
        ("account_id", "source_mode", "updated_at"),
        False,
        False,
    ),
    "ix_knowledge_snapshots_account_created": (
        "knowledge_snapshots",
        ("account_id", "created_at"),
        False,
        False,
    ),
    "ix_brand_kits_account_created": (
        "brand_kits",
        ("account_id", "created_at"),
        False,
        False,
    ),
    "ix_publish_defaults_account_updated": (
        "account_publish_defaults",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_copy_runs_source_created": (
        "account_config_copy_runs",
        ("source_account_id", "created_at"),
        False,
        False,
    ),
    "ix_copy_runs_target_created": (
        "account_config_copy_runs",
        ("target_account_id", "created_at"),
        False,
        False,
    ),
    "ix_account_ai_recipes_account_created": (
        "account_ai_recipes",
        ("account_id", "created_at"),
        False,
        False,
    ),
    "ix_runtime_tasks_account_updated": (
        "runtime_tasks",
        ("account_id", "updated_at"),
        False,
        False,
    ),
    "ix_runtime_tasks_status_updated": (
        "runtime_tasks",
        ("status", "updated_at"),
        False,
        False,
    ),
    "uq_runtime_tasks_system_idempotency": (
        "runtime_tasks",
        ("task_type", "idempotency_key_hash"),
        True,
        True,
    ),
    "uq_runtime_tasks_account_idempotency": (
        "runtime_tasks",
        ("account_id", "task_type", "idempotency_key_hash"),
        True,
        True,
    ),
    "ix_runtime_events_account_occurred": (
        "runtime_events",
        ("account_id", "occurred_at"),
        False,
        False,
    ),
    "ix_runtime_events_unpublished": (
        "runtime_events",
        ("published_at", "occurred_at"),
        False,
        False,
    ),
    "ix_runtime_mutation_expires_at": (
        "runtime_mutation_idempotency",
        ("expires_at",),
        False,
        False,
    ),
    "uq_runtime_mutation_system_idempotency": (
        "runtime_mutation_idempotency",
        ("operation_name", "idempotency_key_hash"),
        True,
        True,
    ),
    "uq_runtime_mutation_account_idempotency": (
        "runtime_mutation_idempotency",
        ("account_id", "operation_name", "idempotency_key_hash"),
        True,
        True,
    ),
    "uq_positioning_profiles_one_active": (
        "positioning_profiles",
        ("account_id",),
        True,
        True,
    ),
    "uq_brand_kits_one_active": (
        "brand_kits",
        ("account_id",),
        True,
        True,
    ),
    "uq_prompt_profiles_one_active": (
        "prompt_profiles",
        ("profile_key",),
        True,
        True,
    ),
    "uq_composition_templates_one_active": (
        "composition_template_profiles",
        ("template_key",),
        True,
        True,
    ),
    "uq_account_ai_recipes_one_active": (
        "account_ai_recipes",
        ("account_id",),
        True,
        True,
    ),
}

P0_REQUIRED_INDEX_PREDICATES = {
    "uq_route_revisions_one_active": "where status = 'active'",
    "uq_device_workspaces_root_ref": "where root_ref is not null",
    "uq_execution_bindings_active_account": "where status = 'active'",
    "uq_account_login_sessions_active": (
        "where state in ('preparing','waiting_user','probing')"
    ),
    "uq_runtime_tasks_system_idempotency": (
        "where scope = 'system' and account_id is null"
    ),
    "uq_runtime_tasks_account_idempotency": (
        "where scope = 'account' and account_id is not null"
    ),
    "uq_runtime_mutation_system_idempotency": (
        "where scope = 'system' and account_id is null"
    ),
    "uq_runtime_mutation_account_idempotency": (
        "where scope = 'account' and account_id is not null"
    ),
}
