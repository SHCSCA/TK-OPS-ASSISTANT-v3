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


class AIProviderHealthDto(BaseModel):
    provider: str
    status: str
    message: str


class AICapabilitySettingsDto(BaseModel):
    capabilities: list[AICapabilityConfigDto]
    providers: list[AIProviderSecretStatusDto]
