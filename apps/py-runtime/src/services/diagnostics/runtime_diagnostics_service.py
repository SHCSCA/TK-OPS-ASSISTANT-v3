from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from app.config import RuntimeConfig
from app.logging import redact_log_text
from errors import DomainError, ErrorCode
from persistence.migration import MigrationReport
from services.media_tool_resolver import resolve_ffmpeg, resolve_ffprobe

log = logging.getLogger(__name__)

_LOG_ID_PATTERN = re.compile(r"^log_[A-Za-z0-9]{8,128}$")
_SAFE_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SAFE_ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_MAX_SUMMARY_LENGTH = 500


class RuntimeDiagnosticsService:
    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig,
        migration_report: MigrationReport,
        log_dir: Path,
    ) -> None:
        self._runtime_config = runtime_config
        self._migration_report = migration_report
        self._log_dir = log_dir

    def get_diagnostics(self) -> dict[str, object]:
        try:
            ffprobe = resolve_ffprobe(repo_root=self._runtime_config.repo_root)
            ffmpeg = resolve_ffmpeg(repo_root=self._runtime_config.repo_root)
            return {
                "runtime": {
                    "status": "ready",
                    "version": self._runtime_config.version,
                    "mode": self._runtime_config.mode,
                },
                "database": {
                    "status": (
                        "ready"
                        if self._runtime_config.database_path.is_file()
                        else "failed"
                    ),
                    "schemaRevision": self._migration_report.target_revision,
                    "migrationChanged": self._migration_report.changed,
                },
                "directories": {
                    "status": self._directory_status(),
                    "items": self._directory_items(),
                },
                "mediaTools": {
                    "status": (
                        "ready"
                        if ffprobe.status == "ready" and ffmpeg.status == "ready"
                        else "attention"
                    ),
                    "ffprobe": {
                        "status": ffprobe.status,
                        "source": ffprobe.source,
                        "errorCode": ffprobe.error_code,
                    },
                    "ffmpeg": {
                        "status": ffmpeg.status,
                        "source": ffmpeg.source,
                        "errorCode": ffmpeg.error_code,
                    },
                },
                "sidecar": {
                    "status": (
                        "ready"
                        if self._runtime_config.managed_sidecar
                        else "not_managed"
                    ),
                    "managed": self._runtime_config.managed_sidecar,
                    "nextStage": None,
                },
                "checkedAt": _utc_now(),
            }
        except DomainError:
            raise
        except Exception as exc:
            log.exception("读取 Runtime v1 诊断失败")
            raise DomainError(
                ErrorCode.DIAGNOSTICS_UNAVAILABLE,
                "诊断信息暂不可用，请稍后重试",
                status_code=503,
                loggable=True,
            ) from exc

    def get_safe_log_excerpt(self, log_id: str) -> dict[str, object]:
        if not _LOG_ID_PATTERN.fullmatch(log_id):
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "日志标识格式无效",
                status_code=422,
            )
        log_path = self._log_dir / "runtime.jsonl"
        try:
            matched = self._find_log_entry(log_path, log_id)
        except OSError as exc:
            log.exception("读取 Runtime 诊断日志失败: log_id=%s", log_id)
            raise DomainError(
                ErrorCode.DIAGNOSTICS_UNAVAILABLE,
                "诊断日志暂不可用，请稍后重试",
                status_code=503,
                loggable=True,
            ) from exc

        if matched is None:
            raise DomainError(
                ErrorCode.LOG_NOT_FOUND,
                "日志引用不存在或已过期",
                status_code=404,
            )
        return self._to_safe_excerpt(log_id, matched)

    def _directory_items(self) -> list[dict[str, object]]:
        paths = {
            "runtimeData": self._runtime_config.data_dir,
            "cache": self._runtime_config.data_dir / "cache",
            "exports": self._runtime_config.data_dir / "exports",
            "logs": self._log_dir,
        }
        return [
            {
                "key": key,
                "status": "ready" if path.is_dir() else "missing",
                "writable": path.is_dir() and os.access(path, os.W_OK),
            }
            for key, path in paths.items()
        ]

    def _directory_status(self) -> str:
        items = self._directory_items()
        return (
            "ready"
            if all(item["status"] == "ready" and item["writable"] for item in items)
            else "attention"
        )

    def _find_log_entry(
        self,
        log_path: Path,
        log_id: str,
    ) -> dict[str, object] | None:
        if not log_path.is_file():
            return None
        matched: dict[str, object] | None = None
        with log_path.open("r", encoding="utf-8") as file:
            for line in file:
                if log_id not in line:
                    continue
                try:
                    candidate = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if candidate.get("log_id") == log_id:
                    matched = candidate
        return matched

    def _to_safe_excerpt(
        self,
        log_id: str,
        entry: dict[str, object],
    ) -> dict[str, object]:
        level = str(entry.get("level") or "ERROR").casefold()
        severity = (
            "error"
            if level in {"error", "critical"}
            else "warning"
            if level == "warning"
            else "info"
        )
        error_code = _safe_error_code(entry.get("error_code"))
        return {
            "logId": log_id,
            "severity": severity,
            "summary": _safe_summary(entry.get("message")),
            "errorCode": error_code,
            "stage": _safe_reference(entry.get("stage")),
            "occurredAt": _safe_timestamp(entry.get("timestamp")),
            "suggestedActions": _suggested_actions(error_code),
            "requestId": _safe_reference(entry.get("request_id")),
            "operationId": _safe_reference(entry.get("operation_id")),
        }


def _safe_summary(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "Runtime 诊断记录"
    redacted = redact_log_text(value)
    compact = " ".join(redacted.split())
    if not compact:
        return "Runtime 诊断记录"
    if len(compact) <= _MAX_SUMMARY_LENGTH:
        return compact
    return f"{compact[:_MAX_SUMMARY_LENGTH - 1]}…"


def _safe_reference(value: object) -> str | None:
    if not isinstance(value, str) or not _SAFE_REFERENCE_PATTERN.fullmatch(value):
        return None
    return value


def _safe_error_code(value: object) -> str | None:
    if not isinstance(value, str) or not _SAFE_ERROR_CODE_PATTERN.fullmatch(value):
        return None
    return value


def _safe_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 64:
        return ""
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return ""
    return value


def _suggested_actions(error_code: str | None) -> list[str]:
    if error_code in {
        ErrorCode.RUNTIME_SESSION_REQUIRED,
        ErrorCode.RUNTIME_SESSION_INVALID,
    }:
        return ["重新建立桌面 Runtime 连接"]
    if error_code in {
        ErrorCode.DATABASE_SCHEMA_UNSUPPORTED,
        ErrorCode.MIGRATION_FAILED,
    }:
        return ["保留当前数据库", "打开迁移诊断", "使用受控恢复流程"]
    if error_code == ErrorCode.LICENSE_INVALID:
        return ["返回许可证向导并重新验证"]
    return ["重试操作", "如仍失败请打开系统诊断"]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
