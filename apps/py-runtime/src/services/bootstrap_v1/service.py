from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Protocol

from app.config import RuntimeConfig
from errors import DomainError, ErrorCode
from schemas.v1.bootstrap import (
    BootstrapBlockingIssueDto,
    BootstrapStatusDto,
    DirectoryReportDto,
    LicenseStatusDto,
    MediaToolsStatusDto,
    RuntimeStatusDto,
    SelfCheckKey,
    TaskAcceptedDto,
)
from services.bootstrap_v1.directories import DirectoryV1Service
from services.bootstrap_v1.license import LicenseV1Service
from services.media_tool_resolver import resolve_ffmpeg, resolve_ffprobe
from services.tasks.types import JsonValue, RuntimeTaskRecord, TaskStatus

log = logging.getLogger(__name__)

SELF_CHECK_TASK_TYPE = "bootstrap.self_check"


class SystemTaskSubmitter(Protocol):
    async def submit_system_task(
        self,
        *,
        task_type: str,
        payload: Mapping[str, JsonValue],
        idempotency_key: str,
        request_id: str,
        operation_id: str,
        timeout_seconds: int | None = None,
    ) -> RuntimeTaskRecord: ...


class BootstrapV1Service:
    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig,
        license_service: LicenseV1Service,
        directory_service: DirectoryV1Service,
        task_submitter: SystemTaskSubmitter | None = None,
    ) -> None:
        self._runtime_config = runtime_config
        self._license_service = license_service
        self._directory_service = directory_service
        self._task_submitter = task_submitter

    def get_status(
        self,
        *,
        request_id: str,
        operation_id: str,
    ) -> BootstrapStatusDto:
        license_status = self.get_license_status(
            request_id=request_id,
            operation_id=operation_id,
        )
        directories = self._directory_service.get_report()
        runtime = RuntimeStatusDto(
            status="ready",
            version=self._runtime_config.version,
        )
        media_tools = self._get_media_tools_status()
        blocking_issues = _build_blocking_issues(
            license_status=license_status,
            directories=directories,
        )
        return BootstrapStatusDto(
            license=license_status,
            directories=directories,
            runtime=runtime,
            mediaTools=media_tools,
            canContinue=not blocking_issues,
            blockingIssues=blocking_issues,
            revision=max(license_status.revision, directories.revision),
        )

    def get_license_status(
        self,
        *,
        request_id: str,
        operation_id: str,
    ) -> LicenseStatusDto:
        return self._license_service.get_status(
            request_id=request_id,
            operation_id=operation_id,
        )

    def activate_license(
        self,
        *,
        license_key: str,
        machine_code: str | None,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> LicenseStatusDto:
        return self._license_service.activate(
            license_key=license_key,
            machine_code=machine_code,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    def initialize_directories(
        self,
        *,
        workspace_root_ref: str | None,
        idempotency_key: str,
    ) -> DirectoryReportDto:
        return self._directory_service.initialize(
            workspace_root_ref=workspace_root_ref,
            idempotency_key=idempotency_key,
        )

    async def accept_self_checks(
        self,
        *,
        checks: list[SelfCheckKey],
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        if self._task_submitter is None:
            raise DomainError(
                ErrorCode.RUNTIME_NOT_READY,
                "Runtime 自检任务服务尚未就绪",
                status_code=503,
                loggable=True,
                log_context={"operation": "bootstrap.self_check"},
            )

        record = await self._task_submitter.submit_system_task(
            task_type=SELF_CHECK_TASK_TYPE,
            payload={"checks": list(dict.fromkeys(checks))},
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )
        if record.status != TaskStatus.QUEUED:
            raise DomainError(
                ErrorCode.SELF_CHECK_ALREADY_RUNNING,
                "系统自检正在运行",
                status_code=409,
                meta={"taskId": record.id},
            )
        return TaskAcceptedDto(
            taskId=record.id,
            scope="system",
            accountId=None,
            taskType=record.task_type,
            status="queued",
            cancellable=record.cancellable,
            createdAt=record.created_at,
        )

    def _get_media_tools_status(self) -> MediaToolsStatusDto:
        try:
            ffprobe = resolve_ffprobe()
            ffmpeg = resolve_ffmpeg()
        except Exception:
            log.exception("读取 Bootstrap 媒体工具状态失败")
            return MediaToolsStatusDto(
                status="failed",
                issues=["MEDIA_TOOLS_CHECK_FAILED"],
            )

        issues = [
            code
            for code in (
                _normalize_issue_code(ffprobe.error_code),
                _normalize_issue_code(ffmpeg.error_code),
            )
            if code is not None
        ]
        return MediaToolsStatusDto(
            status="ready" if not issues else "attention",
            issues=issues,
        )


def _build_blocking_issues(
    *,
    license_status: LicenseStatusDto,
    directories: DirectoryReportDto,
) -> list[BootstrapBlockingIssueDto]:
    issues: list[BootstrapBlockingIssueDto] = []
    if license_status.blockingIssue is not None:
        issues.append(
            BootstrapBlockingIssueDto(
                code=license_status.blockingIssue.code,
                message=license_status.blockingIssue.message,
                logId=None,
            )
        )
    if directories.status != "ready":
        issues.extend(
            BootstrapBlockingIssueDto(
                code=issue.code,
                message=issue.message,
                logId=issue.logId,
            )
            for issue in directories.issues
        )
    return issues


def _normalize_issue_code(error_code: str | None) -> str | None:
    if error_code is None:
        return None
    return error_code.replace(".", "_").replace("-", "_").upper()
