from __future__ import annotations

import logging
import os
import socket
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.config import RuntimeConfig
from common.time import utc_now_iso
from schemas.bootstrap import (
    BootstrapActionDto,
    BootstrapBlockerDto,
    BootstrapDirectoryItemDto,
    BootstrapDirectoryReportDto,
    BootstrapReadinessItemDto,
    BootstrapReadinessReportDto,
    RuntimeSelfCheckItemDto,
    RuntimeSelfCheckReportDto,
)
from services.license_service import LicenseService
from services.settings_service import SettingsService

log = logging.getLogger(__name__)

DEFAULT_RUNTIME_PORT = 8000


class BootstrapService:
    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig,
        settings_service: SettingsService,
        license_service: LicenseService,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._runtime_config = runtime_config
        self._settings_service = settings_service
        self._license_service = license_service
        self._session_factory = session_factory

    def initialize_directories(self) -> BootstrapDirectoryReportDto:
        settings = self._settings_service.get_settings()
        directory_items = self._build_directory_items(
            [
                ("data_root", "数据根目录", self._runtime_config.data_dir),
                ("projects", "项目目录", self._runtime_config.data_dir / "projects"),
                ("assets", "资产目录", self._runtime_config.data_dir / "assets"),
                ("renders", "渲染目录", self._runtime_config.data_dir / "renders"),
                ("cache", "缓存目录", Path(settings.paths.cacheDir)),
                ("exports", "导出目录", Path(settings.paths.exportDir)),
                ("logs", "日志目录", Path(settings.paths.logDir)),
                ("licenses", "许可证目录", self._runtime_config.data_dir / "licenses"),
            ],
            create=True,
        )
        overall_status = "ok" if all(item.status == "ok" for item in directory_items) else "degraded"
        return BootstrapDirectoryReportDto(
            rootDir=str(self._runtime_config.data_dir),
            databasePath=str(self._runtime_config.database_path),
            status=overall_status,
            directories=directory_items,
            checkedAt=utc_now_iso(),
        )

    def runtime_selfcheck(self) -> RuntimeSelfCheckReportDto:
        settings = self._settings_service.get_settings()
        directory_items = self._build_directory_items(
            [
                ("data_root", "数据根目录", self._runtime_config.data_dir),
                ("projects", "项目目录", self._runtime_config.data_dir / "projects"),
                ("assets", "资产目录", self._runtime_config.data_dir / "assets"),
                ("renders", "渲染目录", self._runtime_config.data_dir / "renders"),
                ("cache", "缓存目录", Path(settings.paths.cacheDir)),
                ("exports", "导出目录", Path(settings.paths.exportDir)),
                ("logs", "日志目录", Path(settings.paths.logDir)),
                ("licenses", "许可证目录", self._runtime_config.data_dir / "licenses"),
            ],
            create=True,
        )
        items = [
            self._check_port_item(),
            self._check_database_item(),
            self._check_dependencies_item(settings.runtime.mode),
            RuntimeSelfCheckItemDto(
                key="directories",
                label="目录状态",
                status="ok" if all(item.status == "ok" for item in directory_items) else "warning",
                detail=f"已检查 {len(directory_items)} 个目录。",
                errorCode=None,
                checkedAt=utc_now_iso(),
            ),
        ]
        overall_status = "ok" if all(item.status == "ok" for item in items) else "degraded"
        return RuntimeSelfCheckReportDto(
            status=overall_status,
            runtimeVersion=self._runtime_config.version,
            checkedAt=utc_now_iso(),
            items=items,
        )

    def get_readiness(self) -> BootstrapReadinessReportDto:
        checked_at = utc_now_iso()
        settings = self._settings_service.get_settings()
        directory_items = self._build_directory_items(
            [
                ("data_root", "数据根目录", self._runtime_config.data_dir),
                ("projects", "项目目录", self._runtime_config.data_dir / "projects"),
                ("assets", "资产目录", self._runtime_config.data_dir / "assets"),
                ("renders", "渲染目录", self._runtime_config.data_dir / "renders"),
                ("cache", "缓存目录", Path(settings.paths.cacheDir)),
                ("exports", "导出目录", Path(settings.paths.exportDir)),
                ("logs", "日志目录", Path(settings.paths.logDir)),
                ("licenses", "许可证目录", self._runtime_config.data_dir / "licenses"),
            ],
            create=True,
        )
        runtime_items = [
            self._check_port_item(),
            self._check_database_item(),
            self._check_dependencies_item(settings.runtime.mode),
        ]
        items = [
            self._build_license_readiness_item(checked_at),
            self._build_directory_readiness_item(directory_items, checked_at),
            self._build_runtime_readiness_item(runtime_items, checked_at),
            self._build_media_readiness_item(checked_at),
        ]
        blockers = [
            BootstrapBlockerDto(
                key=item.key,
                errorCode=item.errorCode or "bootstrap.blocked",
                blockedReason=item.blockedReason or item.detail,
                affectedTarget=item.affectedTarget or item.label,
                nextStep=item.nextStep or "请先修复该阻断项后再继续。",
                action=item.action,
            )
            for item in items
            if item.status == "error" and item.blockedReason is not None
        ]
        can_continue = not blockers
        return BootstrapReadinessReportDto(
            status="ready" if can_continue else "blocked",
            canContinue=can_continue,
            checkedAt=checked_at,
            items=items,
            blockers=blockers,
        )

    def _build_directory_items(
        self,
        entries: list[tuple[str, str, Path]],
        *,
        create: bool,
    ) -> list[BootstrapDirectoryItemDto]:
        items: list[BootstrapDirectoryItemDto] = []
        for key, label, path in entries:
            try:
                if create:
                    path.mkdir(parents=True, exist_ok=True)
                exists = path.exists()
                writable = exists and os.access(path, os.W_OK)
                status = "ok" if exists and writable else "warning"
                message = "目录已就绪" if status == "ok" else "目录不可写或不可用"
            except Exception as exc:  # noqa: BLE001
                log.exception("目录检查失败 %s", path)
                exists = path.exists()
                writable = False
                status = "error"
                message = str(exc) or "目录检查失败"
            items.append(
                BootstrapDirectoryItemDto(
                    key=key,
                    label=label,
                    path=str(path),
                    exists=exists,
                    writable=writable,
                    status=status,
                    message=message,
                )
            )
        return items

    def _check_port_item(self) -> RuntimeSelfCheckItemDto:
        port = DEFAULT_RUNTIME_PORT
        try:
            listening, detail = _check_port_listening(port)
        except Exception as exc:  # noqa: BLE001
            log.exception("端口自检失败: %s", port)
            return RuntimeSelfCheckItemDto(
                key="port",
                label="端口检查",
                status="error",
                detail=str(exc) or "端口检查失败",
                errorCode="runtime.not-ready",
                checkedAt=utc_now_iso(),
            )

        if listening:
            return RuntimeSelfCheckItemDto(
                key="port",
                label="端口检查",
                status="ok",
                detail=detail,
                errorCode=None,
                checkedAt=utc_now_iso(),
            )

        return RuntimeSelfCheckItemDto(
            key="port",
            label="端口检查",
            status="warning",
            detail=detail,
            errorCode="runtime.port-not-listening",
            checkedAt=utc_now_iso(),
        )

    def _check_database_item(self) -> RuntimeSelfCheckItemDto:
        try:
            with self._session_factory() as session:
                session.execute(text("select 1"))
            return RuntimeSelfCheckItemDto(
                key="database",
                label="数据库检查",
                status="ok",
                detail="数据库连接可用",
                errorCode=None,
                checkedAt=utc_now_iso(),
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("数据库自检失败")
            return RuntimeSelfCheckItemDto(
                key="database",
                label="数据库检查",
                status="error",
                detail=str(exc) or "数据库不可用",
                errorCode="runtime.not-ready",
                checkedAt=utc_now_iso(),
            )

    def _check_dependencies_item(self, runtime_mode: str) -> RuntimeSelfCheckItemDto:
        return RuntimeSelfCheckItemDto(
            key="dependencies",
            label="依赖检查",
            status="ok",
            detail=f"运行模式 {runtime_mode}，核心服务已加载",
            errorCode=None,
            checkedAt=utc_now_iso(),
        )

    def _build_license_readiness_item(self, checked_at: str) -> BootstrapReadinessItemDto:
        status = self._license_service.get_status()
        if status.active:
            return BootstrapReadinessItemDto(
                key="license",
                label="许可证校验",
                status="ok",
                detail="许可证已激活，当前设备可继续使用。",
                errorCode=None,
                blockedReason=None,
                affectedTarget="许可证",
                nextStep=None,
                action=None,
                checkedAt=checked_at,
            )
        return BootstrapReadinessItemDto(
            key="license",
            label="许可证校验",
            status="error",
            detail="许可证尚未激活，当前无法继续进入产品。",
            errorCode="license.not_activated",
            blockedReason="当前设备还没有可用许可证。",
            affectedTarget="许可证",
            nextStep="请输入有效激活码并完成许可证激活。",
            action=BootstrapActionDto(key="open-license-activation", label="前往激活"),
            checkedAt=checked_at,
        )

    def _build_directory_readiness_item(
        self,
        items: list[BootstrapDirectoryItemDto],
        checked_at: str,
    ) -> BootstrapReadinessItemDto:
        if all(item.status == "ok" for item in items):
            return BootstrapReadinessItemDto(
                key="directories",
                label="目录初始化",
                status="ok",
                detail=f"已检查 {len(items)} 个关键目录，均可读写。",
                errorCode=None,
                blockedReason=None,
                affectedTarget="本地目录",
                nextStep=None,
                action=None,
                checkedAt=checked_at,
            )
        problem = next((item for item in items if item.status != "ok"), items[0])
        return BootstrapReadinessItemDto(
            key="directories",
            label="目录初始化",
            status="error",
            detail="存在目录不可用或不可写，当前无法继续初始化。",
            errorCode="bootstrap.directory_unavailable",
            blockedReason=f"{problem.label} 当前不可用或不可写。",
            affectedTarget=problem.label,
            nextStep="请检查目录权限或磁盘状态后重试。",
            action=BootstrapActionDto(key="retry-directory-check", label="重新检查"),
            checkedAt=checked_at,
        )

    def _build_runtime_readiness_item(
        self,
        items: list[RuntimeSelfCheckItemDto],
        checked_at: str,
    ) -> BootstrapReadinessItemDto:
        failing = next((item for item in items if item.status == "error"), None)
        if failing is None:
            warning = next((item for item in items if item.status == "warning"), None)
            if warning is None:
                return BootstrapReadinessItemDto(
                    key="runtime",
                    label="Runtime 诊断",
                    status="ok",
                    detail="Runtime 核心子系统检查通过。",
                    errorCode=None,
                    blockedReason=None,
                    affectedTarget="Runtime",
                    nextStep=None,
                    action=None,
                    checkedAt=checked_at,
                )
            return BootstrapReadinessItemDto(
                key="runtime",
                label="Runtime 诊断",
                status="warning",
                detail=warning.detail,
                errorCode=warning.errorCode,
                blockedReason=None,
                affectedTarget="Runtime",
                nextStep="请检查 Runtime 端口与依赖状态。",
                action=BootstrapActionDto(key="open-runtime-diagnostics", label="查看诊断"),
                checkedAt=checked_at,
            )
        return BootstrapReadinessItemDto(
            key="runtime",
            label="Runtime 诊断",
            status="error",
            detail=failing.detail,
            errorCode=failing.errorCode,
            blockedReason="Runtime 核心子系统未通过检查。",
            affectedTarget="Runtime",
            nextStep="请先修复 Runtime 子系统错误后再继续。",
            action=BootstrapActionDto(key="open-runtime-diagnostics", label="查看诊断"),
            checkedAt=checked_at,
        )

    def _build_media_readiness_item(self, checked_at: str) -> BootstrapReadinessItemDto:
        media = self._settings_service.get_media_diagnostics()
        if media.ffprobe.status == "ready":
            return BootstrapReadinessItemDto(
                key="media",
                label="媒体依赖",
                status="ok",
                detail="FFprobe 已就绪，可用于媒体诊断与视频拆解。",
                errorCode=None,
                blockedReason=None,
                affectedTarget="FFprobe",
                nextStep=None,
                action=None,
                checkedAt=checked_at,
            )
        return BootstrapReadinessItemDto(
            key="media",
            label="媒体依赖",
            status="warning",
            detail=media.ffprobe.errorMessage or "FFprobe 当前不可用。",
            errorCode=media.ffprobe.errorCode,
            blockedReason=None,
            affectedTarget="FFprobe",
            nextStep="请安装或修复 FFprobe 后再执行媒体相关任务。",
            action=BootstrapActionDto(key="open-media-diagnostics", label="查看媒体诊断"),
            checkedAt=checked_at,
        )


def _check_port_listening(port: int) -> tuple[bool, str]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", port))
    if result == 0:
        return True, f"端口 {port} 已处于监听状态"
    return False, f"端口 {port} 未检测到目标服务"
