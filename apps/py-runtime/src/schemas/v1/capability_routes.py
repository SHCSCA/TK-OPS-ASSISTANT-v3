from __future__ import annotations

from typing import Annotated

from pydantic import Field

from schemas.v1.ai_common import (
    AIConfigurationDto,
    AIConfigurationInput,
    BoundedKey,
    JsonObject,
    PositiveRevision,
    StableId,
    ValidationStatusValue,
)


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
    revision: PositiveRevision


class CapabilityRoutePageDto(AIConfigurationDto):
    items: list[CapabilityRouteDto]
    totalKnown: Annotated[int, Field(ge=0)] | None


__all__ = [
    "CapabilityRouteDto",
    "CapabilityRouteInput",
    "CapabilityRoutePageDto",
]
