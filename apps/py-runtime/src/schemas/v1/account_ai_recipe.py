from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from schemas.v1.ai_dependencies import DependencySnapshotDto
from schemas.v1.ai_common import (
    AIConfigurationDto,
    AIConfigurationInput,
    BoundedKey,
    BoundedName,
    ContentHash,
    JsonObject,
    NonNegativeRevision,
    PositiveRevision,
    ProfileStatusValue,
    StableId,
    ValidationIssueDto,
)

AIRecipeValidationStatus = Literal["unvalidated", "valid", "invalid"]


class AccountAIRecipeVersionInput(AIConfigurationInput):
    name: BoundedName
    routeOverrides: JsonObject
    visualStyle: JsonObject
    voiceProfileRef: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    compositionTemplateRef: Annotated[
        str,
        Field(min_length=1, max_length=512),
    ] | None = None
    costPolicy: JsonObject
    fallbackPolicy: JsonObject


class AIRecipeVersionSummaryDto(AIConfigurationDto):
    version: PositiveRevision
    status: ProfileStatusValue
    validationStatus: AIRecipeValidationStatus


class AIRecipeDto(AIConfigurationDto):
    accountId: StableId
    activeVersion: PositiveRevision | None
    activeVersionId: StableId | None
    versions: list[AIRecipeVersionSummaryDto]
    resolvedSummary: JsonObject | None
    revision: PositiveRevision


class AIRecipeVersionDto(AIConfigurationDto):
    id: StableId
    accountId: StableId
    version: PositiveRevision
    status: ProfileStatusValue
    name: BoundedName
    routeOverrides: JsonObject
    visualStyle: JsonObject
    voiceProfileRef: str | None
    compositionTemplateRef: str | None
    costPolicy: JsonObject
    fallbackPolicy: JsonObject
    sourceAiConfigRevision: NonNegativeRevision
    validationStatus: AIRecipeValidationStatus
    validationIssues: list[ValidationIssueDto]
    contentHash: ContentHash
    createdAt: str
    activatedAt: str | None
    revision: PositiveRevision


class AIRecipeVersionPageDto(AIConfigurationDto):
    items: list[AIRecipeVersionDto]
    totalKnown: Annotated[int, Field(ge=0)] | None


class AIRecipeValidationIssueDto(ValidationIssueDto):
    suggestedAction: str | None


class ResolvedRecipeRouteDto(AIConfigurationDto):
    modelProfileId: StableId
    promptProfileId: StableId | None
    source: Literal["system", "account_override"]


class AIRecipeValidationDto(AIConfigurationDto):
    accountId: StableId
    version: PositiveRevision
    validationStatus: Literal["valid", "invalid"]
    validationIssues: list[AIRecipeValidationIssueDto]
    resolvedRouteSummary: dict[str, ResolvedRecipeRouteDto]
    sourceAiConfigRevision: NonNegativeRevision
    dependencySnapshot: DependencySnapshotDto


__all__ = [
    "AIRecipeDto",
    "AIRecipeValidationDto",
    "AIRecipeVersionDto",
    "AIRecipeVersionPageDto",
    "AccountAIRecipeVersionInput",
]
