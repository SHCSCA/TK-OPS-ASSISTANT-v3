"""保守回填 P0 账号边界与旧 AI 配置。"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import logging
from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "0016_p0_backfill"
down_revision = "0015_p0_expand"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)


_CAPABILITY_KEYS = {
    "topic_generation",
    "script_generation",
    "script_rewrite",
    "storyboard_generation",
    "video_deconstruction",
    "speech_to_text",
    "image_generation",
    "text_to_video",
    "image_to_video",
    "tts",
    "subtitle_alignment",
    "asset_analysis",
    "embedding",
}
_CAPABILITY_ALIASES = {
    "tts_generation": "tts",
    "video_generation": "text_to_video",
    "video_transcription": "speech_to_text",
}
_KNOWN_ACCOUNT_STATUSES = {
    "active",
    "inactive",
    "paused",
    "draft",
    "unbound",
    "ready",
    "attention",
}
_GENERIC_CAPABILITY_MAP = {
    "asset_analysis": ("asset_analysis",),
    "embedding": ("embedding",),
    "image_generation": ("image_generation",),
    "speech_to_text": ("speech_to_text",),
    "tts": ("tts",),
    "video_generation": ("text_to_video", "image_to_video"),
}
_P0_DATA_TABLES = (
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


def upgrade() -> None:
    now = datetime.now(UTC).isoformat()
    _backfill_reconciled_columns(now)
    account_counts = _backfill_account_scope(now)
    ai_counts, source_checksums, skipped_capabilities = _backfill_ai_configuration(now)
    _record_backfill_audit(
        now,
        {**account_counts, **ai_counts},
        source_checksums,
        skipped_capabilities,
    )


def _backfill_reconciled_columns(now: str) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE voice_tracks
            SET version = CASE WHEN version IS NULL OR version < 1 THEN 1 ELSE version END,
                config_json = CASE WHEN config_json IS NULL OR config_json = '' THEN '{}' ELSE config_json END,
                updated_at = CASE
                    WHEN updated_at IS NULL OR updated_at = '' THEN COALESCE(NULLIF(created_at, ''), :now)
                    ELSE updated_at
                END
            """
        ),
        {"now": now},
    )
    bind.execute(
        sa.text(
            """
            UPDATE subtitle_tracks
            SET metadata_json = CASE
                    WHEN metadata_json IS NULL OR metadata_json = '' THEN '{}' ELSE metadata_json
                END,
                updated_at = CASE
                    WHEN updated_at IS NULL OR updated_at = '' THEN COALESCE(NULLIF(created_at, ''), :now)
                    ELSE updated_at
                END
            """
        ),
        {"now": now},
    )
    bind.execute(sa.text("UPDATE accounts SET revision = COALESCE(revision, 1)"))
    bind.execute(
        sa.text("UPDATE system_config SET ai_config_revision = COALESCE(ai_config_revision, 0)")
    )


def _backfill_account_scope(now: str) -> dict[str, int]:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE device_workspaces
            SET account_id = (
                SELECT MIN(binding.account_id)
                FROM execution_bindings AS binding
                WHERE binding.device_workspace_id = device_workspaces.id
            )
            WHERE account_id IS NULL
              AND 1 = (
                SELECT COUNT(DISTINCT binding.account_id)
                FROM execution_bindings AS binding
                WHERE binding.device_workspace_id = device_workspaces.id
              )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE browser_instances
            SET account_id = (
                SELECT workspace.account_id
                FROM device_workspaces AS workspace
                WHERE workspace.id = browser_instances.workspace_id
            )
            WHERE account_id IS NULL
            """
        )
    )
    invalid_binding_condition = """
        NOT EXISTS (
            SELECT 1
            FROM device_workspaces AS workspace
            JOIN browser_instances AS browser
              ON browser.id = execution_bindings.browser_instance_id
             AND browser.workspace_id = workspace.id
            WHERE workspace.id = execution_bindings.device_workspace_id
              AND workspace.account_id = execution_bindings.account_id
              AND browser.account_id = execution_bindings.account_id
        )
    """
    detached_binding_count = int(
        bind.execute(
            sa.text(
                f"""
                SELECT COUNT(*)
                FROM execution_bindings
                WHERE ({invalid_binding_condition})
                  AND (browser_instance_id IS NOT NULL OR status <> 'inactive')
                """
            )
        ).scalar_one()
    )
    bind.execute(
        sa.text(
            f"""
            UPDATE execution_bindings
            SET browser_instance_id = NULL,
                status = 'inactive'
            WHERE ({invalid_binding_condition})
            """
        )
    )

    for account in _rows(
        "SELECT id, platform, status, created_at, wizard_completed_at FROM accounts"
    ):
        account_id = str(account["id"])
        platform = str(account.get("platform") or "").strip().lower()
        old_status = str(account.get("status") or "").strip().lower()
        valid_binding_id = _valid_binding_id(account_id)
        if old_status == "archived":
            status = "archived"
            reason = "MIGRATED_ARCHIVED"
        elif old_status not in _KNOWN_ACCOUNT_STATUSES:
            status = "attention"
            reason = "MIGRATED_STATUS_UNKNOWN"
        elif platform != "tiktok":
            status = "attention"
            reason = "ACCOUNT_PLATFORM_UNSUPPORTED"
        elif valid_binding_id:
            status = "attention"
            reason = "MIGRATED_CONFIGURATION_UNVERIFIED"
        else:
            status = "unbound"
            reason = "EXECUTION_BINDING_REQUIRED"
        completed_at = account.get("wizard_completed_at") or account.get("created_at") or now
        bind.execute(
            sa.text(
                """
                UPDATE accounts
                SET status = :status,
                    status_reason_code = :reason,
                    wizard_completed_at = COALESCE(wizard_completed_at, :completed_at),
                    archived_at = CASE
                        WHEN :status = 'archived' THEN COALESCE(archived_at, :now)
                        ELSE archived_at
                    END,
                    revision = COALESCE(revision, 1)
                WHERE id = :account_id
                """
            ),
            {
                "account_id": account_id,
                "status": status,
                "reason": reason,
                "completed_at": completed_at,
                "now": now,
            },
        )
        _insert_ignore(
            "account_connections",
            {
                "id": f"legacy-connection:{account_id}",
                "account_id": account_id,
                "credential_ref": None,
                "session_ref": None,
                "auth_status": "unknown",
                "health_status": "unknown",
                "active_execution_binding_id": valid_binding_id,
                "last_checked_at": None,
                "error_code": reason,
                "error_log_id": None,
                "revision": 1,
                "created_at": now,
                "updated_at": now,
            },
        )
    if detached_binding_count:
        log.warning(
            "P0 回填已停用无法严格确认账号归属的执行绑定",
            extra={"detached_binding_count": detached_binding_count},
        )
    return {"detachedBindings": detached_binding_count}


def _valid_binding_id(account_id: str) -> str | None:
    row = op.get_bind().execute(
        sa.text(
            """
            SELECT binding.id
            FROM execution_bindings AS binding
            JOIN device_workspaces AS workspace
              ON workspace.id = binding.device_workspace_id
            JOIN browser_instances AS browser
              ON browser.id = binding.browser_instance_id
             AND browser.workspace_id = workspace.id
            WHERE binding.account_id = :account_id
              AND binding.status = 'active'
              AND workspace.account_id = binding.account_id
              AND browser.account_id = binding.account_id
            ORDER BY binding.updated_at DESC, binding.id ASC
            LIMIT 1
            """
        ),
        {"account_id": account_id},
    ).first()
    return str(row[0]) if row else None


def _backfill_ai_configuration(
    now: str,
) -> tuple[dict[str, int], dict[str, str], list[str]]:
    providers = _legacy_provider_rows()
    for provider_id, payload in providers.items():
        _insert_ignore(
            "provider_profiles",
            {
                "id": provider_id,
                "name": payload["name"],
                "adapter_type": _adapter_type(provider_id),
                "base_url": payload["base_url"],
                "credential_ref": None,
                "region": None,
                "proxy_ref": None,
                "timeout_ms": 30000,
                "max_concurrency": 1,
                "enabled": 0,
                "health_status": "unknown",
                "last_checked_at": None,
                "last_error_code": "MIGRATED_REQUIRES_HEALTH_CHECK",
                "last_error_log_id": None,
                "revision": 1,
                "created_at": now,
                "updated_at": payload["updated_at"] or now,
            },
        )

    model_count = 0
    capability_count = 0
    for model in _rows("SELECT * FROM ai_provider_models ORDER BY id"):
        provider_id = str(model.get("provider_id") or "").strip()
        if not provider_id:
            continue
        model_id = str(model["id"])
        _insert_ignore(
            "model_profiles",
            {
                "id": model_id,
                "provider_profile_id": provider_id,
                "model_id": str(model.get("model_id") or model_id),
                "display_name": str(model.get("display_name") or model.get("model_id") or model_id),
                "enabled": 0,
                "discovery_source": "migrated",
                "context_window": model.get("context_window"),
                "base_limits_json": json.dumps(
                    {"legacyDefaultFor": _json_list(model.get("default_for_json"))},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "revision": 1,
                "created_at": str(model.get("created_at") or now),
                "updated_at": str(model.get("updated_at") or now),
            },
        )
        model_count += 1
        for capability_key in _declared_capabilities(model):
            _insert_ignore(
                "model_capabilities",
                {
                    "id": f"legacy-capability:{model_id}:{capability_key}",
                    "model_profile_id": model_id,
                    "capability_key": capability_key,
                    "declared_supported": 1,
                    "adapter_supported": 0,
                    "contract_verified": 0,
                    "input_modalities_json": _safe_json_array(model.get("input_modalities_json")),
                    "output_modalities_json": _safe_json_array(model.get("output_modalities_json")),
                    "parameter_schema_json": "{}",
                    "source_urls_json": "[]",
                    "known_limits_json": "{}",
                    "verified_at": None,
                    "contract_revision": 0,
                },
            )
            capability_count += 1

    prompt_count, template_skips = _migrate_prompt_templates(now)
    capability_prompt_count, route_count, config_skips = _migrate_capability_configs(now)
    skipped_capabilities = sorted(set(template_skips) | set(config_skips))
    counts = {
        "providers": len(providers),
        "models": model_count,
        "modelCapabilities": capability_count,
        "prompts": prompt_count + capability_prompt_count,
        "routes": route_count,
        "skippedCapabilities": len(skipped_capabilities),
    }
    checksums = {
        "providers": _checksum(providers),
        "models": _checksum([row["id"] for row in _rows("SELECT id FROM ai_provider_models")]),
        "prompts": _checksum(
            [row["id"] for row in _rows("SELECT id FROM prompt_templates")]
            + [
                row["capability_id"]
                for row in _rows("SELECT capability_id FROM ai_capability_configs")
            ]
        ),
    }
    if any(value for key, value in counts.items() if key != "skippedCapabilities"):
        op.get_bind().execute(
            sa.text(
                """
                UPDATE system_config
                SET ai_config_revision = CASE
                    WHEN COALESCE(ai_config_revision, 0) < 1 THEN 1
                    ELSE ai_config_revision
                END
                """
            )
        )
    return counts, checksums, skipped_capabilities


def _legacy_provider_rows() -> dict[str, dict[str, str]]:
    providers: dict[str, dict[str, str]] = {}
    for row in _rows("SELECT provider_id, base_url, updated_at FROM ai_provider_settings"):
        provider_id = str(row.get("provider_id") or "").strip()
        if provider_id:
            providers[provider_id] = {
                "name": provider_id,
                "base_url": str(row.get("base_url") or ""),
                "updated_at": str(row.get("updated_at") or ""),
            }
    for query, key in (
        ("SELECT provider_id AS value FROM ai_provider_models", "value"),
        ("SELECT provider_id AS value FROM ai_provider_health", "value"),
        ("SELECT provider AS value FROM ai_capability_configs", "value"),
    ):
        for row in _rows(query):
            provider_id = str(row.get(key) or "").strip()
            if provider_id:
                providers.setdefault(
                    provider_id,
                    {"name": provider_id, "base_url": "", "updated_at": ""},
                )
    for row in _rows("SELECT provider_id, label FROM ai_provider_health"):
        provider_id = str(row.get("provider_id") or "").strip()
        label = str(row.get("label") or "").strip()
        if provider_id in providers and label:
            providers[provider_id]["name"] = label
    return providers


def _migrate_prompt_templates(now: str) -> tuple[int, list[str]]:
    count = 0
    skipped: list[str] = []
    for template in _rows("SELECT * FROM prompt_templates ORDER BY id"):
        source_id = str(template["id"])
        content = str(template.get("content") or "")
        capability_key = _normalize_capability(str(template.get("kind") or ""), keep_unknown=True)
        if capability_key not in _CAPABILITY_KEYS:
            skipped.append(capability_key)
            continue
        _insert_ignore(
            "prompt_profiles",
            {
                "id": f"legacy-template:{source_id}",
                "profile_key": f"legacy-template:{source_id}",
                "name": str(template.get("name") or source_id),
                "capability_key": capability_key,
                "version": 1,
                "status": "draft",
                "system_prompt": "",
                "task_template": content,
                "variables_schema_json": "{}",
                "output_schema_json": "{}",
                "visual_style_prefix": None,
                "safety_constraints_json": "[]",
                "content_hash": _checksum(content),
                "created_from_id": None,
                "created_at": str(template.get("created_at") or now),
                "activated_at": None,
            },
        )
        count += 1
    return count, skipped


def _migrate_capability_configs(now: str) -> tuple[int, int, list[str]]:
    prompt_count = 0
    route_count = 0
    skipped: list[str] = []
    for config in _rows("SELECT * FROM ai_capability_configs ORDER BY capability_id"):
        source_key = str(config["capability_id"])
        capability_key = _normalize_capability(source_key, keep_unknown=True)
        if capability_key not in _CAPABILITY_KEYS:
            skipped.append(capability_key)
            continue
        prompt_id = f"legacy-capability-prompt:{source_key}"
        system_prompt = str(config.get("system_prompt") or "")
        task_template = str(config.get("user_prompt_template") or "")
        _insert_ignore(
            "prompt_profiles",
            {
                "id": prompt_id,
                "profile_key": f"legacy-capability:{source_key}",
                "name": f"旧配置 · {source_key}",
                "capability_key": capability_key,
                "version": 1,
                "status": "draft",
                "system_prompt": system_prompt,
                "task_template": task_template,
                "variables_schema_json": "{}",
                "output_schema_json": "{}",
                "visual_style_prefix": None,
                "safety_constraints_json": "[]",
                "content_hash": _checksum([system_prompt, task_template]),
                "created_from_id": None,
                "created_at": str(config.get("updated_at") or now),
                "activated_at": None,
            },
        )
        prompt_count += 1
        provider_id = str(config.get("provider") or "")
        legacy_model_id = str(config.get("model") or "")
        model = op.get_bind().execute(
            sa.text(
                """
                SELECT id
                FROM model_profiles
                WHERE provider_profile_id = :provider_id AND model_id = :model_id
                LIMIT 1
                """
            ),
            {"provider_id": provider_id, "model_id": legacy_model_id},
        ).first()
        _insert_ignore(
            "capability_routes",
            {
                "id": f"legacy-route:{capability_key}",
                "capability_key": capability_key,
                "primary_model_profile_id": str(model[0]) if model else None,
                "fallback_model_profile_id": None,
                "prompt_profile_id": prompt_id,
                "enabled": 0,
                "validation_status": "incomplete",
                "validation_issues_json": json.dumps(
                    [
                        "MIGRATED_PROVIDER_HEALTH_UNKNOWN",
                        "MIGRATED_MODEL_CONTRACT_UNVERIFIED",
                    ],
                    ensure_ascii=False,
                ),
                "revision": 1,
                "created_at": str(config.get("updated_at") or now),
                "updated_at": str(config.get("updated_at") or now),
            },
        )
        route_count += 1
    return prompt_count, route_count, skipped


def _record_backfill_audit(
    now: str,
    counts: dict[str, int],
    source_checksums: dict[str, str],
    skipped_capabilities: list[str],
) -> None:
    account_count = int(op.get_bind().execute(sa.text("SELECT COUNT(*) FROM accounts")).scalar_one())
    if account_count == 0 and not any(counts.values()):
        return
    next_sequence = int(
        op.get_bind()
        .execute(
            sa.text(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM runtime_events WHERE topic = :topic"
            ),
            {"topic": "system.migrations"},
        )
        .scalar_one()
    )
    _insert_ignore(
        "runtime_events",
        {
            "event_id": "migration:0016_p0_backfill",
            "topic": "system.migrations",
            "sequence": next_sequence,
            "event_type": "migration.legacy_backfill_completed",
            "account_id": None,
            "aggregate_type": "database_migration",
            "aggregate_id": revision,
            "task_id": None,
            "log_id": None,
            "revision": 1,
            "payload_json": json.dumps(
                {
                    "sourceRevision": "0014_magic_cut_suggestion_drafts",
                    "accountRows": account_count,
                    "mappedRows": counts,
                    "sourceChecksums": source_checksums,
                    "skippedCapabilityKeys": skipped_capabilities,
                    "readinessPolicy": "unverified",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            "occurred_at": now,
            "published_at": None,
        },
    )


def _declared_capabilities(model: dict[str, Any]) -> list[str]:
    declared: set[str] = set()
    for value in _json_list(model.get("default_for_json")):
        normalized = _normalize_capability(str(value))
        if normalized in _CAPABILITY_KEYS:
            declared.add(normalized)
    for value in _json_list(model.get("capability_kinds_json")):
        declared.update(_GENERIC_CAPABILITY_MAP.get(str(value), ()))
    return sorted(declared)


def _normalize_capability(value: str, *, keep_unknown: bool = False) -> str:
    normalized = value.strip().lower()
    normalized = _CAPABILITY_ALIASES.get(normalized, normalized)
    if normalized in _CAPABILITY_KEYS:
        return normalized
    if keep_unknown:
        return normalized or "legacy_unknown"
    return ""


def _adapter_type(provider_id: str) -> str:
    normalized = provider_id.lower()
    if "runninghub" in normalized:
        return "runninghub"
    if "comfy" in normalized:
        return "comfyui"
    if "compatible" in normalized or normalized in {"openrouter", "ollama"}:
        return "openai_compatible"
    return "direct_api"


def _rows(query: str) -> list[dict[str, Any]]:
    return [dict(row) for row in op.get_bind().execute(sa.text(query)).mappings().all()]


def _json_list(value: Any) -> list[Any]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _safe_json_array(value: Any) -> str:
    return json.dumps(_json_list(value), ensure_ascii=False, sort_keys=True)


def _checksum(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _insert_ignore(table_name: str, values: dict[str, Any]) -> None:
    columns = ", ".join(f'"{column}"' for column in values)
    parameters = ", ".join(f":{column}" for column in values)
    op.get_bind().execute(
        sa.text(f'INSERT OR IGNORE INTO "{table_name}" ({columns}) VALUES ({parameters})'),
        values,
    )


def downgrade() -> None:
    populated = [
        table_name
        for table_name in _P0_DATA_TABLES
        if op.get_bind().execute(sa.text(f'SELECT 1 FROM "{table_name}" LIMIT 1')).first()
    ]
    if populated:
        names = ", ".join(sorted(populated))
        log.error("P0 回填迁移拒绝有数据降级", extra={"table_names": names})
        raise RuntimeError(
            "P0_DOWNGRADE_REQUIRES_BACKUP: P0 回填或新写数据无法无损逆映射；"
            f"请恢复迁移前备份。涉及表：{names}"
        )
