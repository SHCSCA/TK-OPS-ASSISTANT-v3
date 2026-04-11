from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException

from app.secret_store import SecretStore
from repositories.ai_capability_repository import (
    AICapabilityRepository,
    StoredAICapabilityConfig,
)
from schemas.ai_capabilities import (
    AICapabilityConfigDto,
    AICapabilitySettingsDto,
    AIProviderHealthDto,
    AIProviderSecretStatusDto,
    CAPABILITY_IDS,
)


@dataclass(frozen=True, slots=True)
class ProviderRuntimeConfig:
    provider: str
    label: str
    api_key: str | None
    base_url: str
    secret_source: str
    supports_text_generation: bool


class AICapabilityService:
    def __init__(
        self,
        repository: AICapabilityRepository,
        secret_store: SecretStore,
    ) -> None:
        self._repository = repository
        self._secret_store = secret_store

    def get_settings(self) -> AICapabilitySettingsDto:
        capabilities = self._load_or_create_capabilities()
        return AICapabilitySettingsDto(
            capabilities=[self._to_capability_dto(item) for item in capabilities],
            providers=self.get_provider_statuses(),
        )

    def update_capabilities(
        self,
        items: list[AICapabilityConfigDto],
    ) -> AICapabilitySettingsDto:
        provided_ids = {item.capabilityId for item in items}
        if provided_ids != set(CAPABILITY_IDS):
            raise HTTPException(status_code=400, detail='Capability config set is incomplete.')

        stored = [
            StoredAICapabilityConfig(
                capability_id=item.capabilityId,
                enabled=item.enabled,
                provider=item.provider,
                model=item.model,
                agent_role=item.agentRole,
                system_prompt=item.systemPrompt,
                user_prompt_template=item.userPromptTemplate,
                updated_at=_utc_now(),
            )
            for item in items
        ]
        self._repository.save_capabilities(stored)
        return self.get_settings()

    def set_provider_secret(
        self,
        provider_id: str,
        *,
        api_key: str,
        base_url: str | None = None,
    ) -> AIProviderSecretStatusDto:
        metadata = _provider_metadata()[provider_id]
        self._secret_store.set(f'provider:{provider_id}:api_key', api_key.strip())
        if base_url is not None:
            self._repository.save_provider_setting(provider_id, base_url.strip())
        elif provider_id == 'openai_compatible':
            current = self.get_provider_runtime_config(provider_id)
            self._repository.save_provider_setting(provider_id, current.base_url)

        return self.get_provider_status(provider_id)

    def get_provider_statuses(self) -> list[AIProviderSecretStatusDto]:
        return [self.get_provider_status(provider_id) for provider_id in _provider_metadata()]

    def get_provider_status(self, provider_id: str) -> AIProviderSecretStatusDto:
        metadata = _provider_metadata()[provider_id]
        runtime = self.get_provider_runtime_config(provider_id)
        return AIProviderSecretStatusDto(
            provider=provider_id,
            label=metadata['label'],
            configured=runtime.api_key is not None and runtime.api_key != '',
            maskedSecret=_mask_secret(runtime.api_key),
            baseUrl=runtime.base_url,
            secretSource=runtime.secret_source,
            supportsTextGeneration=runtime.supports_text_generation,
        )

    def check_provider_health(self, provider_id: str) -> AIProviderHealthDto:
        status = self.get_provider_status(provider_id)
        if not status.supportsTextGeneration:
            return AIProviderHealthDto(
                provider=provider_id,
                status='unsupported',
                message='This provider is registered but not wired for text generation in this milestone.',
            )
        if not status.configured:
            return AIProviderHealthDto(
                provider=provider_id,
                status='missing_secret',
                message='API key is not configured.',
            )
        if provider_id == 'openai_compatible' and status.baseUrl.strip() == '':
            return AIProviderHealthDto(
                provider=provider_id,
                status='misconfigured',
                message='Base URL is required for OpenAI-compatible providers.',
            )
        return AIProviderHealthDto(
            provider=provider_id,
            status='ready',
            message='Provider is configured for text generation.',
        )

    def get_capability(self, capability_id: str) -> AICapabilityConfigDto:
        capabilities = {item.capabilityId: item for item in self.get_settings().capabilities}
        capability = capabilities.get(capability_id)
        if capability is None:
            raise HTTPException(status_code=404, detail='AI capability not found.')
        return capability

    def get_provider_runtime_config(self, provider_id: str) -> ProviderRuntimeConfig:
        metadata = _provider_metadata()[provider_id]
        base_urls = {item.provider_id: item.base_url for item in self._repository.load_provider_settings()}
        secret_key = self._secret_store.get(f'provider:{provider_id}:api_key')
        secret_source = 'secure_store'
        if not secret_key:
            env_key = os.getenv(metadata['env_key'], '').strip()
            secret_key = env_key or None
            secret_source = 'env' if secret_key else 'none'

        base_url = base_urls.get(provider_id, '') or os.getenv(metadata['env_base_url'], '').strip() or metadata['default_base_url']
        return ProviderRuntimeConfig(
            provider=provider_id,
            label=metadata['label'],
            api_key=secret_key,
            base_url=base_url,
            secret_source=secret_source,
            supports_text_generation=metadata['supports_text_generation'],
        )

    def _load_or_create_capabilities(self) -> list[StoredAICapabilityConfig]:
        stored = self._repository.load_capabilities()
        if stored:
            return sorted(stored, key=lambda item: CAPABILITY_IDS.index(item.capability_id))

        defaults = [
            StoredAICapabilityConfig(
                capability_id=capability_id,
                enabled=capability_id in {'script_generation', 'script_rewrite', 'storyboard_generation'},
                provider='openai',
                model='gpt-5' if capability_id == 'script_generation' else 'gpt-5-mini',
                agent_role=_default_agent_role(capability_id),
                system_prompt=_default_system_prompt(capability_id),
                user_prompt_template=_default_template(capability_id),
                updated_at=_utc_now(),
            )
            for capability_id in CAPABILITY_IDS
        ]
        return self._repository.save_capabilities(defaults)

    def _to_capability_dto(self, item: StoredAICapabilityConfig) -> AICapabilityConfigDto:
        return AICapabilityConfigDto(
            capabilityId=item.capability_id,
            enabled=item.enabled,
            provider=item.provider,
            model=item.model,
            agentRole=item.agent_role,
            systemPrompt=item.system_prompt,
            userPromptTemplate=item.user_prompt_template,
        )


def _provider_metadata() -> dict[str, dict[str, str | bool]]:
    return {
        'openai': {
            'label': 'OpenAI',
            'env_key': 'TK_OPS_OPENAI_API_KEY',
            'env_base_url': 'TK_OPS_OPENAI_BASE_URL',
            'default_base_url': 'https://api.openai.com/v1/responses',
            'supports_text_generation': True,
        },
        'openai_compatible': {
            'label': 'OpenAI-compatible',
            'env_key': 'TK_OPS_OPENAI_COMPATIBLE_API_KEY',
            'env_base_url': 'TK_OPS_OPENAI_COMPATIBLE_BASE_URL',
            'default_base_url': '',
            'supports_text_generation': True,
        },
        'anthropic': {
            'label': 'Anthropic',
            'env_key': 'TK_OPS_ANTHROPIC_API_KEY',
            'env_base_url': 'TK_OPS_ANTHROPIC_BASE_URL',
            'default_base_url': 'https://api.anthropic.com/v1/messages',
            'supports_text_generation': False,
        },
        'gemini': {
            'label': 'Gemini',
            'env_key': 'TK_OPS_GEMINI_API_KEY',
            'env_base_url': 'TK_OPS_GEMINI_BASE_URL',
            'default_base_url': 'https://generativelanguage.googleapis.com/v1beta/models',
            'supports_text_generation': False,
        },
    }


def _default_agent_role(capability_id: str) -> str:
    return {
        'script_generation': '资深短视频脚本策划',
        'script_rewrite': '短视频脚本改写编辑',
        'storyboard_generation': '分镜规划导演',
        'tts_generation': '配音导演',
        'subtitle_alignment': '字幕对齐编辑',
        'video_generation': '视频生成导演',
        'asset_analysis': '素材分析师',
    }[capability_id]


def _default_system_prompt(capability_id: str) -> str:
    return {
        'script_generation': '围绕用户主题生成高留存、可拍摄的短视频脚本。',
        'script_rewrite': '在保持原意的前提下提升脚本节奏、开场和转化效率。',
        'storyboard_generation': '把脚本文本拆解为清晰的镜头与视觉提示。',
        'tts_generation': '为脚本生成适合配音的语气和节奏说明。',
        'subtitle_alignment': '让字幕语言和节奏更适合短视频表达。',
        'video_generation': '把分镜转成可执行的视频生成提示。',
        'asset_analysis': '总结素材内容、价值点和可复用结构。',
    }[capability_id]


def _default_template(capability_id: str) -> str:
    return {
        'script_generation': '主题：{{topic}}',
        'script_rewrite': '原脚本：\n{{script}}\n\n改写要求：{{instructions}}',
        'storyboard_generation': '脚本内容：\n{{script}}',
        'tts_generation': '脚本内容：\n{{script}}',
        'subtitle_alignment': '脚本内容：\n{{script}}',
        'video_generation': '分镜内容：\n{{storyboard}}',
        'asset_analysis': '素材内容：\n{{assets}}',
    }[capability_id]


def _mask_secret(value: str | None) -> str:
    if not value:
        return ''
    if len(value) <= 8:
        return '*' * len(value)
    return f'{value[:4]}{"*" * max(4, len(value) - 8)}{value[-4:]}'


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
