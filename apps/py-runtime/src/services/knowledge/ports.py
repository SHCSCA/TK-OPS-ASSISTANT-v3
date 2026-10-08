from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from errors import DomainError, ErrorCode
from services.knowledge.index_policy import KnowledgeIndexPolicy


@dataclass(frozen=True, slots=True)
class ResolvedKnowledgeContent:
    data: bytes
    media_type: str | None = None
    controlled_file: ControlledFileGrant | None = None


@dataclass(frozen=True, slots=True)
class ControlledFileGrant:
    file_ref: str
    root_ref: str
    root_revision: int
    file_revision: int
    fingerprint: str
    display_name: str
    kind: str
    media_type: str
    byte_size: int


@dataclass(frozen=True, slots=True)
class ControlledFileExpectation:
    file_ref: str
    root_ref: str
    root_revision: int
    file_revision: int
    fingerprint: str


class ControlledFileResolver(Protocol):
    def describe(
        self,
        account_id: str,
        reference: str,
        *,
        max_bytes: int,
    ) -> ControlledFileGrant: ...

    def read_bytes(
        self,
        account_id: str,
        reference: str,
        *,
        max_bytes: int,
        expected: ControlledFileExpectation | None = None,
    ) -> ResolvedKnowledgeContent: ...


class KnowledgeUrlFetcher(Protocol):
    def fetch(
        self,
        url: str,
        *,
        policy: KnowledgeIndexPolicy,
    ) -> ResolvedKnowledgeContent: ...


class UnavailableControlledFileResolver:
    """在 Tauri 受控文件桥未装配时显式失败。"""

    def describe(
        self,
        account_id: str,
        reference: str,
        *,
        max_bytes: int,
    ) -> ControlledFileGrant:
        del account_id, reference, max_bytes
        raise self._error()

    def read_bytes(
        self,
        account_id: str,
        reference: str,
        *,
        max_bytes: int,
        expected: ControlledFileExpectation | None = None,
    ) -> ResolvedKnowledgeContent:
        del account_id, reference, max_bytes, expected
        raise self._error()

    @staticmethod
    def _error() -> DomainError:
        return DomainError(
            ErrorCode.CONTROLLED_FILE_REF_INVALID,
            "受控文件读取能力尚未就绪，请检查 Runtime 文件桥",
            status_code=503,
            loggable=True,
        )
