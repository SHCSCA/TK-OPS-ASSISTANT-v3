from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from common.identifiers import is_stable_id
from errors import DomainError, ErrorCode

log = logging.getLogger(__name__)

_REF_PREFIX = "knowledge-chunk://"


@dataclass(frozen=True, slots=True)
class StoredKnowledgeChunk:
    ordinal: int
    content_ref: str
    content_hash: str
    token_count: int
    extractor_version: int


class KnowledgeChunkStore:
    """保存由来源抽取的账号隔离文本块，不复制原始文件。"""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def store(
        self,
        account_id: str,
        source_id: str,
        source_revision: int,
        *,
        ordinal: int,
        text: str,
        token_count: int,
        extractor_version: int,
    ) -> StoredKnowledgeChunk:
        payload = text.encode("utf-8")
        destination = self._path(
            account_id,
            source_id,
            source_revision,
            ordinal,
        )
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(destination, payload)
        except OSError as exc:
            log.exception(
                "保存知识派生文本块失败",
                extra={
                    "account_id": account_id,
                    "resource_type": "knowledge_source",
                    "resource_id": source_id,
                    "source_revision": source_revision,
                    "ordinal": ordinal,
                },
            )
            raise DomainError(
                ErrorCode.KNOWLEDGE_INDEX_FAILED,
                "知识派生索引保存失败，请查看诊断日志后重试",
                status_code=500,
                loggable=True,
            ) from exc
        return StoredKnowledgeChunk(
            ordinal=ordinal,
            content_ref=(
                f"{_REF_PREFIX}{account_id}/{source_id}/"
                f"{source_revision}/{ordinal}"
            ),
            content_hash=hashlib.sha256(payload).hexdigest(),
            token_count=token_count,
            extractor_version=extractor_version,
        )

    def remove(self, account_id: str, reference: str) -> None:
        try:
            self._path_from_ref(account_id, reference).unlink(missing_ok=True)
        except (DomainError, OSError):
            log.exception(
                "清理未提交的知识派生文本块失败",
                extra={
                    "account_id": account_id,
                    "resource_type": "knowledge_chunk",
                },
            )

    def read_text(self, account_id: str, reference: str) -> str:
        try:
            return self._path_from_ref(account_id, reference).read_text(
                encoding="utf-8"
            )
        except OSError as exc:
            raise DomainError(
                ErrorCode.KNOWLEDGE_INDEX_FAILED,
                "知识派生索引不可读，请重新建立索引",
                status_code=500,
                loggable=True,
            ) from exc

    def _path(
        self,
        account_id: str,
        source_id: str,
        source_revision: int,
        ordinal: int,
    ) -> Path:
        _require_id(account_id)
        _require_id(source_id)
        if source_revision < 1 or ordinal < 0:
            raise _invalid_ref()
        path = (
            self._root
            / account_id
            / "knowledge-index"
            / source_id
            / str(source_revision)
            / f"{ordinal}.txt"
        ).resolve()
        if self._root not in path.parents:
            raise _invalid_ref()
        return path

    def _path_from_ref(self, account_id: str, reference: str) -> Path:
        prefix = f"{_REF_PREFIX}{account_id}/"
        if not reference.startswith(prefix):
            raise _invalid_ref()
        parts = reference.removeprefix(prefix).split("/")
        if len(parts) != 3:
            raise _invalid_ref()
        try:
            source_revision = int(parts[1])
            ordinal = int(parts[2])
        except ValueError as exc:
            raise _invalid_ref() from exc
        return self._path(
            account_id,
            parts[0],
            source_revision,
            ordinal,
        )


def _atomic_write(destination: Path, payload: bytes) -> None:
    temporary: Path | None = None
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
            temporary = Path(handle.name)
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _require_id(value: str) -> None:
    if not is_stable_id(value):
        raise _invalid_ref()


def _invalid_ref() -> DomainError:
    return DomainError(
        ErrorCode.CONTROLLED_FILE_REF_INVALID,
        "知识派生索引引用无效",
        status_code=422,
    )
