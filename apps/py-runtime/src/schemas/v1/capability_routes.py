from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from schemas.v1.ai_common import (
    AIConfigurationDto,
    AIConfigurationInput,
    BoundedKey,
    JsonObject,
    PositiveRevision,
    StableId,
    ValidationStatusValue,
    ContentHash,
)
from schemas.v1.ai_dependencies import DependencySnapshotDto


class CapabilityRouteInput(AIConfigurationInput):
    primaryModelProfileId: StableId | None
    fallbackModelProfileId: StableId | None
    promptProfileId: StableId | None
    enabled: bool


class CapabilityRouteDto(AIConfigurationDto):
    id: StableId
    capabilityKey: BoundedKey
    primaryModelProfileId: StableId | None
    fallbackModelProfileId: StableId | None
    promptProfileId: StableId | None
    enabled: bool
    validationStatus: ValidationStatusValue
    validationIssues: list[JsonObject]
    activeRevisionId: StableId | None = None
    revision: PositiveRevision


class CapabilityRoutePageDto(AIConfigurationDto):
    items: list[CapabilityRouteDto]
    totalKnown: Annotated[int, Field(ge=0)] | None


class CapabilityRouteCandidateInput(AIConfigurationInput):
    modelProfileId: StableId


class CapabilityRouteRevisionInput(AIConfigurationInput):
    promptProfileId: StableId | None = None
    candidates: Annotated[
        list[CapabilityRouteCandidateInput],
        Field(max_length=8),
    ]
    timeoutMs: Annotated[int, Field(ge=1, le=86_400_000)] = 120_000
    maxRetries: Annotated[int, Field(ge=0, le=3)] = 1
    retryPolicy: JsonObject = Field(default_factory=dict)
    maxConcurrency: Annotated[int, Field(ge=1, le=32)] = 1
    maxCostMicros: Annotated[int, Field(ge=0, le=10**12)] = 0
    currency: Annotated[str, Field(min_length=3, max_length=3)] = "USD"
    enabled: bool = True


class CapabilityRouteRevisionDto(AIConfigurationDto):
    id: StableId
    capabilityRouteId: StableId
    capabilityKey: BoundedKey
    revision: PositiveRevision
    status: Literal["draft", "active", "archived"]
    promptProfileId: StableId | None
    candidates: list[JsonObject]
    timeoutMs: Annotated[int, Field(ge=1)]
    maxRetries: Annotated[int, Field(ge=0)]
    retryPolicy: JsonObject
    maxConcurrency: Annotated[int, Field(ge=1)]
    maxCostMicros: Annotated[int, Field(ge=0)]
    currency: Annotated[str, Field(min_length=3, max_length=3)]
    enabled: bool
    dependencySnapshotId: StableId | None
    contentHash: ContentHash
    createdAt: str


class CapabilityRouteRevisionPageDto(AIConfigurationDto):
    items: list[CapabilityRouteRevisionDto]
    totalKnown: Annotated[int, Field(ge=0)]


class CapabilityRouteValidationDto(AIConfigurationDto):
    capabilityRouteId: StableId
    capabilityKey: BoundedKey
    routeRevision: PositiveRevision
    status: Literal["valid", "invalid"]
    dependencySnapshot: DependencySnapshotDto


__all__ = [
    "CapabilityRouteDto",
    "CapabilityRouteCandidateInput",
    "CapabilityRouteInput",
    "CapabilityRoutePageDto",
    "CapabilityRouteRevisionDto",
    "CapabilityRouteRevisionInput",
    "CapabilityRouteRevisionPageDto",
    "CapabilityRouteValidationDto",
]
