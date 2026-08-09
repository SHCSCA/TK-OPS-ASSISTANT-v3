from __future__ import annotations

from dataclasses import dataclass, field

from persistence.migration.types import BackupManifest


@dataclass(frozen=True, slots=True)
class MigrationReport:
    log_id: str
    schema_kind: str
    previous_revision: str | None
    target_revision: str
    backup_database_id: str | None
    duration_ms: int
    table_count: int
    changed: bool
    cutover_event_id: str = ""
    cutover_journal_path: str | None = field(default=None, repr=False)
    compatibility_evidence_path: str | None = field(default=None, repr=False)
    pre_migration_fingerprint: str = ""
    post_migration_fingerprint: str = ""
    schema_read_min_revision: str = ""
    schema_read_max_revision: str = ""
    recovery_policy: str = "pre_write_automatic_restore_only"
    backup_manifest: BackupManifest | None = field(
        default=None,
        repr=False,
    )
    pre_migration_empty_file_existed: bool = False

    def to_log_context(self) -> dict[str, object]:
        return {
            "logId": self.log_id,
            "schemaKind": self.schema_kind,
            "previousRevision": self.previous_revision,
            "targetRevision": self.target_revision,
            "backupDatabaseId": self.backup_database_id,
            "durationMs": self.duration_ms,
            "tableCount": self.table_count,
            "changed": self.changed,
            "cutoverEventId": self.cutover_event_id,
            "cutoverJournalReady": self.cutover_journal_path is not None,
            "compatibilityEvidenceReady": (
                self.compatibility_evidence_path is not None
            ),
            "preMigrationFingerprint": self.pre_migration_fingerprint,
            "postMigrationFingerprint": self.post_migration_fingerprint,
            "schemaReadMinRevision": self.schema_read_min_revision,
            "schemaReadMaxRevision": self.schema_read_max_revision,
            "recoveryPolicy": self.recovery_policy,
        }
