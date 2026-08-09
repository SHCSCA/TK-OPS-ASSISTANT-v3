from __future__ import annotations

from persistence.migration import MigrationReport
from services.events.contracts import RuntimeEventDraft
from services.events.service import RuntimeEventService


def record_migration_cutover_event(
    event_service: RuntimeEventService,
    migration_report: MigrationReport,
) -> None:
    """将本地 cutover 证据映射为可重放的 Runtime 系统事件。"""

    cutover_event_id = migration_report.cutover_event_id
    if not cutover_event_id:
        raise RuntimeError("迁移报告缺少 cutover_event_id")
    event_service.append_standalone_idempotent(
        RuntimeEventDraft(
            event_id=f"evt_{cutover_event_id}",
            event_type="migration.cutover.prepared",
            topic="system:migrations",
            aggregate_type="runtime_migration",
            aggregate_id=cutover_event_id,
            log_id=migration_report.log_id,
            revision=1,
            payload={
                "cutoverEventId": cutover_event_id,
                "previousRevision": migration_report.previous_revision,
                "targetRevision": migration_report.target_revision,
                "changed": migration_report.changed,
                "preMigrationFingerprint": (
                    migration_report.pre_migration_fingerprint
                ),
                "postMigrationFingerprint": (
                    migration_report.post_migration_fingerprint
                ),
                "schemaReadMinRevision": (
                    migration_report.schema_read_min_revision
                ),
                "schemaReadMaxRevision": (
                    migration_report.schema_read_max_revision
                ),
                "recoveryPolicy": migration_report.recovery_policy,
            },
        )
    )
