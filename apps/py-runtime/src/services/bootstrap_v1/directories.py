from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Protocol

from app.config import RuntimeConfig
from errors import DomainError, ErrorCode
from schemas.v1.bootstrap import (
    DirectoryIssueDto,
    DirectoryItemDto,
    DirectoryReportDto,
)
from services.events import RuntimeEventDraft, RuntimeEventService

log = logging.getLogger(__name__)


class WorkspaceRootResolver(Protocol):
    def resolve(self, workspace_root_ref: str) -> Path: ...


class DirectoryV1Service:
    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig,
        workspace_root_resolver: WorkspaceRootResolver | None = None,
        event_service: RuntimeEventService | None = None,
    ) -> None:
        self._runtime_config = runtime_config
        self._workspace_root_resolver = workspace_root_resolver
        self._event_service = event_service

    def get_report(self) -> DirectoryReportDto:
        root = self._runtime_config.data_dir
        return self._inspect(root, create=False)

    def initialize(
        self,
        *,
        workspace_root_ref: str | None,
        idempotency_key: str,
    ) -> DirectoryReportDto:
        root = self._resolve_root(workspace_root_ref)
        report = self._inspect(root, create=True)
        if report.status == "failed":
            failed_keys = [
                item.key for item in report.directories if item.status == "failed"
            ]
            raise DomainError(
                ErrorCode.DIRECTORY_CREATE_FAILED,
                "工作目录初始化失败",
                status_code=500,
                loggable=True,
                log_context={"failedDirectories": failed_keys},
            )
        self._append_initialized_event(
            report,
            idempotency_key=idempotency_key,
        )
        return report

    def _append_initialized_event(
        self,
        report: DirectoryReportDto,
        *,
        idempotency_key: str,
    ) -> None:
        if self._event_service is None:
            return
        digest = hashlib.sha256(
            idempotency_key.encode("utf-8")
        ).hexdigest()
        self._event_service.append_standalone_idempotent(
            RuntimeEventDraft(
                event_id=f"evt_bootstrap_directories_{digest}",
                event_type="bootstrap.directories.changed",
                topic="system:bootstrap",
                revision=report.revision,
                payload={
                    "status": report.status,
                    "invalidations": ["bootstrap", "directories"],
                },
            )
        )

    def _resolve_root(self, workspace_root_ref: str | None) -> Path:
        if workspace_root_ref is None:
            return self._runtime_config.data_dir
        if self._workspace_root_resolver is None:
            raise DomainError(
                ErrorCode.DIRECTORY_CREATE_FAILED,
                "工作目录引用暂不可用",
                status_code=500,
                log_context={"workspaceRootRefProvided": True},
            )
        try:
            return self._workspace_root_resolver.resolve(workspace_root_ref)
        except DomainError:
            raise
        except Exception as exc:
            log.exception("解析工作目录引用失败")
            raise DomainError(
                ErrorCode.DIRECTORY_CREATE_FAILED,
                "工作目录引用无效",
                status_code=500,
                loggable=True,
                log_context={"workspaceRootRefProvided": True},
            ) from exc

    def _inspect(self, root: Path, *, create: bool) -> DirectoryReportDto:
        entries = _directory_entries(root)
        items: list[DirectoryItemDto] = []
        issues: list[DirectoryIssueDto] = []
        mtimes: list[int] = []
        hard_failure = False

        for key, label, path in entries:
            try:
                existed_before = path.is_dir()
                if create:
                    path.mkdir(parents=True, exist_ok=True)
                exists = path.is_dir()
                writable = exists and os.access(path, os.W_OK)
                if exists:
                    mtimes.append(path.stat().st_mtime_ns)
                item_status = (
                    "created"
                    if create and not existed_before and exists and writable
                    else "ready"
                    if exists and writable
                    else "failed"
                )
                if not exists:
                    issues.append(
                        DirectoryIssueDto(
                            code="DIRECTORY_NOT_INITIALIZED",
                            message=f"{label}尚未初始化",
                            logId=None,
                        )
                    )
                elif not writable:
                    hard_failure = True
                    issues.append(
                        DirectoryIssueDto(
                            code="DIRECTORY_NOT_WRITABLE",
                            message=f"{label}不可写",
                            logId=None,
                        )
                    )
            except Exception:
                log.exception("检查工作目录失败: key=%s", key)
                writable = False
                item_status = "failed"
                hard_failure = True
                issues.append(
                    DirectoryIssueDto(
                        code=str(ErrorCode.DIRECTORY_CREATE_FAILED),
                        message=f"{label}不可用",
                        logId=None,
                    )
                )

            items.append(
                DirectoryItemDto(
                    key=key,
                    status=item_status,
                    writable=writable,
                )
            )

        status = (
            "failed"
            if hard_failure
            else "attention"
            if issues
            else "ready"
        )
        return DirectoryReportDto(
            status=status,
            workspaceRootDisplay=_display_path(root),
            directories=items,
            issues=issues,
            revision=max(mtimes, default=0),
        )


def _directory_entries(root: Path) -> tuple[tuple[str, str, Path], ...]:
    return (
        ("data_root", "数据根目录", root),
        ("projects", "项目目录", root / "projects"),
        ("assets", "资产目录", root / "assets"),
        ("renders", "渲染目录", root / "renders"),
        ("cache", "缓存目录", root / "cache"),
        ("exports", "导出目录", root / "exports"),
        ("logs", "日志目录", root / "logs"),
        ("licenses", "许可证目录", root / "licenses"),
    )


def _display_path(path: Path) -> str:
    parts = path.parts
    if len(parts) <= 2:
        return path.name or "本地工作目录"
    return str(Path("…", *parts[-2:]))
