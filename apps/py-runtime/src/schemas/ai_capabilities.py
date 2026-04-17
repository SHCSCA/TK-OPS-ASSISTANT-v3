from __future__ import annotations

from pydantic import BaseModel, Field


CAPABILITY_IDS = (
    'script_generation',
    'script_rewrite',
    'storyboard_generation',
    'tts_generation',
    'subtitle_alignment',
    'video_generation',
    'asset_analysis',
)


class AICapabilityConfigDto(BaseModel):
    capabilityId: str
    enabled: bool
    provider: str
    model: str
    agentRole: str
    systemPrompt: str
    userPromptTemplate: str


class AICapabilityConfigListInput(BaseModel):
    capabilities: list[AICapabilityConfigDto] = Field(min_length=1)


class AIProviderSecretStatusDto(BaseModel):
    provider: str
    label: str
    configured: bool
    maskedSecret: str
    baseUrl: str
    secretSource: str
    supportsTextGeneration: bool


class AIProviderSecretInput(BaseModel):
    apiKey: str = Field(min_length=1)
    baseUrl: str | None = None


class AIProviderHealthCheckInput(BaseModel):
    model: str | None = None


class AIProviderHealthDto(BaseModel):
    provider: str
    status: str
    message: str
    model: str | None = None
    checkedAt: str | None = None
    latencyMs: int | None = None


class AICapabilitySettingsDto(BaseModel):
    capabilities: list[AICapabilityConfigDto]
    providers: list[AIProviderSecretStatusDto]


class AIProviderCatalogItemDto(BaseModel):
    provider: str
    label: str
    kind: str
    configured: bool
    baseUrl: str
    secretSource: str
    capabilities: list[str]
    requiresBaseUrl: bool
    supportsModelDiscovery: bool
    status: str


class AIModelCatalogItemDto(BaseModel):
    modelId: str
    displayName: str
    provider: str
    capabilityTypes: list[str]
    inputModalities: list[str]
    outputModalities: list[str]
    contextWindow: int | None
    defaultFor: list[str]
    enabled: bool


class AICapabilityModelOptionDto(BaseModel):
    provider: str
    modelId: str
    displayName: str
    capabilityTypes: list[str]


class AICapabilitySupportItemDto(BaseModel):
    capabilityId: str
    providers: list[str]
    models: list[AICapabilityModelOptionDto]


class AICapabilitySupportMatrixDto(BaseModel):
    capabilities: list[AICapabilitySupportItemDto]


class AIModelCatalogRefreshResultDto(BaseModel):
    provider: str
    status: str
    message: str
