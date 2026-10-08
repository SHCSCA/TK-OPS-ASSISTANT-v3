from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class KnowledgeIndexPlan:
    account_id: str
    source_ids: tuple[str, ...]
    source_manifests: tuple[KnowledgeIndexSourceManifest, ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeIndexSourceManifest:
    source_id: str
    source_revision: int
    source_mode: str
    file_ref: str | None = None
    root_ref: str | None = None
    root_revision: int | None = None
    file_revision: int | None = None
    fingerprint: str | None = None

    def to_snapshot(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sourceId": self.source_id,
            "sourceRevision": self.source_revision,
            "sourceMode": self.source_mode,
        }
        if self.source_mode == "file":
            payload.update(
                {
                    "fileRef": self.file_ref,
                    "rootRef": self.root_ref,
                    "rootRevision": self.root_revision,
                    "fileRevision": self.file_revision,
                    "fingerprint": self.fingerprint,
                }
            )
        return payload


@dataclass(frozen=True, slots=True)
class KnowledgeIndexSource:
    id: str
    source_mode: str
    source_ref: str
    source_url: str | None
    revision: int
    status: str


@dataclass(frozen=True, slots=True)
class KnowledgeIndexChunkWrite:
    ordinal: int
    content_ref: str
    content_hash: str
    token_count: int
    extractor_version: int


@dataclass(frozen=True, slots=True)
class KnowledgeIndexResult:
    source_id: str
    content_hash: str
    byte_size: int
    account_revision: int
