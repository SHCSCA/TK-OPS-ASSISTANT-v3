from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from common.identifiers import is_stable_id
from errors import DomainError, ErrorCode

log = logging.getLogger(__name__)

_REF_PREFIX = "knowledge-content://"


@dataclass(frozen=True, slots=True)
class StoredKnowledgeContent:
    reference: str
    content_hash: str
    byte_size: int


@dataclass(frozen=True, slots=True)
class KnowledgeContentReconciliationReport:
    scanned_candidate_count: int
    protected_file_count: int
    removed_orphan_count: int


class KnowledgeContentStore:
    """在 Runtime 数据目录中保存账号隔离的内联知识正文。"""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def store_text(
        self,
        account_id: str,
        source_id: str,
        text: str,
    ) -> StoredKnowledgeContent:
        payload = text.encode("utf-8")
        destination = self._path(account_id, source_id)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(destination, payload)
        except OSError as exc:
            log.exception(
                "保存知识正文失败",
                extra={
                    "account_id": account_id,
                    "resource_type": "knowledge_source",
                    "resource_id": source_id,
                },
            )
            raise DomainError(
                ErrorCode.KNOWLEDGE_SOURCE_INVALID,
                "知识正文保存失败，请检查工作目录后重试",
                status_code=500,
                loggable=True,
            ) from exc
        return StoredKnowledgeContent(
            reference=f"{_REF_PREFIX}{account_id}/{source_id}",
            content_hash=hashlib.sha256(payload).hexdigest(),
            byte_size=len(payload),
        )

    def read_bytes(self, account_id: str, reference: str) -> bytes:
        source_id = self._source_id_from_ref(account_id, reference)
        path = self._path(account_id, source_id)
        try:
            return path.read_bytes()
        except OSError as exc:
            log.exception(
                "读取知识正文失败",
                extra={
                    "account_id": account_id,
                    "resource_type": "knowledge_source",
                    "resource_id": source_id,
                },
            )
            raise DomainError(
                ErrorCode.KNOWLEDGE_INDEX_FAILED,
                "知识正文不可读，请重新添加来源",
                status_code=500,
                loggable=True,
            ) from exc

    def remove(self, account_id: str, reference: str) -> None:
        source_id = self._source_id_from_ref(account_id, reference)
        path = self._path(account_id, source_id)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            log.exception(
                "清理未提交的知识正文失败",
                extra={
                    "account_id": account_id,
                    "resource_type": "knowledge_source",
                    "resource_id": source_id,
                },
            )

    def reconcile_orphaned_text_files(
        self,
        referenced_sources: Collection[tuple[str, str]],
    ) -> KnowledgeContentReconciliationReport:
        """只清理 Runtime 生成且数据库没有引用的内联正文文件。"""
        try:
            protected = {
                self._path(
                    account_id,
                    self._source_id_from_ref(account_id, reference),
                )
                for account_id, reference in referenced_sources
            }
            candidates = set(self._candidate_text_paths())
            orphaned = candidates - protected
            for path in sorted(orphaned):
                path.unlink()
        except Exception as exc:
            log.exception(
                "启动时对账知识正文孤儿文件失败",
                extra={
                    "resource_type": "knowledge_content",
                    "operation": "knowledge.reconcile_content_files",
                },
            )
            raise RuntimeError(
                "知识正文孤儿文件对账失败，Runtime 已阻止进入就绪状态"
            ) from exc
        return KnowledgeContentReconciliationReport(
            scanned_candidate_count=len(candidates),
            protected_file_count=len(candidates & protected),
            removed_orphan_count=len(orphaned),
        )

    def _path(self, account_id: str, source_id: str) -> Path:
        _require_stable_id(account_id, "账号")
        _require_stable_id(source_id, "知识来源")
        path = (
            self._root
            / account_id
            / "knowledge"
            / f"{source_id}.txt"
        ).resolve()
        if self._root not in path.parents:
            raise DomainError(
                ErrorCode.CONTROLLED_FILE_REF_INVALID,
                "知识正文引用超出受控目录",
                status_code=422,
            )
        return path

    def _candidate_text_paths(self) -> tuple[Path, ...]:
        if not self._root.exists():
            return ()
        if not self._root.is_dir():
            raise OSError("知识正文根路径不是目录")
        candidates: list[Path] = []
        with os.scandir(self._root) as account_entries:
            for account_entry in account_entries:
                if (
                    not is_stable_id(account_entry.name)
                    or not account_entry.is_dir(follow_symlinks=False)
                ):
                    continue
                knowledge_dir = Path(account_entry.path) / "knowledge"
                if (
                    knowledge_dir.is_symlink()
                    or not knowledge_dir.is_dir()
                ):
                    continue
                with os.scandir(knowledge_dir) as content_entries:
                    for content_entry in content_entries:
                        if not content_entry.is_file(follow_symlinks=False):
                            continue
                        source_id = _source_id_from_filename(
                            content_entry.name
                        )
                        if source_id is None:
                            continue
                        candidate = Path(content_entry.path).resolve(
                            strict=True
                        )
                        if (
                            candidate.parent != knowledge_dir.resolve()
                            or self._root not in candidate.parents
                        ):
                            raise OSError("知识正文候选文件超出受控目录")
                        candidates.append(candidate)
        return tuple(candidates)

    @staticmethod
    def _atomic_write(destination: Path, payload: bytes) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_path = Path(handle.name)
            os.replace(temporary_path, destination)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _source_id_from_ref(account_id: str, reference: str) -> str:
        prefix = f"{_REF_PREFIX}{account_id}/"
        if not reference.startswith(prefix):
            raise DomainError(
                ErrorCode.CONTROLLED_FILE_REF_INVALID,
                "知识正文引用不属于当前账号",
                status_code=422,
            )
        source_id = reference.removeprefix(prefix)
        _require_stable_id(source_id, "知识来源")
        return source_id


def _require_stable_id(value: str, label: str) -> None:
    if not is_stable_id(value):
        raise DomainError(
            ErrorCode.CONTROLLED_FILE_REF_INVALID,
            f"{label}引用格式无效",
            status_code=422,
        )


def _source_id_from_filename(filename: str) -> str | None:
    if not filename.endswith(".txt"):
        return None
    source_id = filename[:-4]
    return source_id if is_stable_id(source_id) else None
