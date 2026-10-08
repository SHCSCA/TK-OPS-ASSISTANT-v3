from __future__ import annotations

# 该映射冻结 0021 head 的 CHECK 语义，防止同名约束被弱化后继续启动。
P0_CHECK_CONTRACTS: dict[str, dict[str, str]] = {
    "account_login_sessions": {
        "ck_account_login_sessions_state": (
            "state IN ('preparing','waiting_user','probing','completed',"
            "'cancelled','failed','timed_out')"
        ),
        "ck_account_login_sessions_revision": "revision >= 1",
    },
    "accounts": {
        "ck_accounts_stable_id": (
            "id IS NOT NULL "
            "AND length(id) BETWEEN 1 AND 128 "
            "AND substr(id, 1, 1) GLOB '[A-Za-z0-9]' "
            "AND id NOT GLOB '*[^A-Za-z0-9._-]*'"
        ),
        "ck_accounts_status": (
            "status IN ('draft','unbound','ready','attention','archived')"
        ),
        "ck_accounts_revision": "revision >= 1",
    },
    "account_connections": {
        "ck_account_connections_auth_status": (
            "auth_status IN ('unknown','required','valid','expired','failed')"
        ),
        "ck_account_connections_health_status": (
            "health_status IN ('unknown','checking','ready','attention','failed')"
        ),
        "ck_account_connections_revision": "revision >= 1",
    },
    "positioning_profiles": {
        "ck_positioning_profiles_status": "status IN ('draft','active','archived')",
        "ck_positioning_profiles_version": "version >= 1 AND revision >= 1",
    },
    "account_knowledge_bases": {
        "ck_knowledge_bases_status": (
            "status IN ('empty','indexing','ready','stale','attention')"
        ),
        "ck_knowledge_bases_revision": (
            "rules_version >= 0 AND index_revision >= 0 AND revision >= 1"
        ),
    },
    "knowledge_sources": {
        "ck_knowledge_sources_kind": (
            "kind IN ('document','image','video','audio','text','reference')"
        ),
        "ck_knowledge_sources_status": (
            "status IN ('pending','indexing','ready','failed','stale')"
        ),
        "ck_knowledge_sources_revision": "revision >= 1",
        "ck_knowledge_sources_source_mode": (
            "source_mode IN ('file','url','text')"
        ),
        "ck_knowledge_sources_source_url": (
            "(source_mode = 'url' AND source_url IS NOT NULL "
            "AND length(trim(source_url)) > 0 "
            "AND source_url = trim(source_url) "
            "AND (lower(source_url) LIKE 'http://%' "
            "OR lower(source_url) LIKE 'https://%')) "
            "OR (source_mode IN ('file','text') AND source_url IS NULL)"
        ),
    },
    "brand_kits": {
        "ck_brand_kits_status": "status IN ('draft','active','archived')",
        "ck_brand_kits_version": "version >= 1 AND revision >= 1",
    },
    "account_config_copy_runs": {
        "ck_copy_runs_status": (
            "status IN ('running','succeeded','failed','rolled_back')"
        ),
        "ck_copy_runs_accounts": "source_account_id <> target_account_id",
    },
    "provider_profiles": {
        "ck_provider_profiles_adapter": (
            "adapter_type IN ('direct_api','openai_compatible','comfyui','runninghub')"
        ),
        "ck_provider_profiles_health": (
            "health_status IN ('unknown','checking','ready','degraded','failed')"
        ),
        "ck_provider_profiles_limits": (
            "timeout_ms > 0 AND max_concurrency > 0 AND revision >= 1"
        ),
    },
    "model_profiles": {
        "ck_model_profiles_discovery": (
            "discovery_source IN ('discovered','manual','migrated')"
        ),
        "ck_model_profiles_revision": "revision >= 1",
    },
    "model_capabilities": {
        "ck_model_capabilities_contract_revision": "contract_revision >= 0",
        "ck_model_capabilities_verified_at": (
            "contract_verified = 0 OR verified_at IS NOT NULL"
        ),
    },
    "prompt_profiles": {
        "ck_prompt_profiles_status": "status IN ('draft','active','archived')",
        "ck_prompt_profiles_version": "version >= 1 AND revision >= 1",
    },
    "capability_routes": {
        "ck_capability_routes_validation": (
            "validation_status IN ('valid','incomplete','invalid')"
        ),
        "ck_capability_routes_revision": "revision >= 1",
    },
    "composition_template_profiles": {
        "ck_composition_templates_status": (
            "status IN ('draft','active','archived')"
        ),
        "ck_composition_templates_type": (
            "template_type IN "
            "('slideshow','talking_head','product_showcase','mixed_media')"
        ),
        "ck_composition_templates_version": "version >= 1 AND revision >= 1",
    },
    "account_ai_recipes": {
        "ck_account_ai_recipes_status": "status IN ('draft','active','archived')",
        "ck_account_ai_recipes_validation": (
            "validation_status IN ('valid','incomplete','invalid')"
        ),
        "ck_account_ai_recipes_content_hash": (
            "length(content_hash) = 64 "
            "AND content_hash NOT GLOB '*[^0-9a-f]*'"
        ),
        "ck_account_ai_recipes_version": "version >= 1 AND revision >= 1",
    },
    "runtime_tasks": {
        "ck_runtime_tasks_scope": "scope IN ('system','account')",
        "ck_runtime_tasks_account_scope": (
            "(scope = 'system' AND account_id IS NULL) OR "
            "(scope = 'account' AND account_id IS NOT NULL "
            "AND length(trim(account_id)) > 0)"
        ),
        "ck_runtime_tasks_task_type": (
            "length(trim(task_type)) > 0 AND task_type = trim(task_type)"
        ),
        "ck_runtime_tasks_status": (
            "status IN ('queued','running','cancelling','failed','completed')"
        ),
        "ck_runtime_tasks_completion_kind": (
            "completion_kind IS NULL OR completion_kind IN ('succeeded','cancelled')"
        ),
        "ck_runtime_tasks_failure_kind": (
            "failure_kind IS NULL OR failure_kind IN "
            "('error','timed_out','restart_interrupted')"
        ),
        "ck_runtime_tasks_terminal_kind": (
            "(status = 'completed' AND completion_kind IS NOT NULL "
            "AND failure_kind IS NULL AND completed_at IS NOT NULL) "
            "OR (status = 'failed' AND failure_kind IS NOT NULL "
            "AND completion_kind IS NULL AND completed_at IS NOT NULL) "
            "OR (status IN ('queued','running','cancelling') "
            "AND completion_kind IS NULL AND failure_kind IS NULL "
            "AND completed_at IS NULL)"
        ),
        "ck_runtime_tasks_progress": "progress BETWEEN 0 AND 1",
        "ck_runtime_tasks_attempt_revision": "attempt >= 1 AND revision >= 1",
        "ck_runtime_tasks_idempotency_hash": (
            "length(idempotency_key_hash) = 64 "
            "AND idempotency_key_hash NOT GLOB '*[^0-9a-f]*'"
        ),
        "ck_runtime_tasks_request_hash": (
            "length(request_hash) = 64 "
            "AND request_hash NOT GLOB '*[^0-9a-f]*'"
        ),
        "ck_runtime_tasks_handler_version": "handler_version >= 1",
    },
    "runtime_events": {
        "ck_runtime_events_topic": "length(trim(topic)) > 0",
        "ck_runtime_events_account_topic": (
            "(account_id IS NULL AND topic LIKE 'system:%' "
            "AND length(topic) > length('system:')) OR "
            "(account_id IS NOT NULL AND length(trim(account_id)) > 0 "
            "AND "
            "substr(topic, 1, length('account:' || account_id || ':')) = "
            "'account:' || account_id || ':' "
            "AND length(topic) > length('account:' || account_id || ':'))"
        ),
        "ck_runtime_events_sequence": "sequence >= 1",
    },
    "runtime_mutation_idempotency": {
        "ck_runtime_mutation_scope": "scope IN ('system','account')",
        "ck_runtime_mutation_account_scope": (
            "(scope = 'system' AND account_id IS NULL) OR "
            "(scope = 'account' AND account_id IS NOT NULL "
            "AND length(trim(account_id)) > 0)"
        ),
        "ck_runtime_mutation_operation": (
            "length(trim(operation_name)) > 0 "
            "AND operation_name = trim(operation_name)"
        ),
        "ck_runtime_mutation_idempotency_hash": (
            "length(idempotency_key_hash) = 64 "
            "AND idempotency_key_hash NOT GLOB '*[^0-9a-f]*'"
        ),
        "ck_runtime_mutation_request_hash": (
            "length(request_hash) = 64 "
            "AND request_hash NOT GLOB '*[^0-9a-f]*'"
        ),
        "ck_runtime_mutation_response": "length(trim(response_json)) > 0",
        "ck_runtime_mutation_resource": (
            "(resource_type IS NULL AND resource_id IS NULL) OR "
            "(resource_type IS NOT NULL AND resource_id IS NOT NULL "
            "AND length(trim(resource_type)) > 0 "
            "AND resource_type = trim(resource_type) "
            "AND length(trim(resource_id)) > 0 "
            "AND resource_id = trim(resource_id))"
        ),
        "ck_runtime_mutation_retention": (
            "length(trim(created_at)) > 0 "
            "AND length(trim(expires_at)) > 0 "
            "AND expires_at > created_at"
        ),
    },
}

P0_CHECK_CONTRACTS.update(
    {
        "ai_dependency_snapshots": {
            "ck_ai_dependency_snapshots_owner": (
                "owner_type IN ('route','recipe','composition_template',"
                "'execution_preflight')"
            ),
            "ck_ai_dependency_snapshots_status": "status IN ('valid','invalid')",
        },
        "provider_profile_revisions": {
            "ck_provider_revisions_revision": "revision >= 1",
        },
        "model_profile_revisions": {
            "ck_model_revisions_revision": "revision >= 1",
        },
        "capability_route_revisions": {
            "ck_route_revisions_status": "status IN ('draft','active','archived')",
            "ck_route_revisions_limits": (
                "revision >= 1 AND timeout_ms > 0 AND max_retries >= 0 "
                "AND max_concurrency > 0 AND max_cost_micros >= 0"
            ),
        },
        "ai_provider_validation_runs": {
            "ck_ai_provider_validation_stage": (
                "stage IN ('network','authentication','model_discovery',"
                "'real_small_call')"
            ),
            "ck_ai_provider_validation_status": (
                "status IN ('queued','running','verified','partial','failed',"
                "'cancelled')"
            ),
        },
        "account_assets": {
            "ck_account_assets_source_kind": "source_kind IN ('controlled_file')",
            "ck_account_assets_status": (
                "status IN ('pending','ready','metadata_only','failed','stale')"
            ),
            "ck_account_assets_limits": "byte_size >= 0 AND revision >= 1",
        },
        "knowledge_index_chunks": {
            "ck_knowledge_index_chunks_limits": (
                "source_revision >= 1 AND ordinal >= 0 AND token_count >= 0"
            ),
        },
        "ai_execution_candidates": {
            "ck_ai_execution_candidates_ordinal": "ordinal >= 0",
        },
        "ai_executions": {
            "ck_ai_executions_status": (
                "status IN ('queued','running','cancelling','failed','completed')"
            ),
            "ck_ai_executions_completion": (
                "completion_kind IS NULL OR completion_kind IN "
                "('succeeded','cancelled')"
            ),
            "ck_ai_executions_failure": (
                "failure_kind IS NULL OR failure_kind IN "
                "('error','timed_out','restart_interrupted','result_unknown')"
            ),
            "ck_ai_executions_cost_status": (
                "cost_status IN ('reported','estimated','unavailable')"
            ),
            "ck_ai_executions_limits": (
                "budget_limit_micros >= 0 AND output_count >= 0 AND revision >= 1"
            ),
        },
        "ai_execution_jobs": {
            "ck_ai_execution_jobs_status": (
                "status IN ('queued','running','cancelling','failed','completed')"
            ),
            "ck_ai_execution_jobs_completion": (
                "completion_kind IS NULL OR completion_kind IN "
                "('succeeded','cancelled')"
            ),
            "ck_ai_execution_jobs_failure": (
                "failure_kind IS NULL OR failure_kind IN "
                "('error','timed_out','restart_interrupted','result_unknown')"
            ),
            "ck_ai_execution_jobs_attempt": (
                "attempt >= 1 AND fallback_index >= 0 AND retry_index >= 0 "
                "AND revision >= 1"
            ),
        },
        "ai_usage_records": {
            "ck_ai_usage_cost_source": (
                "cost_source IN ('reported','estimated','unavailable')"
            ),
        },
        "ai_execution_outputs": {
            "ck_ai_outputs_byte_size": "byte_size >= 0",
        },
    }
)
