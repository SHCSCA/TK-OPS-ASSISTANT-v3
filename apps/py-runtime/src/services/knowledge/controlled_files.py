from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from errors import DomainError, ErrorCode
from services.execution_environments.workspace_root_resolver import (
    WorkspaceRootResolutionError,
    WorkspaceRootResolver,
)
from services.knowledge.ports import (
    ControlledFileExpectation,
    ControlledFileGrant,
    ResolvedKnowledgeContent,
)
from services.knowledge.source_validation import require_controlled_file_ref

log = logging.getLogger(__name__)

_MAX_REGISTRY_BYTES = 2 * 1024 * 1024
_ROOT_REF_PATTERN = re.compile(r"^wr_[0-9a-f]{32}$")
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class _ResolvedGrant:
    grant: ControlledFileGrant
    path: Path


class RegistryControlledFileResolver:
    """按账号和 rootRef 二次验证 Tauri 私有文件授权。"""

    def __init__(
        self,
        registry_path: Path,
        *,
        workspace_roots: WorkspaceRootResolver,
    ) -> None:
        self._registry_path = registry_path.resolve()
        self._workspace_roots = workspace_roots

    def describe(
        self,
        account_id: str,
        reference: str,
        *,
        max_bytes: int,
    ) -> ControlledFileGrant:
        return self._resolve(
            account_id,
            require_controlled_file_ref(reference),
            max_bytes=max_bytes,
        ).grant

    def read_bytes(
        self,
        account_id: str,
        reference: str,
        *,
        max_bytes: int,
        expected: ControlledFileExpectation | None = None,
    ) -> ResolvedKnowledgeContent:
        before = self._resolve(
            account_id,
            require_controlled_file_ref(reference),
            max_bytes=max_bytes,
        )
        _require_expected(before.grant, expected)
        try:
            with before.path.open("rb") as file:
                data = file.read(max_bytes + 1)
        except OSError as exc:
            raise _changed_error("文件已不可读，请重新授权并重试") from exc
        if len(data) > max_bytes:
            raise _invalid_size_error()
        after = self._resolve(
            account_id,
            reference,
            max_bytes=max_bytes,
        )
        _require_expected(after.grant, expected)
        if before.grant.fingerprint != after.grant.fingerprint:
            raise _changed_error("文件在读取期间发生变化，请重新授权并重试")
        return ResolvedKnowledgeContent(
            data=data,
            media_type=after.grant.media_type,
            controlled_file=after.grant,
        )

    def _resolve(
        self,
        account_id: str,
        reference: str,
        *,
        max_bytes: int,
    ) -> _ResolvedGrant:
        record = self._find_owned_record(account_id, reference)
        if record["status"] != "active":
            raise DomainError(
                ErrorCode.CONTROLLED_FILE_REF_INVALID,
                "文件授权已撤销，请重新选择文件",
                status_code=409,
            )
        try:
            root = self._workspace_roots.resolve(
                account_id=account_id,
                root_ref=record["rootRef"],
            )
        except WorkspaceRootResolutionError as exc:
            raise DomainError(
                _workspace_error_code(exc.error_code),
                str(exc),
                status_code=409,
            ) from exc
        if root.revision != record["rootRevision"]:
            raise _changed_error("工作目录授权已变化，请重新选择文件")
        path = _resolve_record_path(record, root.path)
        metadata = _read_metadata(path)
        if metadata.st_size <= 0 or metadata.st_size > max_bytes:
            raise _invalid_size_error()
        current_mtime = metadata.st_mtime_ns // 1_000_000
        identity = _file_identity(record["rootRef"], record["relativePath"])
        if (
            metadata.st_size != record["size"]
            or current_mtime != record["mtime"]
            or identity != record["fileIdentity"]
        ):
            raise _changed_error("文件内容或身份已变化，请重新授权并重试")
        fingerprint = _fingerprint(
            identity,
            byte_size=metadata.st_size,
            mtime=current_mtime,
        )
        return _ResolvedGrant(
            grant=ControlledFileGrant(
                file_ref=reference,
                root_ref=record["rootRef"],
                root_revision=record["rootRevision"],
                file_revision=record["revision"],
                fingerprint=fingerprint,
                display_name=Path(record["relativePath"]).name,
                kind=record["kind"],
                media_type=record["mediaType"],
                byte_size=metadata.st_size,
            ),
            path=path,
        )

    def _find_owned_record(
        self,
        account_id: str,
        reference: str,
    ) -> dict[str, Any]:
        payload = self._load_registry()
        record = next(
            (
                item
                for item in payload["files"]
                if item["fileRef"] == reference
                and item["accountId"] == account_id
            ),
            None,
        )
        if record is None:
            raise DomainError(
                ErrorCode.CONTROLLED_FILE_REF_INVALID,
                "文件授权不存在或不属于当前账号",
                status_code=404,
            )
        return record

    def _load_registry(self) -> dict[str, Any]:
        try:
            return _read_registry(self._registry_path)
        except (OSError, ValueError, json.JSONDecodeError):
            try:
                return _read_registry(
                    self._registry_path.with_suffix(".json.bak")
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                log.exception(
                    "受控文件注册表不可用",
                    extra={"error_code": "CONTROLLED_FILE_REGISTRY_INVALID"},
                )
                raise DomainError(
                    ErrorCode.CONTROLLED_FILE_REF_INVALID,
                    "受控文件注册表不可用，请重新启动桌面应用",
                    status_code=503,
                    loggable=True,
                ) from exc


def _read_registry(path: Path) -> dict[str, Any]:
    metadata = path.stat()
    if not path.is_file() or metadata.st_size > _MAX_REGISTRY_BYTES:
        raise ValueError("受控文件注册表文件无效")
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return _validate_registry(payload)


def _validate_registry(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {
        "schemaVersion",
        "revision",
        "files",
    }:
        raise ValueError("受控文件注册表结构无效")
    if payload["schemaVersion"] != 1:
        raise ValueError("受控文件注册表版本不受支持")
    if (
        not isinstance(payload["revision"], int)
        or payload["revision"] < 0
        or not isinstance(payload["files"], list)
    ):
        raise ValueError("受控文件注册表修订无效")
    files = [_validate_record(item) for item in payload["files"]]
    refs = [item["fileRef"] for item in files]
    if len(refs) != len(set(refs)):
        raise ValueError("受控文件引用重复")
    return {**payload, "files": files}


def _validate_record(value: Any) -> dict[str, Any]:
    required = {
        "accountId",
        "canonicalPath",
        "fileIdentity",
        "fileRef",
        "kind",
        "mediaType",
        "mtime",
        "relativePath",
        "revision",
        "rootRef",
        "rootRevision",
        "size",
        "status",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("受控文件记录结构无效")
    string_fields = (
        "accountId",
        "canonicalPath",
        "fileIdentity",
        "fileRef",
        "kind",
        "mediaType",
        "relativePath",
        "rootRef",
        "status",
    )
    if any(
        not isinstance(value[field], str) or not value[field].strip()
        for field in string_fields
    ):
        raise ValueError("受控文件记录字符串字段无效")
    if (
        not Path(value["canonicalPath"]).is_absolute()
        or Path(value["relativePath"]).is_absolute()
        or ".." in Path(value["relativePath"]).parts
        or not _ROOT_REF_PATTERN.fullmatch(value["rootRef"])
        or not _HASH_PATTERN.fullmatch(value["fileIdentity"])
        or value["status"] not in {"active", "revoked"}
        or value["kind"]
        not in {"document", "image", "video", "audio", "text"}
        or any(
            isinstance(value[field], bool)
            or not isinstance(value[field], int)
            or value[field] < 1
            for field in ("revision", "rootRevision", "size")
        )
        or isinstance(value["mtime"], bool)
        or not isinstance(value["mtime"], int)
        or value["mtime"] < 0
    ):
        raise ValueError("受控文件记录字段无效")
    try:
        require_controlled_file_ref(value["fileRef"])
    except DomainError as exc:
        raise ValueError("受控文件引用格式无效") from exc
    return dict(value)


def _resolve_record_path(record: dict[str, Any], root: Path) -> Path:
    relative = Path(record["relativePath"])
    if relative.is_absolute() or ".." in relative.parts:
        raise _changed_error("文件相对路径无效，请重新授权")
    candidate = root / relative
    if _contains_link_or_reparse(candidate, root):
        raise _changed_error("文件路径包含链接或重解析点，请重新授权")
    try:
        path = candidate.resolve(strict=True)
        stored = Path(record["canonicalPath"]).resolve(strict=True)
    except OSError as exc:
        raise _changed_error("文件已移动或删除，请重新授权") from exc
    if (
        path != stored
        or path == root
        or root not in path.parents
        or path.is_symlink()
        or not path.is_file()
    ):
        raise _changed_error("文件已超出受控工作目录，请重新授权")
    return path


def _contains_link_or_reparse(candidate: Path, root: Path) -> bool:
    current = root
    try:
        for part in candidate.relative_to(root).parts:
            current = current / part
            metadata = current.stat(follow_symlinks=False)
            if current.is_symlink() or (
                getattr(metadata, "st_file_attributes", 0) & 0x400
            ):
                return True
    except OSError as exc:
        raise _changed_error("文件路径已不可用，请重新授权") from exc
    return False


def _read_metadata(path: Path) -> os.stat_result:
    try:
        return path.stat(follow_symlinks=False)
    except OSError as exc:
        raise _changed_error("文件已不可用，请重新授权") from exc


def _file_identity(root_ref: str, relative_path: str) -> str:
    return hashlib.sha256(
        f"{root_ref}\0{relative_path}".encode("utf-8")
    ).hexdigest()


def _fingerprint(identity: str, *, byte_size: int, mtime: int) -> str:
    return hashlib.sha256(
        f"{identity}\0{byte_size}\0{mtime}".encode("utf-8")
    ).hexdigest()


def _require_expected(
    grant: ControlledFileGrant,
    expected: ControlledFileExpectation | None,
) -> None:
    if expected is None:
        return
    if (
        grant.file_ref != expected.file_ref
        or grant.root_ref != expected.root_ref
        or grant.root_revision != expected.root_revision
        or grant.file_revision != expected.file_revision
        or grant.fingerprint != expected.fingerprint
    ):
        raise _changed_error("文件授权快照已变化，请重新授权并重试")


def _workspace_error_code(value: str) -> ErrorCode:
    try:
        return ErrorCode(value)
    except ValueError:
        return ErrorCode.CONTROLLED_FILE_REF_INVALID


def _invalid_size_error() -> DomainError:
    return DomainError(
        ErrorCode.KNOWLEDGE_INDEX_FAILED,
        "文件为空或超过配置总线允许的大小",
        status_code=422,
    )


def _changed_error(message: str) -> DomainError:
    return DomainError(
        ErrorCode.CONTROLLED_FILE_CHANGED,
        message,
        status_code=409,
        meta={"repairAction": "reauthorize_and_retry"},
    )
