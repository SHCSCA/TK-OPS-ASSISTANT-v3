from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Protocol

from persistence.migration import MigrationReport, RuntimeMigrationError
from persistence.migration.cutover import DurableCutoverJournal
from persistence.migration.recovery import (
    append_cutover_evidence_safely,
    is_automatic_restore_allowed,
    restore_pre_write_migration_failure,
    validate_restored_database_fingerprint,
)

log = logging.getLogger(__name__)

PRE_WRITE_STARTUP_FAILED = "PRE_WRITE_STARTUP_FAILED"
PRE_WRITE_STARTUP_RECOVERY_FAILED = "PRE_WRITE_STARTUP_RECOVERY_FAILED"
PRE_WRITE_STARTUP_RESTORE_FORBIDDEN = "PRE_WRITE_STARTUP_RESTORE_FORBIDDEN"


class BackgroundServices(Protocol):
    async def shutdown(self) -> None: ...


class DisposableEngine(Protocol):
    def dispose(self) -> None: ...


class PreWriteStartupRecoveryError(RuntimeMigrationError):
    """Runtime 写门前启动失败的稳定错误。"""

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        log_id: str,
        restored: bool,
        automatic_restore_allowed: bool,
        cutover_event_id: str,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            log_id=log_id,
            restored=restored,
            cutover_event_id=cutover_event_id,
        )
        self.automatic_restore_allowed = automatic_restore_allowed


class PreWriteStartupRecoveryCoordinator:
    """在后台与引擎完全停止后处理写门前数据库恢复。"""

    def __init__(
        self,
        *,
        database_path: Path,
        migration_report: MigrationReport,
    ) -> None:
        self._database_path = database_path.resolve()
        self._report = migration_report

    def recover_sync(
        self,
        cause: BaseException,
        *,
        engine: DisposableEngine | None,
        failure_stage: str,
    ) -> None:
        resources_released = self._dispose_engine(engine)
        self._recover_or_raise(
            cause,
            resources_released=resources_released,
            failure_stage=failure_stage,
        )

    async def recover_async(
        self,
        cause: BaseException,
        *,
        background_services: BackgroundServices,
        engine: DisposableEngine,
        failure_stage: str,
    ) -> None:
        background_stopped = await self._stop_background(background_services)
        engine_released = self._dispose_engine(engine)
        self._recover_or_raise(
            cause,
            resources_released=background_stopped and engine_released,
            failure_stage=failure_stage,
        )

    def _recover_or_raise(
        self,
        cause: BaseException,
        *,
        resources_released: bool,
        failure_stage: str,
    ) -> None:
        report = self._report
        journal = self._load_journal()
        automatic_restore_allowed = (
            journal is not None
            and is_automatic_restore_allowed(
                journal,
                cutover_event_id=report.cutover_event_id,
                log_id=report.log_id,
            )
        )
        self._record_failure(
            journal,
            failure_stage=failure_stage,
            resources_released=resources_released,
            automatic_restore_allowed=automatic_restore_allowed,
        )

        if not report.changed:
            self._raise_startup_error(
                cause,
                error_code=PRE_WRITE_STARTUP_FAILED,
                restored=False,
                automatic_restore_allowed=automatic_restore_allowed,
                message="Runtime 启动失败，数据库迁移前后未发生变更",
            )
        if not resources_released:
            self._raise_startup_error(
                cause,
                error_code=PRE_WRITE_STARTUP_RECOVERY_FAILED,
                restored=False,
                automatic_restore_allowed=automatic_restore_allowed,
                message="Runtime 启动失败且资源未完全停止，已保留当前数据库与恢复证据",
            )
        if journal is None or not automatic_restore_allowed:
            self._raise_startup_error(
                cause,
                error_code=PRE_WRITE_STARTUP_RESTORE_FORBIDDEN,
                restored=False,
                automatic_restore_allowed=False,
                message="Runtime 启动失败，写门状态不允许自动恢复，已保留当前数据库",
            )

        restored = self._restore_database(journal)
        if not restored:
            self._raise_startup_error(
                cause,
                error_code=PRE_WRITE_STARTUP_RECOVERY_FAILED,
                restored=False,
                automatic_restore_allowed=True,
                message="Runtime 启动失败且迁移前状态恢复未完成，已保留当前数据库与恢复证据",
            )
        self._raise_startup_error(
            cause,
            error_code=PRE_WRITE_STARTUP_FAILED,
            restored=True,
            automatic_restore_allowed=True,
            message="Runtime 启动失败，已恢复迁移前数据库状态",
        )

    def _restore_database(self, journal: DurableCutoverJournal) -> bool:
        report = self._report
        backup_manifest = report.backup_manifest
        if (
            backup_manifest is None
            and report.schema_kind != "empty"
        ):
            log.error(
                "写门前启动恢复缺少受控备份句柄: log_id=%s",
                report.log_id,
            )
            return False
        if (
            backup_manifest is not None
            and backup_manifest.database_id != report.backup_database_id
        ):
            log.error(
                "写门前启动恢复的备份标识不一致: log_id=%s",
                report.log_id,
            )
            return False

        try:
            journal.append(
                cutover_event_id=report.cutover_event_id,
                log_id=report.log_id,
                stage="pre_write_startup_restore_started",
                evidence={
                    "backupDatabaseId": report.backup_database_id,
                    "expectedFingerprint": report.pre_migration_fingerprint,
                },
            )
        except Exception:
            log.exception(
                "写门前启动恢复证据无法持久化，已拒绝修改数据库: log_id=%s",
                report.log_id,
            )
            return False

        restored = restore_pre_write_migration_failure(
            database_path=self._database_path,
            backup_manifest=backup_manifest,
            empty_file_existed=report.pre_migration_empty_file_existed,
            log_id=report.log_id,
        )
        actual_fingerprint: str | None = None
        if restored:
            restored, actual_fingerprint = validate_restored_database_fingerprint(
                self._database_path,
                expected_fingerprint=report.pre_migration_fingerprint,
                log_id=report.log_id,
            )
        stage = (
            "pre_write_startup_restore_validated"
            if restored
            else "pre_write_startup_restore_failed"
        )
        try:
            journal.append(
                cutover_event_id=report.cutover_event_id,
                log_id=report.log_id,
                stage=stage,
                evidence={
                    "expectedFingerprint": report.pre_migration_fingerprint,
                    "actualFingerprint": actual_fingerprint,
                    "integrity": "ok" if restored else "failed",
                },
            )
        except Exception:
            log.exception(
                "写门前启动恢复结果证据无法持久化: log_id=%s",
                report.log_id,
            )
            return False
        return restored

    def _record_failure(
        self,
        journal: DurableCutoverJournal | None,
        *,
        failure_stage: str,
        resources_released: bool,
        automatic_restore_allowed: bool,
    ) -> None:
        if journal is None:
            return
        append_cutover_evidence_safely(
            journal,
            cutover_event_id=self._report.cutover_event_id,
            log_id=self._report.log_id,
            stage="pre_write_startup_failed",
            evidence={
                "failureStage": failure_stage,
                "resourcesReleased": resources_released,
                "migrationChanged": self._report.changed,
                "automaticRestoreAllowed": automatic_restore_allowed,
            },
        )

    def _load_journal(self) -> DurableCutoverJournal | None:
        path = self._report.cutover_journal_path
        if not path or not self._report.cutover_event_id:
            log.error(
                "写门前启动恢复缺少 cutover 证据句柄: log_id=%s",
                self._report.log_id,
            )
            return None
        return DurableCutoverJournal(Path(path))

    def _dispose_engine(self, engine: DisposableEngine | None) -> bool:
        if engine is None:
            return True
        try:
            engine.dispose()
            return True
        except Exception:
            log.exception(
                "写门前启动失败后释放数据库引擎失败: log_id=%s",
                self._report.log_id,
            )
            return False

    async def _stop_background(
        self,
        background_services: BackgroundServices,
    ) -> bool:
        try:
            await background_services.shutdown()
            return True
        except asyncio.CancelledError:
            log.exception(
                "写门前启动失败后停止后台服务被取消: log_id=%s",
                self._report.log_id,
            )
            return False
        except Exception:
            log.exception(
                "写门前启动失败后停止后台服务失败: log_id=%s",
                self._report.log_id,
            )
            return False

    def _raise_startup_error(
        self,
        cause: BaseException,
        *,
        error_code: str,
        restored: bool,
        automatic_restore_allowed: bool,
        message: str,
    ) -> None:
        log.error(
            "%s: log_id=%s",
            message,
            self._report.log_id,
            exc_info=(type(cause), cause, cause.__traceback__),
            extra={
                "category": "runtime",
                "request_id": self._report.log_id,
                "context": {
                    "errorCode": error_code,
                    "cutoverEventId": self._report.cutover_event_id,
                    "restored": restored,
                    "automaticRestoreAllowed": automatic_restore_allowed,
                },
            },
        )
        raise PreWriteStartupRecoveryError(
            f"{message}，请查看日志后重试（log_id={self._report.log_id}）",
            error_code=error_code,
            log_id=self._report.log_id,
            restored=restored,
            automatic_restore_allowed=automatic_restore_allowed,
            cutover_event_id=self._report.cutover_event_id,
        ) from cause
