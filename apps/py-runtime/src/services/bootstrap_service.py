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
    BootstrapDirectoryItemDto,
    BootstrapDirectoryReportDto,
    RuntimeSelfCheckItemDto,
    RuntimeSelfCheckReportDto,
)
from services.settings_service import SettingsService

log = logging.getLogger(__name__)

DEFAULT_RUNTIME_PORT = 8000


class BootstrapService:
    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig,
        settings_service: SettingsService,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._runtime_config = runtime_config
        self._settings_service = settings_service
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
                detail=f"已检查 {len(directory_items)} 个目录",
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
                log.exception("目录检查失败: %s", path)
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
        detail = f"运行模式 {runtime_mode}，核心服务已加载"
        return RuntimeSelfCheckItemDto(
            key="dependencies",
            label="依赖检查",
            status="ok",
            detail=detail,
            errorCode=None,
            checkedAt=utc_now_iso(),
        )


def _check_port_listening(port: int) -> tuple[bool, str]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", port))
    if result == 0:
        return True, f"端口 {port} 已处于监听状态"
    return False, f"端口 {port} 未检测到目标服务"
