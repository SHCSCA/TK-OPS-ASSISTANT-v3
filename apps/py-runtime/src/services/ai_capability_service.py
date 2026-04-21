from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException

from app.secret_store import SecretStore
from common.http_errors import RuntimeHTTPException
from repositories.ai_capability_repository import (
    AICapabilityRepository,
    StoredAICapabilityConfig,
    StoredAIProviderHealth,
    StoredAIProviderModel,
)
from schemas.ai_capabilities import (
    AICapabilityConfigDto,
    AICapabilityModelOptionDto,
    AICapabilitySettingsDto,
    AICapabilitySupportItemDto,
    AICapabilitySupportMatrixDto,
    AIModelCatalogItemDto,
    AIModelCatalogRefreshResultDto,
    AIProviderCatalogItemDto,
    AIProviderHealthAggregateItemDto,
    AIProviderHealthDto,
    AIProviderHealthOverviewDto,
    AIProviderModelUpsertInput,
    AIProviderModelWriteReceiptDto,
    AIProviderSecretStatusDto,
    CAPABILITY_IDS,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProviderRuntimeConfig:
    provider: str
    label: str
    api_key: str | None
    base_url: str
    secret_source: str
    requires_secret: bool
    supports_text_generation: bool
    supports_tts: bool
    protocol_family: str


@dataclass(frozen=True, slots=True)
class ProviderHealthProbeResult:
    status: str
    message: str
    latency_ms: int | None


class ProviderConnectivityError(Exception):
    def __init__(self, *, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


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
            raise HTTPException(status_code=400, detail="AI 能力配置不完整。")

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
        metadata = _get_provider_catalog_metadata(provider_id)
        self._secret_store.set(f"provider:{provider_id}:api_key", api_key.strip())
        if base_url is not None:
            self._repository.save_provider_setting(provider_id, base_url.strip())
        elif bool(metadata["requires_base_url"]):
            current = self.get_provider_runtime_config(provider_id)
            self._repository.save_provider_setting(provider_id, current.base_url)
        return self.get_provider_status(provider_id)

    def get_provider_statuses(self) -> list[AIProviderSecretStatusDto]:
        return [self.get_provider_status(provider_id) for provider_id in _provider_catalog_metadata()]

    def get_provider_status(self, provider_id: str) -> AIProviderSecretStatusDto:
        metadata = _get_provider_catalog_metadata(provider_id)
        runtime = self.get_provider_runtime_config(provider_id)
        configured = _is_catalog_provider_configured(metadata, runtime)
        return AIProviderSecretStatusDto(
            provider=provider_id,
            label=str(metadata["label"]),
            configured=configured,
            maskedSecret=_mask_secret(runtime.api_key),
            baseUrl=runtime.base_url,
            secretSource=runtime.secret_source,
            supportsTextGeneration="text_generation" in metadata["capabilities"],
        )

    def get_provider_catalog(self) -> list[AIProviderCatalogItemDto]:
        return [self.get_provider_catalog_item(provider_id) for provider_id in _provider_catalog_metadata()]

    def get_provider_catalog_item(self, provider_id: str) -> AIProviderCatalogItemDto:
        metadata = _get_provider_catalog_metadata(provider_id)
        runtime = self._get_catalog_runtime_config(provider_id)
        configured = _is_catalog_provider_configured(metadata, runtime)
        return AIProviderCatalogItemDto(
            provider=provider_id,
            label=str(metadata["label"]),
            kind=str(metadata["kind"]),
            configured=configured,
            baseUrl=runtime.base_url,
            secretSource=runtime.secret_source,
            capabilities=list(metadata["capabilities"]),
            requiresBaseUrl=bool(metadata["requires_base_url"]),
            supportsModelDiscovery=bool(metadata["supports_model_discovery"]),
            status=_catalog_provider_status(metadata, runtime, configured),
        )

    def get_provider_health_overview(self) -> AIProviderHealthOverviewDto:
        snapshots = {
            item.provider_id: item
            for item in self._repository.load_provider_health_snapshots()
        }
        providers = [
            AIProviderHealthAggregateItemDto(
                provider=provider_id,
                label=str(metadata["label"]),
                readiness=snapshots[provider_id].readiness if provider_id in snapshots else "not_checked",
                lastCheckedAt=snapshots[provider_id].last_checked_at if provider_id in snapshots else None,
                latencyMs=snapshots[provider_id].latency_ms if provider_id in snapshots else None,
                errorCode=snapshots[provider_id].error_code if provider_id in snapshots else None,
                errorMessage=snapshots[provider_id].error_message if provider_id in snapshots else None,
            )
            for provider_id, metadata in _provider_catalog_metadata().items()
        ]
        refreshed_at = max((item.updated_at for item in snapshots.values()), default=None)
        return AIProviderHealthOverviewDto(providers=providers, refreshedAt=refreshed_at)

    def refresh_provider_health(self) -> AIProviderHealthOverviewDto:
        refreshed_at = _utc_now()
        snapshots: list[StoredAIProviderHealth] = []
        for provider_id, metadata in _provider_catalog_metadata().items():
            try:
                health = self.check_provider_health(provider_id)
                snapshots.append(
                    StoredAIProviderHealth(
                        provider_id=provider_id,
                        label=str(metadata["label"]),
                        readiness=health.status,
                        last_checked_at=health.checkedAt,
                        latency_ms=health.latencyMs,
                        error_code=_provider_health_error_code(health.status),
                        error_message=None if health.status == "ready" else health.message,
                        updated_at=refreshed_at,
                    )
                )
            except Exception as exc:
                log.exception("刷新 AI Provider 聚合健康失败 provider=%s", provider_id)
                snapshots.append(
                    StoredAIProviderHealth(
                        provider_id=provider_id,
                        label=str(metadata["label"]),
                        readiness="refresh_failed",
                        last_checked_at=refreshed_at,
                        latency_ms=None,
                        error_code="provider.health.refresh_failed",
                        error_message=str(exc),
                        updated_at=refreshed_at,
                    )
                )
        self._repository.save_provider_health_snapshots(snapshots)
        return self.get_provider_health_overview()

    def get_provider_models(self, provider_id: str) -> list[AIModelCatalogItemDto]:
        _get_provider_catalog_metadata(provider_id)
        return [item for item in self._model_catalog() if item.provider == provider_id]

    def upsert_provider_model(
        self,
        provider_id: str,
        model_id: str,
        payload: AIProviderModelUpsertInput,
    ) -> AIProviderModelWriteReceiptDto:
        _get_provider_catalog_metadata(provider_id)
        capability_kinds = [item.strip() for item in payload.capabilityKinds if item.strip()]
        if not capability_kinds:
            raise RuntimeHTTPException(
                status_code=400,
                detail="AI Provider 模型至少需要声明一项 capability。",
                error_code="provider.model.capability_required",
            )

        now = _utc_now()
        stored, was_upsert = self._repository.upsert_provider_model(
            StoredAIProviderModel(
                provider_id=provider_id,
                model_id=model_id,
                display_name=payload.displayName.strip(),
                capability_kinds=capability_kinds,
                input_modalities=[item.strip() for item in payload.inputModalities if item.strip()],
                output_modalities=[item.strip() for item in payload.outputModalities if item.strip()],
                context_window=payload.contextWindow,
                default_for=[item.strip() for item in payload.defaultFor if item.strip()],
                enabled=payload.enabled,
                created_at=now,
                updated_at=now,
            )
        )
        dto = self._to_model_dto(stored)
        return AIProviderModelWriteReceiptDto(
            saved=True,
            wasUpsert=was_upsert,
            updatedAt=stored.updated_at,
            versionOrRevision=stored.updated_at,
            objectSummary={
                "provider": provider_id,
                "modelId": model_id,
                "displayName": dto.displayName,
            },
            model=dto,
        )

    def refresh_provider_models(self, provider_id: str) -> AIModelCatalogRefreshResultDto:
        _get_provider_catalog_metadata(provider_id)
        return AIModelCatalogRefreshResultDto(
            provider=provider_id,
            status="static_catalog",
            message="当前模型目录来自内置注册表，暂未执行远端刷新。",
        )

    def get_capability_support_matrix(self) -> AICapabilitySupportMatrixDto:
        models = [item for item in self._model_catalog() if item.enabled]
        items: list[AICapabilitySupportItemDto] = []
        for capability_id in CAPABILITY_IDS:
            supported = [
                model
                for model in models
                if capability_id in model.defaultFor
                or _capability_type_for(capability_id) in model.capabilityTypes
            ]
            items.append(
                AICapabilitySupportItemDto(
                    capabilityId=capability_id,
                    providers=sorted({model.provider for model in supported}),
                    models=[
                        AICapabilityModelOptionDto(
                            provider=model.provider,
                            modelId=model.modelId,
                            displayName=model.displayName,
                            capabilityTypes=model.capabilityTypes,
                        )
                        for model in supported
                    ],
                )
            )
        return AICapabilitySupportMatrixDto(capabilities=items)

    def check_provider_health(
        self,
        provider_id: str,
        *,
        model: str | None = None,
    ) -> AIProviderHealthDto:
        metadata = _get_provider_catalog_metadata(provider_id)
        runtime = self.get_provider_runtime_config(provider_id)
        checked_at = _utc_now()

        if "text_generation" not in metadata["capabilities"]:
            return AIProviderHealthDto(
                provider=provider_id,
                status="unsupported",
                message="当前 Provider 已注册，但当前阶段尚未接入文本模型连通性检测。",
                model=None,
                checkedAt=checked_at,
                latencyMs=None,
            )

        if bool(metadata["requires_base_url"]) and runtime.base_url.strip() == "":
            return AIProviderHealthDto(
                provider=provider_id,
                status="misconfigured",
                message="当前 Provider 必须先配置 Base URL。",
                model=model,
                checkedAt=checked_at,
                latencyMs=None,
            )

        if bool(metadata["requires_secret"]) and not runtime.api_key:
            return AIProviderHealthDto(
                provider=provider_id,
                status="missing_secret",
                message="Provider API Key 尚未配置。",
                model=model,
                checkedAt=checked_at,
                latencyMs=None,
            )

        resolved_model = (model or self._default_probe_model(provider_id)).strip()
        if resolved_model == "":
            return AIProviderHealthDto(
                provider=provider_id,
                status="misconfigured",
                message="当前 Provider 暂无可用于诊断的模型。",
                model=None,
                checkedAt=checked_at,
                latencyMs=None,
            )

        probe = self._probe_provider_connectivity(runtime, resolved_model)
        return AIProviderHealthDto(
            provider=provider_id,
            status=str(probe["status"]),
            message=str(probe["message"]),
            model=resolved_model,
            checkedAt=checked_at,
            latencyMs=int(probe["latency_ms"]) if probe["latency_ms"] is not None else None,
        )

    def get_capability(self, capability_id: str) -> AICapabilityConfigDto:
        capabilities = {item.capabilityId: item for item in self.get_settings().capabilities}
        capability = capabilities.get(capability_id)
        if capability is None:
            raise HTTPException(status_code=404, detail="未找到 AI 能力配置。")
        return capability

    def get_provider_runtime_config(self, provider_id: str) -> ProviderRuntimeConfig:
        return self._get_catalog_runtime_config(provider_id)

    def _get_catalog_runtime_config(self, provider_id: str) -> ProviderRuntimeConfig:
        metadata = _get_provider_catalog_metadata(provider_id)
        base_urls = {item.provider_id: item.base_url for item in self._repository.load_provider_settings()}
        secret_key = self._secret_store.get(f"provider:{provider_id}:api_key")
        secret_source = "secure_store"
        if not secret_key:
            env_key = str(metadata["env_key"])
            env_value = os.getenv(env_key, "").strip() if env_key else ""
            secret_key = env_value or None
            secret_source = "env" if secret_key else "none"

        env_base_url = str(metadata["env_base_url"])
        base_url = (
            base_urls.get(provider_id, "")
            or (os.getenv(env_base_url, "").strip() if env_base_url else "")
            or str(metadata["default_base_url"])
        )
        return ProviderRuntimeConfig(
            provider=provider_id,
            label=str(metadata["label"]),
            api_key=secret_key,
            base_url=base_url,
            secret_source=secret_source,
            requires_secret=bool(metadata["requires_secret"]),
            supports_text_generation="text_generation" in metadata["capabilities"],
            supports_tts="tts" in metadata["capabilities"],
            protocol_family=_protocol_family_for(provider_id),
        )

    def _probe_provider_connectivity(
        self,
        runtime: ProviderRuntimeConfig,
        model: str,
    ) -> dict[str, object]:
        started_at = time.perf_counter()
        try:
            if runtime.provider == "openai" or runtime.base_url.rstrip("/").endswith("/responses"):
                _post_openai_responses_probe(
                    base_url=runtime.base_url,
                    api_key=runtime.api_key,
                    model=model,
                )
            elif runtime.provider == "anthropic":
                _post_anthropic_probe(
                    base_url=runtime.base_url,
                    api_key=runtime.api_key,
                    model=model,
                )
            elif runtime.provider == "gemini":
                _post_gemini_probe(
                    base_url=runtime.base_url,
                    api_key=runtime.api_key,
                    model=model,
                )
            elif runtime.provider == "cohere":
                _post_cohere_probe(
                    base_url=runtime.base_url,
                    api_key=runtime.api_key,
                    model=model,
                )
            else:
                _post_openai_compatible_probe(
                    base_url=runtime.base_url,
                    api_key=runtime.api_key,
                    model=model,
                )
        except ProviderConnectivityError as exc:
            return {
                "status": exc.status,
                "message": exc.message,
                "latency_ms": int((time.perf_counter() - started_at) * 1000),
            }
        except Exception:
            log.exception("AI Provider 健康检查失败 provider=%s model=%s", runtime.provider, model)
            return {
                "status": "offline",
                "message": "Provider 连通性测试失败，请检查网络、Base URL 或本地服务状态。",
                "latency_ms": int((time.perf_counter() - started_at) * 1000),
            }

        return {
            "status": "ready",
            "message": f"{runtime.label} / {model} 真实连通性测试通过。",
            "latency_ms": int((time.perf_counter() - started_at) * 1000),
        }

    def _model_catalog(self) -> list[AIModelCatalogItemDto]:
        models = {
            (item.provider, item.modelId): item
            for item in _static_model_catalog()
        }
        for item in self._repository.load_provider_models():
            dto = self._to_model_dto(item)
            models[(dto.provider, dto.modelId)] = dto
        return sorted(models.values(), key=lambda item: (item.provider, item.modelId))

    def _default_probe_model(self, provider_id: str) -> str:
        for item in self._model_catalog():
            if item.provider == provider_id and "text_generation" in item.capabilityTypes and item.enabled:
                return item.modelId
        return ""

    def _load_or_create_capabilities(self) -> list[StoredAICapabilityConfig]:
        stored = self._repository.load_capabilities()
        if stored:
            return sorted(stored, key=lambda item: CAPABILITY_IDS.index(item.capability_id))

        defaults = [
            StoredAICapabilityConfig(
                capability_id=capability_id,
                enabled=capability_id in {"script_generation", "script_rewrite", "storyboard_generation"},
                provider="openai",
                model="gpt-5" if capability_id == "script_generation" else "gpt-5-mini",
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

    def _to_model_dto(self, item: StoredAIProviderModel) -> AIModelCatalogItemDto:
        return AIModelCatalogItemDto(
            modelId=item.model_id,
            displayName=item.display_name,
            provider=item.provider_id,
            capabilityTypes=item.capability_kinds,
            inputModalities=item.input_modalities,
            outputModalities=item.output_modalities,
            contextWindow=item.context_window,
            defaultFor=item.default_for,
            enabled=item.enabled,
        )


def _provider_catalog_metadata() -> dict[str, dict[str, object]]:
    return {
        "openai": _catalog_item(
            "OpenAI",
            "commercial",
            "TK_OPS_OPENAI_API_KEY",
            "TK_OPS_OPENAI_BASE_URL",
            "https://api.openai.com/v1/responses",
            ["text_generation", "vision", "tts"],
        ),
        "openai_compatible": _catalog_item(
            "OpenAI-compatible",
            "openai_compatible",
            "TK_OPS_OPENAI_COMPATIBLE_API_KEY",
            "TK_OPS_OPENAI_COMPATIBLE_BASE_URL",
            "",
            ["text_generation", "vision"],
            requires_base_url=True,
        ),
        "anthropic": _catalog_item(
            "Anthropic",
            "commercial",
            "TK_OPS_ANTHROPIC_API_KEY",
            "TK_OPS_ANTHROPIC_BASE_URL",
            "https://api.anthropic.com/v1/messages",
            ["text_generation", "vision"],
        ),
        "gemini": _catalog_item(
            "Google Gemini",
            "commercial",
            "TK_OPS_GEMINI_API_KEY",
            "TK_OPS_GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/models",
            ["text_generation", "vision", "asset_analysis"],
        ),
        "deepseek": _catalog_item(
            "DeepSeek",
            "commercial",
            "TK_OPS_DEEPSEEK_API_KEY",
            "TK_OPS_DEEPSEEK_BASE_URL",
            "https://api.deepseek.com/v1",
            ["text_generation"],
        ),
        "qwen": _catalog_item(
            "Qwen",
            "commercial",
            "TK_OPS_QWEN_API_KEY",
            "TK_OPS_QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ["text_generation", "vision"],
        ),
        "kimi": _catalog_item(
            "Kimi",
            "commercial",
            "TK_OPS_KIMI_API_KEY",
            "TK_OPS_KIMI_BASE_URL",
            "https://api.moonshot.cn/v1",
            ["text_generation"],
        ),
        "zhipu": _catalog_item(
            "GLM",
            "commercial",
            "TK_OPS_ZHIPU_API_KEY",
            "TK_OPS_ZHIPU_BASE_URL",
            "https://open.bigmodel.cn/api/paas/v4",
            ["text_generation", "vision"],
        ),
        "openrouter": _catalog_item(
            "OpenRouter",
            "aggregator",
            "TK_OPS_OPENROUTER_API_KEY",
            "TK_OPS_OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
            ["text_generation", "vision"],
            supports_model_discovery=True,
        ),
        "ollama": _catalog_item(
            "Ollama",
            "local",
            "",
            "TK_OPS_OLLAMA_BASE_URL",
            "http://127.0.0.1:11434/v1",
            ["text_generation", "vision"],
            requires_secret=False,
            supports_model_discovery=True,
        ),
        "cohere": _catalog_item(
            "Cohere",
            "commercial",
            "TK_OPS_COHERE_API_KEY",
            "TK_OPS_COHERE_BASE_URL",
            "https://api.cohere.com/v2",
            ["text_generation"],
        ),
        "azure_speech": _catalog_item(
            "Azure Speech",
            "media",
            "TK_OPS_AZURE_SPEECH_KEY",
            "TK_OPS_AZURE_SPEECH_BASE_URL",
            "",
            ["tts"],
            requires_base_url=True,
        ),
        "elevenlabs": _catalog_item(
            "ElevenLabs",
            "media",
            "TK_OPS_ELEVENLABS_API_KEY",
            "TK_OPS_ELEVENLABS_BASE_URL",
            "https://api.elevenlabs.io/v1",
            ["tts"],
        ),
        "video_generation_provider": _catalog_item(
            "视频生成 Provider",
            "media",
            "",
            "",
            "",
            ["video_generation"],
            requires_secret=False,
        ),
        "asset_analysis_provider": _catalog_item(
            "资产分析 Provider",
            "media",
            "",
            "",
            "",
            ["asset_analysis"],
            requires_secret=False,
        ),
    }


def _catalog_item(
    label: str,
    kind: str,
    env_key: str,
    env_base_url: str,
    default_base_url: str,
    capabilities: list[str],
    *,
    requires_base_url: bool = False,
    requires_secret: bool = True,
    supports_model_discovery: bool = False,
) -> dict[str, object]:
    return {
        "label": label,
        "kind": kind,
        "env_key": env_key,
        "env_base_url": env_base_url,
        "default_base_url": default_base_url,
        "capabilities": capabilities,
        "requires_base_url": requires_base_url,
        "requires_secret": requires_secret,
        "supports_model_discovery": supports_model_discovery,
    }


def _get_provider_catalog_metadata(provider_id: str) -> dict[str, object]:
    metadata = _provider_catalog_metadata().get(provider_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="未找到 AI Provider。")
    return metadata


def _is_catalog_provider_configured(
    metadata: dict[str, object],
    runtime: ProviderRuntimeConfig,
) -> bool:
    if bool(metadata["requires_base_url"]) and runtime.base_url.strip() == "":
        return False
    if bool(metadata["requires_secret"]):
        return runtime.api_key is not None and runtime.api_key != ""
    return runtime.base_url.strip() != "" or not bool(metadata["requires_base_url"])


def _catalog_provider_status(
    metadata: dict[str, object],
    runtime: ProviderRuntimeConfig,
    configured: bool,
) -> str:
    if bool(metadata["requires_base_url"]) and runtime.base_url.strip() == "":
        return "misconfigured"
    if bool(metadata["requires_secret"]) and not configured:
        return "missing_secret"
    if not metadata["capabilities"]:
        return "unsupported"
    return "ready"


def _provider_health_error_code(status: str) -> str | None:
    if status == "ready":
        return None
    if status == "offline":
        return "provider.health.refresh_failed"
    return None


def _post_openai_responses_probe(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
) -> None:
    endpoint = _normalize_endpoint(base_url, "/responses")
    _request_json(
        endpoint,
        headers=_build_headers(api_key),
        payload={"model": model, "input": "ping", "max_output_tokens": 8},
    )


def _post_openai_compatible_probe(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
) -> None:
    endpoint = _normalize_endpoint(base_url, "/chat/completions")
    _request_json(
        endpoint,
        headers=_build_headers(api_key),
        payload={
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 8,
        },
    )


def _post_anthropic_probe(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
) -> None:
    endpoint = _normalize_endpoint(base_url, "/messages")
    headers = {"anthropic-version": "2023-06-01", "content-type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    _request_json(
        endpoint,
        headers=headers,
        payload={"model": model, "max_tokens": 8, "messages": [{"role": "user", "content": "ping"}]},
    )


def _post_gemini_probe(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
) -> None:
    if not api_key:
        raise ProviderConnectivityError(status="missing_secret", message="Gemini API Key 尚未配置。")
    endpoint_root = base_url.rstrip("/")
    if not endpoint_root.endswith("/models"):
        endpoint_root = f"{endpoint_root}/models"
    endpoint = (
        f"{endpoint_root}/{urllib.parse.quote(model, safe='')}"
        f":generateContent?key={urllib.parse.quote(api_key, safe='')}"
    )
    _request_json(
        endpoint,
        headers={"content-type": "application/json"},
        payload={"contents": [{"parts": [{"text": "ping"}]}]},
    )


def _post_cohere_probe(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
) -> None:
    endpoint = _normalize_endpoint(base_url, "/chat")
    _request_json(
        endpoint,
        headers=_build_headers(api_key),
        payload={"model": model, "message": "ping", "max_tokens": 8},
    )


def _request_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, object],
) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8") if response.length != 0 else ""
    except urllib.error.HTTPError as exc:
        raise ProviderConnectivityError(
            status="misconfigured" if exc.code < 500 else "offline",
            message=f"远端返回 HTTP {exc.code}：{_extract_remote_message(exc)}",
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderConnectivityError(
            status="offline",
            message="无法连接到 Provider，请检查网络、Base URL 或本地服务状态。",
        ) from exc

    if not body.strip():
        return {}

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _build_headers(api_key: str | None) -> dict[str, str]:
    headers = {"content-type": "application/json"}
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    return headers


def _normalize_endpoint(base_url: str, suffix: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith(suffix):
        return normalized
    return f"{normalized}{suffix}"


def _extract_remote_message(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except Exception:
        return "请求被远端拒绝。"

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        snippet = body.strip().replace("\n", " ")
        return snippet[:120] if snippet else "请求被远端拒绝。"

    if isinstance(payload, dict):
        if isinstance(payload.get("error"), dict):
            message = payload["error"].get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:120]
        error_value = payload.get("error")
        if isinstance(error_value, str) and error_value.strip():
            return error_value.strip()[:120]
        message_value = payload.get("message")
        if isinstance(message_value, str) and message_value.strip():
            return message_value.strip()[:120]
    return "请求被远端拒绝。"


def _capability_type_for(capability_id: str) -> str:
    return {
        "script_generation": "text_generation",
        "script_rewrite": "text_generation",
        "storyboard_generation": "text_generation",
        "tts_generation": "tts",
        "subtitle_alignment": "subtitle_alignment",
        "video_generation": "video_generation",
        "asset_analysis": "asset_analysis",
    }[capability_id]


def _static_model_catalog() -> list[AIModelCatalogItemDto]:
    return [
        _model("openai", "gpt-5", "GPT-5", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation"]),
        _model("openai", "gpt-5.4", "GPT-5.4", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "script_rewrite", "storyboard_generation"]),
        _model("openai", "gpt-5-mini", "GPT-5 Mini", ["text_generation"], ["text"], ["text"], ["script_rewrite"]),
        _model("openai", "gpt-4o-mini-tts", "GPT-4o Mini TTS", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("anthropic", "claude-sonnet", "Claude Sonnet", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "script_rewrite"]),
        _model("gemini", "gemini-pro", "Gemini Pro", ["text_generation", "vision", "asset_analysis"], ["text", "image", "video"], ["text"], ["storyboard_generation", "asset_analysis"]),
        _model("deepseek", "deepseek-chat", "DeepSeek Chat", ["text_generation"], ["text"], ["text"], ["script_generation", "script_rewrite"]),
        _model("qwen", "qwen-plus", "Qwen Plus", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "storyboard_generation"]),
        _model("kimi", "moonshot-v1", "Kimi", ["text_generation"], ["text"], ["text"], ["script_rewrite"]),
        _model("zhipu", "glm-4", "GLM-4", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation"]),
        _model("cohere", "command-r-plus", "Command R+", ["text_generation"], ["text"], ["text"], ["script_rewrite"]),
        _model("openrouter", "openrouter/auto", "OpenRouter Auto", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "storyboard_generation"]),
        _model("ollama", "llama3.1", "Llama 3.1", ["text_generation"], ["text"], ["text"], ["script_generation"]),
        _model("ollama", "llava", "LLaVA", ["text_generation", "vision"], ["text", "image"], ["text"], ["asset_analysis"]),
        _model("azure_speech", "azure-neural-voice", "Azure Neural Voice", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("elevenlabs", "eleven-multilingual", "Eleven Multilingual", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("video_generation_provider", "video-default", "默认视频生成模型", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("asset_analysis_provider", "asset-analysis-default", "默认资产分析模型", ["asset_analysis"], ["text", "image", "video"], ["text"], ["asset_analysis"]),
        _model("openai_compatible", "custom-compatible-model", "自定义兼容模型", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "storyboard_generation"]),
    ]


def _model(
    provider: str,
    model_id: str,
    display_name: str,
    capability_types: list[str],
    input_modalities: list[str],
    output_modalities: list[str],
    default_for: list[str],
) -> AIModelCatalogItemDto:
    return AIModelCatalogItemDto(
        modelId=model_id,
        displayName=display_name,
        provider=provider,
        capabilityTypes=capability_types,
        inputModalities=input_modalities,
        outputModalities=output_modalities,
        contextWindow=None,
        defaultFor=default_for,
        enabled=True,
    )


def _default_agent_role(capability_id: str) -> str:
    return {
        "script_generation": "资深短视频脚本策划",
        "script_rewrite": "短视频脚本改写编辑",
        "storyboard_generation": "分镜规划导演",
        "tts_generation": "配音导演",
        "subtitle_alignment": "字幕对齐编辑",
        "video_generation": "视频生成导演",
        "asset_analysis": "素材分析师",
    }[capability_id]


def _default_system_prompt(capability_id: str) -> str:
    return {
        "script_generation": "围绕用户主题生成高留存、可拍摄的短视频脚本。",
        "script_rewrite": "在保持原意的前提下提升脚本节奏、开场和转化效率。",
        "storyboard_generation": "把脚本文本拆解为清晰的镜头与视觉提示。",
        "tts_generation": "为脚本生成适合配音的语气和节奏说明。",
        "subtitle_alignment": "让字幕语言和节奏更适合短视频表达。",
        "video_generation": "把分镜转成可执行的视频生成提示。",
        "asset_analysis": "总结素材内容、价值点和可复用结构。",
    }[capability_id]


def _default_template(capability_id: str) -> str:
    return {
        "script_generation": "主题：{{topic}}",
        "script_rewrite": "原脚本：\n{{script}}\n\n改写要求：{{instructions}}",
        "storyboard_generation": "脚本内容：\n{{script}}",
        "tts_generation": "脚本内容：\n{{script}}",
        "subtitle_alignment": "脚本内容：\n{{script}}",
        "video_generation": "分镜内容：\n{{storyboard}}",
        "asset_analysis": "素材内容：\n{{assets}}",
    }[capability_id]


def _mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"


def _protocol_family_for(provider_id: str) -> str:
    if provider_id == "openai":
        return "openai_responses"
    if provider_id == "anthropic":
        return "anthropic_messages"
    if provider_id == "gemini":
        return "gemini_generate"
    if provider_id == "cohere":
        return "cohere_chat"
    if provider_id in {
        "openai_compatible",
        "deepseek",
        "qwen",
        "kimi",
        "zhipu",
        "openrouter",
        "ollama",
    }:
        return "openai_chat"
    if provider_id in {"azure_speech", "elevenlabs"}:
        return "tts_openai"
    return "unknown"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
