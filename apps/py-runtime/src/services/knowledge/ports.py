from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from errors import DomainError, ErrorCode
from services.knowledge.index_policy import KnowledgeIndexPolicy


@dataclass(frozen=True, slots=True)
class ResolvedKnowledgeContent:
    data: bytes
    media_type: str | None = None


class ControlledFileResolver(Protocol):
    def read_bytes(
        self,
        account_id: str,
        reference: str,
        *,
        max_bytes: int,
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

    def read_bytes(
        self,
        account_id: str,
        reference: str,
        *,
        max_bytes: int,
    ) -> ResolvedKnowledgeContent:
        del account_id, reference, max_bytes
        raise DomainError(
            ErrorCode.CONTROLLED_FILE_REF_INVALID,
            "受控文件读取能力尚未就绪，请检查 Runtime 文件桥",
            status_code=503,
            loggable=True,
        )
