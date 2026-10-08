from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from schemas.v1.ai_common import (
    AIConfigurationDto,
    AIConfigurationInput,
    BoundedName,
    JsonObject,
    PositiveRevision,
    StableId,
)

ProviderAdapterType = Literal[
    "direct_api",
    "openai_compatible",
    "comfyui",
    "runninghub",
]
ProviderHealthStatus = Literal[
    "unknown",
    "checking",
    "ready",
    "degraded",
    "failed",
]


class ProviderCreateInput(AIConfigurationInput):
    name: BoundedName
    adapterType: ProviderAdapterType
    baseUrl: Annotated[str, Field(min_length=1, max_length=2_048)]
    region: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    proxyRef: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    timeoutMs: Annotated[int, Field(ge=1)]
    maxConcurrency: Annotated[int, Field(ge=1)]
    enabled: bool
    extraParams: JsonObject = Field(default_factory=dict)
    costPolicy: JsonObject = Field(default_factory=dict)


class ProviderPatchInput(AIConfigurationInput):
    name: BoundedName | None = None
    baseUrl: Annotated[str, Field(min_length=1, max_length=2_048)] | None = None
    region: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    proxyRef: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    timeoutMs: Annotated[int, Field(ge=1)] | None = None
    maxConcurrency: Annotated[int, Field(ge=1)] | None = None
    enabled: bool | None = None
    extraParams: JsonObject | None = None
    costPolicy: JsonObject | None = None

    @model_validator(mode="after")
    def require_patch_field(self) -> ProviderPatchInput:
        if not self.model_fields_set:
            raise ValueError("至少需要提交一个 Provider 字段")
        nullable_fields = {"region", "proxyRef"}
        invalid_nulls = {
            field_name
            for field_name in self.model_fields_set
            if field_name not in nullable_fields
            and getattr(self, field_name) is None
        }
        if invalid_nulls:
            raise ValueError("Provider 更新字段不能设为空值")
        return self


class ProviderCredentialInput(AIConfigurationInput):
    credential: Annotated[str, Field(min_length=1, max_length=32_768)]


class ProviderCheckInput(AIConfigurationInput):
    stages: list[Literal["network", "authentication"]] = Field(
        default_factory=lambda: ["network", "authentication"],
        min_length=1,
        max_length=2,
    )
    force: bool = False

    @model_validator(mode="after")
    def reject_duplicate_stages(self) -> ProviderCheckInput:
        if len(set(self.stages)) != len(self.stages):
            raise ValueError("Provider 检查阶段不能重复")
        return self


class ModelDiscoveryInput(AIConfigurationInput):
    replaceMissing: Literal[False] = False


class ProviderCredentialDto(AIConfigurationDto):
    configured: bool
    maskedValue: Annotated[str, Field(min_length=1, max_length=256)] | None


class ProviderDto(AIConfigurationDto):
    id: StableId
    name: BoundedName
    adapterType: ProviderAdapterType
    baseUrl: Annotated[str, Field(min_length=1, max_length=2_048)]
    credentialSummary: ProviderCredentialDto
    region: str | None = None
    proxyRef: str | None = None
    timeoutMs: Annotated[int, Field(ge=1)] | None = None
    maxConcurrency: Annotated[int, Field(ge=1)] | None = None
    enabled: bool
    extraParams: JsonObject = Field(default_factory=dict)
    costPolicy: JsonObject = Field(default_factory=dict)
    activeRevisionId: StableId | None = None
    healthStatus: ProviderHealthStatus
    lastCheckedAt: str | None = None
    lastErrorCode: str | None = None
    logId: str | None = None
    revision: PositiveRevision


class ProviderPageDto(AIConfigurationDto):
    items: list[ProviderDto]
    totalKnown: Annotated[int, Field(ge=0)] | None


class CredentialSummaryDto(AIConfigurationDto):
    configured: Literal[True]
    maskedValue: Annotated[str, Field(min_length=1, max_length=256)]
    updatedAt: str
    providerRevision: PositiveRevision
    credentialReferenceChanged: Literal[True]


__all__ = [
    "CredentialSummaryDto",
    "ModelDiscoveryInput",
    "ProviderAdapterType",
    "ProviderCheckInput",
    "ProviderCreateInput",
    "ProviderCredentialInput",
    "ProviderDto",
    "ProviderHealthStatus",
    "ProviderPageDto",
    "ProviderPatchInput",
]
