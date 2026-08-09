from __future__ import annotations

from typing import Annotated

from pydantic import Field

from schemas.v1.ai_common import (
    AIConfigurationDto,
    AIConfigurationInput,
    BoundedKey,
    BoundedName,
    ContentHash,
    JsonObject,
    NonEmptyText,
    PositiveRevision,
    ProfileStatusValue,
    StableId,
    VersionSummaryDto,
)


class PromptProfileInput(AIConfigurationInput):
    profileKey: StableId
    name: BoundedName
    capabilityKey: BoundedKey
    systemPrompt: NonEmptyText
    taskTemplate: NonEmptyText
    variablesSchema: JsonObject
    outputSchema: JsonObject
    visualStylePrefix: Annotated[str, Field(max_length=32_768)] = ""
    safetyConstraints: JsonObject


class PromptVersionInput(AIConfigurationInput):
    name: BoundedName
    systemPrompt: NonEmptyText
    taskTemplate: NonEmptyText
    variablesSchema: JsonObject
    outputSchema: JsonObject
    visualStylePrefix: Annotated[str, Field(max_length=32_768)] = ""
    safetyConstraints: JsonObject
    createdFromVersion: PositiveRevision


class PromptVersionSummaryDto(VersionSummaryDto):
    pass


class PromptProfileDto(AIConfigurationDto):
    profileKey: StableId
    name: BoundedName
    capabilityKey: BoundedKey
    activeVersion: PositiveRevision | None
    activeVersionId: StableId | None
    versions: list[PromptVersionSummaryDto]
    referenceCount: Annotated[int, Field(ge=0)]
    revision: PositiveRevision


class PromptProfilePageDto(AIConfigurationDto):
    items: list[PromptProfileDto]
    totalKnown: Annotated[int, Field(ge=0)] | None


class PromptVersionDto(AIConfigurationDto):
    id: StableId
    profileKey: StableId
    name: BoundedName
    capabilityKey: BoundedKey
    version: PositiveRevision
    status: ProfileStatusValue
    systemPrompt: str
    taskTemplate: str
    variablesSchema: JsonObject
    outputSchema: JsonObject
    visualStylePrefix: str
    safetyConstraints: JsonObject
    contentHash: ContentHash
    createdFromId: StableId | None
    createdAt: str
    activatedAt: str | None
    revision: PositiveRevision


__all__ = [
    "PromptProfileDto",
    "PromptProfileInput",
    "PromptProfilePageDto",
    "PromptVersionDto",
    "PromptVersionInput",
    "PromptVersionSummaryDto",
]
