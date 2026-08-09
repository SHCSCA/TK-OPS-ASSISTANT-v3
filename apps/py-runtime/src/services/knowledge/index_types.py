from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeIndexPlan:
    account_id: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class KnowledgeIndexSource:
    id: str
    source_mode: str
    source_ref: str
    source_url: str | None


@dataclass(frozen=True, slots=True)
class KnowledgeIndexResult:
    source_id: str
    content_hash: str
    byte_size: int
    account_revision: int
