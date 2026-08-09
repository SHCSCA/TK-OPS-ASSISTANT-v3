from __future__ import annotations

from persistence.migration.types import DatabaseSchemaKind, SchemaFingerprint

KNOWN_LEGACY_SCHEMA_META_VERSION = "3"

# 该集合冻结 2026-07-19 真实开发库的 38 张业务表。
KNOWN_RUNTIME_CURRENT_TABLE_NAMES = (
    "account_group_members",
    "account_groups",
    "accounts",
    "ai_capability_configs",
    "ai_job_records",
    "ai_provider_health",
    "ai_provider_models",
    "ai_provider_settings",
    "asset_groups",
    "asset_references",
    "assets",
    "automation_task_runs",
    "automation_tasks",
    "browser_instances",
    "device_workspace_logs",
    "device_workspaces",
    "execution_bindings",
    "export_profiles",
    "imported_videos",
    "license_grant",
    "magic_cut_suggestion_drafts",
    "projects",
    "prompt_templates",
    "publish_plans",
    "publish_receipts",
    "render_tasks",
    "review_summaries",
    "script_versions",
    "session_context",
    "storyboard_versions",
    "subtitle_tracks",
    "system_config",
    "timelines",
    "video_deconstruction_artifacts",
    "video_stage_runs",
    "video_transcripts",
    "voice_profiles",
    "voice_tracks",
)

# 指纹只覆盖匿名结构信息，不包含数据库路径、业务行或密钥。
KNOWN_RUNTIME_CURRENT_SHA256 = "8fd9aba0469a8de2efc7f4c14563defc4746ce88598d56c808d4ddf713721f7d"
KNOWN_FRESH_RUNTIME_TABLE_NAMES = KNOWN_RUNTIME_CURRENT_TABLE_NAMES
KNOWN_FRESH_RUNTIME_SHA256 = "f65a60e68cf17e30fde645d37146299b21415946da991882668dec0485c846dd"
KNOWN_SCHEMA_V3_TABLE_NAMES = tuple(
    sorted((*KNOWN_RUNTIME_CURRENT_TABLE_NAMES, "schema_meta"))
)
KNOWN_SCHEMA_V3_SHA256 = "7ead34aa2a6749a0547cdded8c68f6378296416073e4dccb90e91e97fd6251da"


def match_known_legacy_schema(
    fingerprint: SchemaFingerprint,
    *,
    schema_meta_version: str | None,
) -> DatabaseSchemaKind | None:
    """仅接受完整命中三个冻结 cohort 的 legacy 数据库。"""

    if (
        schema_meta_version is None
        and fingerprint.table_names == KNOWN_FRESH_RUNTIME_TABLE_NAMES
        and fingerprint.sha256 == KNOWN_FRESH_RUNTIME_SHA256
    ):
        return DatabaseSchemaKind.LEGACY_FRESH_RUNTIME
    if (
        schema_meta_version is None
        and fingerprint.table_names == KNOWN_RUNTIME_CURRENT_TABLE_NAMES
        and fingerprint.sha256 == KNOWN_RUNTIME_CURRENT_SHA256
    ):
        return DatabaseSchemaKind.LEGACY_RUNTIME_CURRENT
    if (
        schema_meta_version == KNOWN_LEGACY_SCHEMA_META_VERSION
        and fingerprint.table_names == KNOWN_SCHEMA_V3_TABLE_NAMES
        and fingerprint.sha256 == KNOWN_SCHEMA_V3_SHA256
    ):
        return DatabaseSchemaKind.LEGACY_SCHEMA_V3
    return None


def matches_known_legacy_schema(
    fingerprint: SchemaFingerprint,
    *,
    schema_meta_version: str | None,
) -> bool:
    """兼容布尔判断调用。"""

    return match_known_legacy_schema(
        fingerprint,
        schema_meta_version=schema_meta_version,
    ) is not None
