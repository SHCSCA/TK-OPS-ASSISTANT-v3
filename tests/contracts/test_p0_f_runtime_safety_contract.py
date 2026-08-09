from __future__ import annotations

from pathlib import Path

import pytest

from persistence.migration.compatibility import (
    P0_MINIMUM_SUPPORTED_SCHEMA_REVISION,
    SchemaCompatibilityEvidenceError,
    verify_runtime_compatibility_evidence,
    write_runtime_compatibility_evidence,
)
from persistence.migration.runner import MigrationReport

TARGET_REVISION = "0022_p0g_production_hardening"


def test_compatibility_evidence_declares_real_p0_read_range(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-schema-compatibility.json"

    written = write_runtime_compatibility_evidence(
        path,
        runtime_version="0.4.7",
        migration_log_id="log_contract",
        cutover_event_id="cut_contract",
        database_fingerprint="sha256-contract",
        target_revision=TARGET_REVISION,
        artifact_build_id="build:contract:001",
    )
    verified = verify_runtime_compatibility_evidence(path)

    assert verified == written
    assert verified.rollback_eligible is True
    assert (
        verified.schema_range.minimum_revision
        == P0_MINIMUM_SUPPORTED_SCHEMA_REVISION
    )
    assert verified.schema_range.maximum_revision == TARGET_REVISION
    assert verified.schema_range.write_revision == TARGET_REVISION


def test_missing_tauri_build_id_is_not_rollback_eligible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TK_OPS_RUNTIME_ARTIFACT_BUILD_ID", raising=False)
    path = tmp_path / "runtime-schema-compatibility.json"

    evidence = write_runtime_compatibility_evidence(
        path,
        runtime_version="development",
        migration_log_id="log_development",
        cutover_event_id="cut_development",
        database_fingerprint="sha256-development",
        target_revision=TARGET_REVISION,
    )

    assert evidence.artifact_build_id is None
    assert evidence.rollback_eligible is False
    with pytest.raises(
        SchemaCompatibilityEvidenceError,
        match="Tauri 注入",
    ):
        write_runtime_compatibility_evidence(
            path,
            runtime_version="0.4.7",
            migration_log_id="log_managed",
            cutover_event_id="cut_managed",
            database_fingerprint="sha256-managed",
            target_revision=TARGET_REVISION,
            require_artifact_build_id=True,
        )


def test_migration_log_context_never_exposes_local_evidence_paths(
    tmp_path: Path,
) -> None:
    report = MigrationReport(
        log_id="log_contract",
        schema_kind="versioned",
        previous_revision=TARGET_REVISION,
        target_revision=TARGET_REVISION,
        backup_database_id=None,
        duration_ms=1,
        table_count=10,
        changed=False,
        cutover_event_id="cut_contract",
        cutover_journal_path=str(tmp_path / "private" / "cutover.json"),
        compatibility_evidence_path=str(
            tmp_path / "private" / "compatibility.json"
        ),
    )

    context = report.to_log_context()
    serialized = repr(context)

    assert context["cutoverJournalReady"] is True
    assert context["compatibilityEvidenceReady"] is True
    assert str(tmp_path) not in serialized
