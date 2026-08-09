from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from schemas.v1.account_common import (
    AccountV1Model,
    PositiveRevision,
    StableId,
)

KnowledgeKind = Literal[
    "document",
    "image",
    "video",
    "audio",
    "text",
    "reference",
]
KNOWLEDGE_KINDS = frozenset(
    {"document", "image", "video", "audio", "text", "reference"}
)
KnowledgeSourceMode = Literal["file", "url", "text"]
KnowledgeSourceStatus = Literal[
    "pending",
    "indexing",
    "ready",
    "failed",
    "stale",
    "removed",
]
KNOWLEDGE_SOURCE_STATUSES = frozenset(
    {"pending", "indexing", "ready", "failed", "stale", "removed"}
)


class KnowledgeRulesPatchInput(AccountV1Model):
    inclusionRules: dict[str, object]
    exclusionRules: dict[str, object]
    citationPolicy: dict[str, object]


class KnowledgeSourceInput(AccountV1Model):
    kind: KnowledgeKind
    sourceMode: KnowledgeSourceMode
    controlledFileRef: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    url: Annotated[str, Field(min_length=1, max_length=2048)] | None = None
    title: Annotated[str, Field(min_length=1, max_length=256)]
    text: Annotated[str, Field(min_length=1, max_length=1_000_000)] | None = None

    @model_validator(mode="after")
    def validate_source_mode(self) -> KnowledgeSourceInput:
        provided = {
            "file": self.controlledFileRef is not None,
            "url": self.url is not None,
            "text": self.text is not None,
        }
        if not provided[self.sourceMode]:
            raise ValueError("知识来源缺少与摄取方式匹配的内容")
        if sum(provided.values()) != 1:
            raise ValueError("知识来源只能提交一种摄取内容")
        return self


class KnowledgeSnapshotInput(AccountV1Model):
    sourceIds: Annotated[
        list[StableId],
        Field(min_length=1, max_length=10_000),
    ]
    label: Annotated[str, Field(min_length=1, max_length=256)] | None = None


class KnowledgeIndexInput(AccountV1Model):
    sourceIds: Annotated[
        list[StableId],
        Field(min_length=1, max_length=10_000),
    ] | None = None


class KnowledgeDto(AccountV1Model):
    accountId: StableId
    rules: KnowledgeRulesPatchInput
    rulesVersion: Annotated[int, Field(ge=0)]
    sourceCounts: dict[str, Annotated[int, Field(ge=0)]]
    latestSnapshotId: StableId | None
    readiness: dict[str, object]
    revision: PositiveRevision


class KnowledgeSourceDto(AccountV1Model):
    id: StableId
    accountId: StableId
    kind: KnowledgeKind
    sourceMode: KnowledgeSourceMode
    title: str
    status: KnowledgeSourceStatus
    controlledRef: str | None
    sourceUrl: str | None
    contentHash: str | None
    indexedAt: str | None
    removedAt: str | None
    errorCode: str | None
    logId: StableId | None
    revision: PositiveRevision


class KnowledgeSourcePageDto(AccountV1Model):
    items: list[KnowledgeSourceDto]
    totalKnown: Annotated[int, Field(ge=0)] | None


class KnowledgeSourceEvidenceDto(AccountV1Model):
    sourceId: StableId
    contentHash: Annotated[str, Field(min_length=64, max_length=64)]
    indexedRevision: PositiveRevision


class KnowledgeSnapshotDto(AccountV1Model):
    id: StableId
    accountId: StableId
    label: str | None
    sourceIds: list[StableId]
    sourceEvidence: list[KnowledgeSourceEvidenceDto]
    rulesVersion: Annotated[int, Field(ge=0)]
    contentHash: Annotated[str, Field(min_length=64, max_length=64)]
    createdAt: str


class KnowledgeSnapshotPageDto(AccountV1Model):
    items: list[KnowledgeSnapshotDto]
    totalKnown: Annotated[int, Field(ge=0)] | None
