from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from schemas.v1.ai_common import (
    AIConfigurationDto,
    AIConfigurationInput,
    BoundedKey,
    BoundedName,
    JsonObject,
    PositiveRevision,
    StableId,
)

ModelAvailability = Literal["available", "unverified", "unavailable"]


class ModelCreateInput(AIConfigurationInput):
    providerProfileId: StableId
    modelId: Annotated[str, Field(min_length=1, max_length=256)]
    displayName: BoundedName
    enabled: bool
    baseLimits: JsonObject = Field(default_factory=dict)


class ModelPatchInput(AIConfigurationInput):
    displayName: BoundedName | None = None
    enabled: bool | None = None
    baseLimits: JsonObject | None = None

    @model_validator(mode="after")
    def require_patch_field(self) -> ModelPatchInput:
        if not self.model_fields_set:
            raise ValueError("至少需要提交一个模型字段")
        if any(
            getattr(self, field_name) is None
            for field_name in self.model_fields_set
        ):
            raise ValueError("模型更新字段不能设为空值")
        return self


class CapabilityCheckInput(AIConfigurationInput):
    capabilityKeys: Annotated[
        list[BoundedKey],
        Field(max_length=100),
    ] | None = None
    force: bool = False

    @model_validator(mode="after")
    def reject_duplicate_capabilities(self) -> CapabilityCheckInput:
        if (
            "capabilityKeys" in self.model_fields_set
            and self.capabilityKeys is None
        ):
            raise ValueError("能力键列表不能设为空值")
        if self.capabilityKeys is not None and len(
            set(self.capabilityKeys)
        ) != len(self.capabilityKeys):
            raise ValueError("能力键不能重复")
        return self


class ModelCapabilityDto(AIConfigurationDto):
    capabilityKey: BoundedKey
    declaredSupported: bool
    adapterSupported: bool
    contractVerified: bool
    availability: ModelAvailability
    inputModalities: list[str] = Field(default_factory=list)
    outputModalities: list[str] = Field(default_factory=list)
    parameterSchema: JsonObject = Field(default_factory=dict)
    knownLimits: JsonObject = Field(default_factory=dict)
    verifiedAt: str | None
    contractRevision: PositiveRevision


class ModelProfileDto(AIConfigurationDto):
    id: StableId
    providerProfileId: StableId
    modelId: Annotated[str, Field(min_length=1, max_length=256)]
    displayName: BoundedName
    enabled: bool
    discoverySource: Literal["discovered", "manual", "migrated"]
    contextWindow: Annotated[int, Field(ge=1)] | None = None
    baseLimits: JsonObject = Field(default_factory=dict)
    capabilities: list[ModelCapabilityDto]
    revision: PositiveRevision


class ModelPageDto(AIConfigurationDto):
    items: list[ModelProfileDto]
    totalKnown: Annotated[int, Field(ge=0)] | None


class ModelCapabilityListItemDto(ModelCapabilityDto):
    modelProfileId: StableId
    providerProfileId: StableId


class ModelCapabilityPageDto(AIConfigurationDto):
    items: list[ModelCapabilityListItemDto]
    totalKnown: Annotated[int, Field(ge=0)] | None


__all__ = [
    "CapabilityCheckInput",
    "ModelAvailability",
    "ModelCapabilityDto",
    "ModelCapabilityListItemDto",
    "ModelCapabilityPageDto",
    "ModelCreateInput",
    "ModelPageDto",
    "ModelPatchInput",
    "ModelProfileDto",
]
