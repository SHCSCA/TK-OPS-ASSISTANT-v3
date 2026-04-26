from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CAPABILITY_IDS = (
    'script_generation',
    'script_rewrite',
    'storyboard_generation',
    'tts_generation',
    'subtitle_alignment',
    'video_transcription',
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
    readiness: str
    lastCheckedAt: str | None = None
    errorCode: str | None = None
    errorMessage: str | None = None
    scope: str


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


class AIDiagnosticSummaryDto(BaseModel):
    configuredProviderCount: int
    readyProviderCount: int
    degradedProviderCount: int
    lastHealthRefreshAt: str | None = None


class AICapabilitySettingsDto(BaseModel):
    capabilities: list[AICapabilityConfigDto]
    providers: list[AIProviderSecretStatusDto]
    configVersion: str
    scope: str
    diagnosticSummary: AIDiagnosticSummaryDto


class AICapabilityChangedEventDto(BaseModel):
    type: Literal["ai-capability.changed"] = "ai-capability.changed"
    scope: str = "runtime_local"
    configVersion: str
    reason: str
    providerIds: list[str]
    capabilityIds: list[str]


class AIProviderCatalogItemDto(BaseModel):
    provider: str
    label: str
    kind: str
    region: str
    category: str
    protocol: str
    modelSyncMode: str
    tags: list[str]
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


class AIProviderHealthAggregateItemDto(BaseModel):
    provider: str
    label: str
    readiness: str
    lastCheckedAt: str | None = None
    latencyMs: int | None = None
    errorCode: str | None = None
    errorMessage: str | None = None


class AIProviderHealthOverviewDto(BaseModel):
    providers: list[AIProviderHealthAggregateItemDto]
    refreshedAt: str | None = None


class AIProviderModelUpsertInput(BaseModel):
    displayName: str = Field(min_length=1)
    capabilityKinds: list[str]
    inputModalities: list[str] = Field(default_factory=list)
    outputModalities: list[str] = Field(default_factory=list)
    contextWindow: int | None = None
    defaultFor: list[str] = Field(default_factory=list)
    enabled: bool = True


class AIProviderModelWriteReceiptDto(BaseModel):
    saved: bool
    wasUpsert: bool
    updatedAt: str
    versionOrRevision: str
    objectSummary: dict[str, str]
    model: AIModelCatalogItemDto
