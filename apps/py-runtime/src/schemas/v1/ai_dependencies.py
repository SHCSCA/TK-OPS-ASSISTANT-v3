from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from schemas.v1.ai_common import (
    AIConfigurationDto,
    BoundedKey,
    ContentHash,
    PositiveRevision,
    StableId,
)


class DependencyIssueDto(AIConfigurationDto):
    code: BoundedKey
    severity: Literal["info", "warning", "error"]
    nodeType: BoundedKey
    nodeId: Annotated[str, Field(min_length=1, max_length=256)] | None
    path: Annotated[str, Field(max_length=512)]
    message: Annotated[str, Field(min_length=1, max_length=1_024)]
    blocking: bool
    evidenceRef: Annotated[str, Field(min_length=1, max_length=512)] | None


class RepairActionDto(AIConfigurationDto):
    kind: Literal["navigate", "edit"]
    label: Annotated[str, Field(min_length=1, max_length=128)]
    targetPage: BoundedKey
    targetSection: BoundedKey
    targetResourceId: Annotated[str, Field(min_length=1, max_length=256)] | None
    requiredAccountId: StableId | None


class DependencySnapshotDto(AIConfigurationDto):
    id: StableId
    ownerType: Literal[
        "route",
        "recipe",
        "composition_template",
        "execution_preflight",
    ]
    ownerId: StableId
    ownerRevision: PositiveRevision
    status: Literal["valid", "invalid"]
    contentHash: ContentHash
    issues: list[DependencyIssueDto]
    repairActions: list[RepairActionDto]
    createdAt: str


__all__ = [
    "DependencyIssueDto",
    "DependencySnapshotDto",
    "RepairActionDto",
]
