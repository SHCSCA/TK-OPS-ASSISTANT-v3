from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from schemas.v1.ai_common import (
    AIConfigurationDto,
    AIConfigurationInput,
    BoundedKey,
    BoundedName,
    ContentHash,
    JsonObject,
    PositiveRevision,
    ProfileStatusValue,
    StableId,
    ValidationIssueDto,
    VersionSummaryDto,
)

CompositionTemplateType = Literal[
    "slideshow",
    "talking_head",
    "product_showcase",
    "mixed_media",
]


class CompositionTemplateInput(AIConfigurationInput):
    templateKey: StableId
    name: BoundedName
    templateType: CompositionTemplateType
    aspectRatios: Annotated[list[str], Field(min_length=1, max_length=32)]
    parameterSchema: JsonObject
    compositionSpecTemplate: JsonObject
    compatibleCapabilities: JsonObject
    previewAssetRef: Annotated[str, Field(min_length=1, max_length=512)] | None = None


class CompositionTemplateVersionInput(AIConfigurationInput):
    name: BoundedName
    aspectRatios: Annotated[list[str], Field(min_length=1, max_length=32)]
    parameterSchema: JsonObject
    compositionSpecTemplate: JsonObject
    compatibleCapabilities: JsonObject
    previewAssetRef: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    createdFromVersion: PositiveRevision


class CompositionTemplateVersionSummaryDto(VersionSummaryDto):
    pass


class CompositionTemplateDto(AIConfigurationDto):
    templateKey: StableId
    name: BoundedName
    templateType: CompositionTemplateType
    activeVersion: PositiveRevision | None
    activeVersionId: StableId | None
    versions: list[CompositionTemplateVersionSummaryDto]
    compatibleCapabilities: JsonObject
    referenceCount: Annotated[int, Field(ge=0)]
    revision: PositiveRevision


class CompositionTemplatePageDto(AIConfigurationDto):
    items: list[CompositionTemplateDto]
    totalKnown: Annotated[int, Field(ge=0)] | None


class CompositionTemplateVersionDto(AIConfigurationDto):
    id: StableId
    templateKey: StableId
    name: BoundedName
    templateType: CompositionTemplateType
    version: PositiveRevision
    status: ProfileStatusValue
    aspectRatios: list[str]
    parameterSchema: JsonObject
    compositionSpecTemplate: JsonObject
    compatibleCapabilities: JsonObject
    previewAssetRef: str | None
    contentHash: ContentHash
    createdFromId: StableId | None
    createdAt: str
    activatedAt: str | None
    revision: PositiveRevision


class CompositionTemplateValidationDto(AIConfigurationDto):
    templateKey: StableId
    version: PositiveRevision
    validationStatus: Literal["valid", "invalid"]
    validationIssues: list[ValidationIssueDto]
    verifiedCapabilities: list[BoundedKey]
    checkedAt: str


__all__ = [
    "CompositionTemplateDto",
    "CompositionTemplateInput",
    "CompositionTemplatePageDto",
    "CompositionTemplateType",
    "CompositionTemplateValidationDto",
    "CompositionTemplateVersionDto",
    "CompositionTemplateVersionInput",
]
