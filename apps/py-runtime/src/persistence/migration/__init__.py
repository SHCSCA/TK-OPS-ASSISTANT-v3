from __future__ import annotations

from persistence.migration.backup import (
    DatabaseBackupError,
    create_database_backup,
    load_backup_manifest,
    prune_database_backups,
    restore_database_backup,
    verify_database_backup,
)
from persistence.migration.compatibility import (
    RuntimeCompatibilityEvidence,
    RuntimeSchemaReadRange,
    SchemaCompatibilityEvidenceError,
    verify_runtime_compatibility_evidence,
    write_runtime_compatibility_evidence,
)
from persistence.migration.cutover import (
    CutoverEvidence,
    CutoverJournalError,
    DurableCutoverJournal,
)
from persistence.migration.fingerprint import (
    DatabaseIntegrityError,
    SchemaInspectionError,
    classify_database_schema,
    fingerprint_database,
    inspect_schema,
    inspect_database_schema,
    validate_database_integrity,
)
from persistence.migration.lock import (
    MigrationLock,
    MigrationLockError,
    MigrationLockTimeoutError,
)
from persistence.migration.runner import (
    DATABASE_SCHEMA_UNSUPPORTED,
    MIGRATION_FAILED,
    DatabaseSchemaUnsupportedError,
    RuntimeMigrationError,
    run_startup_migrations,
)
from persistence.migration.report import MigrationReport
from persistence.migration.target_contract import (
    TargetSchemaContractError,
    validate_target_schema_contract,
)
from persistence.migration.types import (
    BackupFileRecord,
    BackupManifest,
    DatabaseSchemaClassification,
    DatabaseSchemaKind,
    DatabaseIntegrityResult,
    SchemaFingerprint,
    SchemaInspection,
)

__all__ = [
    "BackupFileRecord",
    "BackupManifest",
    "DatabaseBackupError",
    "DatabaseIntegrityError",
    "DatabaseIntegrityResult",
    "DatabaseSchemaClassification",
    "DatabaseSchemaKind",
    "DatabaseSchemaUnsupportedError",
    "CutoverEvidence",
    "CutoverJournalError",
    "DATABASE_SCHEMA_UNSUPPORTED",
    "MIGRATION_FAILED",
    "MigrationLock",
    "MigrationLockError",
    "MigrationLockTimeoutError",
    "MigrationReport",
    "DurableCutoverJournal",
    "RuntimeCompatibilityEvidence",
    "RuntimeMigrationError",
    "RuntimeSchemaReadRange",
    "SchemaCompatibilityEvidenceError",
    "SchemaFingerprint",
    "SchemaInspection",
    "SchemaInspectionError",
    "TargetSchemaContractError",
    "classify_database_schema",
    "create_database_backup",
    "fingerprint_database",
    "inspect_database_schema",
    "inspect_schema",
    "load_backup_manifest",
    "prune_database_backups",
    "restore_database_backup",
    "run_startup_migrations",
    "validate_database_integrity",
    "validate_target_schema_contract",
    "verify_database_backup",
    "verify_runtime_compatibility_evidence",
    "write_runtime_compatibility_evidence",
]
