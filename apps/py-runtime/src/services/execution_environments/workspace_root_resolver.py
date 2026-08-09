from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_MAX_REGISTRY_BYTES = 1024 * 1024
_ROOT_REF_PATTERN = re.compile(r"^wr_[0-9a-f]{32}$")


class WorkspaceRootResolutionError(RuntimeError):
    """工作目录引用不可安全解析。"""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True, slots=True)
class WorkspaceRootResolution:
    account_id: str
    display_name: str
    path: Path
    registry_revision: int
    revision: int
    root_ref: str


@dataclass(frozen=True, slots=True)
class _RegistrySnapshot:
    file_mtime_ns: int
    registry_revision: int
    roots: tuple[dict[str, Any], ...]


class WorkspaceRootResolver:
    """只读解析由 Tauri 管理的账号工作目录引用。"""

    def __init__(self, registry_path: Path) -> None:
        self._registry_path = registry_path.resolve()
        self._snapshot: _RegistrySnapshot | None = None
        self._lock = threading.RLock()

    def resolve(
        self,
        *,
        account_id: str,
        root_ref: str,
    ) -> WorkspaceRootResolution:
        if not account_id.strip() or not _ROOT_REF_PATTERN.fullmatch(root_ref):
            raise WorkspaceRootResolutionError(
                "WORKSPACE_ROOT_REFERENCE_INVALID",
                "工作目录引用无效，请重新选择目录。",
            )
        snapshot = self._load_snapshot()
        record = next(
            (
                item
                for item in snapshot.roots
                if item["rootRef"] == root_ref
                and item["accountId"] == account_id
            ),
            None,
        )
        if record is None:
            raise WorkspaceRootResolutionError(
                "WORKSPACE_ROOT_NOT_FOUND",
                "工作目录授权不存在或不属于当前账号。",
            )
        if record["status"] != "active":
            raise WorkspaceRootResolutionError(
                "WORKSPACE_ROOT_REVOKED",
                "工作目录授权已撤销，请重新授权。",
            )
        canonical = self._resolve_directory(record["canonicalPath"])
        return WorkspaceRootResolution(
            account_id=account_id,
            display_name=record["displayName"],
            path=canonical,
            registry_revision=snapshot.registry_revision,
            revision=record["revision"],
            root_ref=root_ref,
        )

    def invalidate(self) -> None:
        with self._lock:
            self._snapshot = None

    def _load_snapshot(self) -> _RegistrySnapshot:
        with self._lock:
            try:
                mtime_ns = self._registry_path.stat().st_mtime_ns
            except OSError as exc:
                return self._fallback_or_raise(exc)
            if self._snapshot and self._snapshot.file_mtime_ns == mtime_ns:
                return self._snapshot
            try:
                snapshot = self._read_snapshot(self._registry_path, mtime_ns)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                log.exception(
                    "工作目录主注册表解析失败，尝试使用已验证快照",
                    extra={"error_code": "WORKSPACE_ROOT_REGISTRY_INVALID"},
                )
                return self._fallback_or_raise(exc)
            self._snapshot = snapshot
            return snapshot

    def _fallback_or_raise(self, cause: BaseException) -> _RegistrySnapshot:
        if self._snapshot is not None:
            return self._snapshot
        backup_path = self._registry_path.with_suffix(".json.bak")
        try:
            snapshot = self._read_snapshot(
                backup_path,
                backup_path.stat().st_mtime_ns,
            )
        except (OSError, ValueError, json.JSONDecodeError) as backup_error:
            raise WorkspaceRootResolutionError(
                "WORKSPACE_ROOT_REGISTRY_UNAVAILABLE",
                "工作目录注册表不可用，请重新启动桌面应用。",
            ) from backup_error
        log.warning(
            "工作目录注册表已回退到备份快照",
            extra={
                "error_code": "WORKSPACE_ROOT_REGISTRY_FALLBACK",
                "cause_type": type(cause).__name__,
            },
        )
        self._snapshot = snapshot
        return snapshot

    def _read_snapshot(self, path: Path, mtime_ns: int) -> _RegistrySnapshot:
        metadata = path.stat()
        if not path.is_file() or metadata.st_size > _MAX_REGISTRY_BYTES:
            raise ValueError("工作目录注册表文件无效")
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return _validate_registry(payload, mtime_ns)

    @staticmethod
    def _resolve_directory(raw_path: str) -> Path:
        try:
            canonical = Path(raw_path).resolve(strict=True)
        except OSError as exc:
            raise WorkspaceRootResolutionError(
                "WORKSPACE_ROOT_EXPIRED",
                "工作目录已失效，请重新授权。",
            ) from exc
        if not canonical.is_dir() or not os.access(canonical, os.W_OK):
            raise WorkspaceRootResolutionError(
                "WORKSPACE_ROOT_NOT_WRITABLE",
                "工作目录不可写，请检查权限或重新授权。",
            )
        return canonical


def _validate_registry(payload: Any, mtime_ns: int) -> _RegistrySnapshot:
    if not isinstance(payload, dict) or set(payload) != {
        "schemaVersion",
        "revision",
        "roots",
    }:
        raise ValueError("工作目录注册表结构无效")
    if payload["schemaVersion"] != 1:
        raise ValueError("工作目录注册表版本不受支持")
    revision = payload["revision"]
    roots = payload["roots"]
    if not isinstance(revision, int) or revision < 0 or not isinstance(roots, list):
        raise ValueError("工作目录注册表修订无效")
    validated = tuple(_validate_record(item) for item in roots)
    root_refs = [item["rootRef"] for item in validated]
    if len(root_refs) != len(set(root_refs)):
        raise ValueError("工作目录引用重复")
    active_paths = [
        os.path.normcase(item["canonicalPath"])
        for item in validated
        if item["status"] == "active"
    ]
    if len(active_paths) != len(set(active_paths)):
        raise ValueError("活动工作目录重复")
    return _RegistrySnapshot(
        file_mtime_ns=mtime_ns,
        registry_revision=revision,
        roots=validated,
    )


def _validate_record(value: Any) -> dict[str, Any]:
    required = {
        "accountId",
        "canonicalPath",
        "createdAt",
        "displayName",
        "revision",
        "rootRef",
        "status",
        "updatedAt",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("工作目录记录结构无效")
    if (
        not isinstance(value["accountId"], str)
        or not value["accountId"].strip()
        or not isinstance(value["canonicalPath"], str)
        or not Path(value["canonicalPath"]).is_absolute()
        or not isinstance(value["displayName"], str)
        or not value["displayName"].strip()
        or not isinstance(value["revision"], int)
        or value["revision"] < 1
        or not isinstance(value["rootRef"], str)
        or not _ROOT_REF_PATTERN.fullmatch(value["rootRef"])
        or value["status"] not in {"active", "revoked"}
        or not isinstance(value["createdAt"], str)
        or not isinstance(value["updatedAt"], str)
    ):
        raise ValueError("工作目录记录字段无效")
    return dict(value)
