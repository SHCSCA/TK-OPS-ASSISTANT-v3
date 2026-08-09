from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.engine import Engine

import app.factory as runtime_factory
import app.pre_write_startup_recovery as startup_recovery_module
from app.config import RuntimeConfig
from app.pre_write_startup_recovery import (
    PRE_WRITE_STARTUP_FAILED,
    PRE_WRITE_STARTUP_RESTORE_FORBIDDEN,
    PreWriteStartupRecoveryCoordinator,
    PreWriteStartupRecoveryError,
)
from app.secret_store import SecretStore
from app.write_gate import RuntimeWriteGate
from persistence.migration.cutover import DurableCutoverJournal
from persistence.migration.report import MigrationReport
from persistence.migration.types import BackupManifest
from sidecar_main import _safe_error


class _FakeEngine:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def dispose(self) -> None:
        self._calls.append("engine.dispose")


class _FailingBackgroundServices:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def start(self) -> None:
        self._calls.append("background.start")
        raise RuntimeError("模拟后台启动失败")

    async def shutdown(self) -> None:
        self._calls.append("background.shutdown")


def test_container_build_failure_disposes_engine_before_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    report = _migration_report(tmp_path)
    runtime_config = SimpleNamespace(database_path=tmp_path / "runtime.db")
    engine = _FakeEngine(calls)
    _install_successful_restore(monkeypatch, calls, report)
    monkeypatch.setattr(
        runtime_factory,
        "load_runtime_bootstrap_config",
        lambda: SimpleNamespace(data_dir=tmp_path),
    )
    monkeypatch.setattr(runtime_factory, "configure_logging", lambda _path: None)
    monkeypatch.setattr(
        runtime_factory,
        "load_runtime_config",
        lambda _bootstrap: runtime_config,
    )
    monkeypatch.setattr(
        runtime_factory,
        "prepare_runtime_database",
        lambda _config: report,
    )
    monkeypatch.setattr(
        runtime_factory,
        "build_secret_store",
        lambda _config: object(),
    )
    monkeypatch.setattr(
        runtime_factory,
        "create_runtime_engine",
        lambda _path: engine,
    )

    def fail_container_build(**_: object) -> None:
        raise RuntimeError("模拟容器构建失败")

    monkeypatch.setattr(
        runtime_factory,
        "build_runtime_container",
        fail_container_build,
    )

    with pytest.raises(PreWriteStartupRecoveryError) as captured:
        runtime_factory.create_app()

    assert calls == ["engine.dispose", "database.restore", "fingerprint.validate"]
    assert captured.value.error_code == PRE_WRITE_STARTUP_FAILED
    assert captured.value.log_id == report.log_id
    assert captured.value.restored is True
    assert _cutover_stages(report)[-1] == (
        "pre_write_startup_restore_validated"
    )
    assert _safe_error(captured.value) == (
        PRE_WRITE_STARTUP_FAILED,
        str(captured.value),
        report.log_id,
    )


@pytest.mark.asyncio
async def test_background_start_failure_stops_background_before_engine_and_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    report = _migration_report(tmp_path)
    coordinator = PreWriteStartupRecoveryCoordinator(
        database_path=tmp_path / "runtime.db",
        migration_report=report,
    )
    background = _FailingBackgroundServices(calls)
    engine = _FakeEngine(calls)
    _install_successful_restore(monkeypatch, calls, report)
    journal = DurableCutoverJournal(Path(report.cutover_journal_path))

    def write_transition(
        stage: str,
        evidence: Mapping[str, object],
    ) -> None:
        journal.append(
            cutover_event_id=report.cutover_event_id,
            log_id=report.log_id,
            stage=stage,
            evidence=evidence,
        )

    write_gate = RuntimeWriteGate(
        cutover_event_id=report.cutover_event_id,
        transition_writer=write_transition,
    )
    container = SimpleNamespace(
        kernel=SimpleNamespace(
            policy=SimpleNamespace(shutdown_grace_seconds=1.0)
        )
    )
    runtime_config = SimpleNamespace(
        version="test",
        allowed_origins=(),
        mode="test",
        database_path=tmp_path / "runtime.db",
    )
    monkeypatch.setattr(
        runtime_factory,
        "build_runtime_container",
        lambda **_: container,
    )
    monkeypatch.setattr(
        runtime_factory,
        "RuntimeBackgroundServices",
        lambda _kernel: background,
    )
    monkeypatch.setattr(
        runtime_factory,
        "_build_runtime_write_gate",
        lambda **_: write_gate,
    )
    monkeypatch.setattr(
        runtime_factory,
        "attach_container_state",
        lambda _app, _container: None,
    )
    monkeypatch.setattr(
        runtime_factory,
        "install_runtime_write_gate_middleware",
        lambda _app, _gate: None,
    )
    monkeypatch.setattr(
        runtime_factory,
        "install_v1_security_middleware",
        lambda _app: None,
    )
    monkeypatch.setattr(
        runtime_factory,
        "install_request_context_middleware",
        lambda _app: None,
    )
    monkeypatch.setattr(
        runtime_factory,
        "install_exception_handlers",
        lambda _app: None,
    )
    monkeypatch.setattr(
        runtime_factory,
        "register_routes",
        lambda _app, _container: None,
    )
    app = runtime_factory._build_runtime_app(
        runtime_config=cast(RuntimeConfig, runtime_config),
        migration_report=report,
        secret_store=cast(SecretStore, object()),
        engine=cast(Engine, engine),
        startup_recovery=coordinator,
    )

    with pytest.raises(PreWriteStartupRecoveryError) as captured:
        async with app.router.lifespan_context(app):
            pytest.fail("后台启动失败时不应进入 Runtime 就绪区间")

    assert calls == [
        "background.start",
        "background.shutdown",
        "engine.dispose",
        "database.restore",
        "fingerprint.validate",
    ]
    assert captured.value.restored is True
    assert captured.value.log_id == report.log_id


def test_durable_open_forbids_automatic_startup_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    report = _migration_report(tmp_path)
    journal = DurableCutoverJournal(Path(report.cutover_journal_path))
    journal.append(
        cutover_event_id=report.cutover_event_id,
        log_id=report.log_id,
        stage="write_gate_opened",
        evidence={"automaticRestoreAllowed": False},
    )

    def unexpected_restore(**_: object) -> bool:
        calls.append("database.restore")
        return True

    monkeypatch.setattr(
        startup_recovery_module,
        "restore_pre_write_migration_failure",
        unexpected_restore,
    )
    coordinator = PreWriteStartupRecoveryCoordinator(
        database_path=tmp_path / "runtime.db",
        migration_report=report,
    )

    with pytest.raises(PreWriteStartupRecoveryError) as captured:
        coordinator.recover_sync(
            RuntimeError("模拟写门开放后的启动失败"),
            engine=_FakeEngine(calls),
            failure_stage="runtime_started_event",
        )

    assert calls == ["engine.dispose"]
    assert captured.value.error_code == PRE_WRITE_STARTUP_RESTORE_FORBIDDEN
    assert captured.value.restored is False
    assert captured.value.automatic_restore_allowed is False
    assert "pre_write_startup_restore_started" not in _cutover_stages(report)


def _migration_report(tmp_path: Path) -> MigrationReport:
    journal = DurableCutoverJournal(tmp_path / "cutover-journal.json")
    started = journal.begin(
        log_id="log_p0f_startup_recovery",
        evidence={"automaticRestoreAllowed": True},
    )
    manifest = BackupManifest(
        backup_dir=tmp_path / "backup-unit",
        database_id="abcdef123456",
        created_at="2026-07-26T00:00:00+00:00",
        checkpoint_busy=0,
        checkpoint_log_frames=0,
        checkpointed_frames=0,
        files=(),
    )
    return MigrationReport(
        log_id="log_p0f_startup_recovery",
        schema_kind="versioned",
        previous_revision="0017_p0_enforce_and_cutover",
        target_revision="0020_p0e_ai_vertical_chain",
        backup_database_id=manifest.database_id,
        duration_ms=10,
        table_count=20,
        changed=True,
        cutover_event_id=started.cutover_event_id,
        cutover_journal_path=str(journal.path),
        pre_migration_fingerprint="a" * 64,
        post_migration_fingerprint="b" * 64,
        schema_read_min_revision="0017_p0_enforce_and_cutover",
        schema_read_max_revision="0020_p0e_ai_vertical_chain",
        backup_manifest=manifest,
    )


def _install_successful_restore(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[str],
    report: MigrationReport,
) -> None:
    def restore(**_: object) -> bool:
        calls.append("database.restore")
        return True

    def validate(
        _database_path: Path,
        *,
        expected_fingerprint: str,
        log_id: str,
    ) -> tuple[bool, str]:
        calls.append("fingerprint.validate")
        assert expected_fingerprint == report.pre_migration_fingerprint
        assert log_id == report.log_id
        return True, expected_fingerprint

    monkeypatch.setattr(
        startup_recovery_module,
        "restore_pre_write_migration_failure",
        restore,
    )
    monkeypatch.setattr(
        startup_recovery_module,
        "validate_restored_database_fingerprint",
        validate,
    )


def _cutover_stages(report: MigrationReport) -> list[str]:
    document = json.loads(
        Path(report.cutover_journal_path).read_text(encoding="utf-8")
    )
    return [
        str(item["stage"])
        for item in document["events"]
        if item["cutoverEventId"] == report.cutover_event_id
    ]
