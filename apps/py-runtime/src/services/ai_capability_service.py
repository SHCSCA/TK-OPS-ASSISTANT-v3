from __future__ import annotations

import asyncio
import json
import logging
import os
import re
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
    AIDiagnosticSummaryDto,
    AICapabilityConfigDto,
    AICapabilityChangedEventDto,
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
from services.ai_default_prompts import (
    default_agent_role as _default_agent_role_from_config,
    default_system_prompt as _default_system_prompt_from_config,
    default_user_prompt_template as _default_user_prompt_template_from_config,
)
from services.ws_manager import ws_manager

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
    supports_speech_to_text: bool = False


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
        provider_statuses = self.get_provider_statuses()
        return AICapabilitySettingsDto(
            capabilities=[self._to_capability_dto(item) for item in capabilities],
            providers=provider_statuses,
            configVersion=self._resolve_settings_version(capabilities),
            scope="runtime_local",
            diagnosticSummary=self._build_diagnostic_summary(provider_statuses),
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
                agent_role=_default_agent_role(item.capabilityId),
                system_prompt=_default_system_prompt(item.capabilityId),
                user_prompt_template=_default_template(item.capabilityId),
                updated_at=_utc_now(),
            )
            for item in items
        ]
        self._repository.save_capabilities(stored)
        settings = self.get_settings()
        self._broadcast_ai_capability_changed(
            settings=settings,
            reason="capability_config_updated",
            provider_ids=sorted({item.provider for item in items}),
            capability_ids=sorted(provided_ids),
        )
        return settings

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
        settings = self.get_settings()
        self._broadcast_ai_capability_changed(
            settings=settings,
            reason="provider_secret_updated",
            provider_ids=[provider_id],
            capability_ids=self._capability_ids_for_provider(provider_id),
        )
        return self.get_provider_status(provider_id)

    def get_provider_statuses(self) -> list[AIProviderSecretStatusDto]:
        snapshots = {
            item.provider_id: item
            for item in self._repository.load_provider_health_snapshots()
        }
        return [
            self.get_provider_status(provider_id, snapshots=snapshots)
            for provider_id in _provider_catalog_metadata()
        ]

    def get_provider_status(
        self,
        provider_id: str,
        *,
        snapshots: dict[str, StoredAIProviderHealth] | None = None,
    ) -> AIProviderSecretStatusDto:
        metadata = _get_provider_catalog_metadata(provider_id)
        runtime = self.get_provider_runtime_config(provider_id)
        configured = _is_catalog_provider_configured(metadata, runtime)
        snapshot = None if snapshots is None else snapshots.get(provider_id)
        readiness = snapshot.readiness if snapshot is not None else ("not_checked" if configured else "not_configured")
        return AIProviderSecretStatusDto(
            provider=provider_id,
            label=str(metadata["label"]),
            configured=configured,
            maskedSecret=_mask_secret(runtime.api_key),
            baseUrl=runtime.base_url,
            secretSource=runtime.secret_source,
            supportsTextGeneration="text_generation" in metadata["capabilities"],
            readiness=readiness,
            lastCheckedAt=snapshot.last_checked_at if snapshot is not None else None,
            errorCode=snapshot.error_code if snapshot is not None else None,
            errorMessage=snapshot.error_message if snapshot is not None else None,
            scope="runtime_local",
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
            region=str(metadata["region"]),
            category=str(metadata["category"]),
            protocol=str(metadata["protocol"]),
            modelSyncMode=str(metadata["model_sync_mode"]),
            tags=list(metadata["tags"]),
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
        settings = self.get_settings()
        self._broadcast_ai_capability_changed(
            settings=settings,
            reason="provider_health_refreshed",
            provider_ids=sorted(_provider_catalog_metadata()),
            capability_ids=list(CAPABILITY_IDS),
        )
        return self.get_provider_health_overview()

    def _broadcast_ai_capability_changed(
        self,
        *,
        settings: AICapabilitySettingsDto,
        reason: str,
        provider_ids: list[str],
        capability_ids: list[str],
    ) -> None:
        event = AICapabilityChangedEventDto(
            scope=settings.scope,
            configVersion=settings.configVersion,
            reason=reason,
            providerIds=sorted({provider_id for provider_id in provider_ids if provider_id}),
            capabilityIds=sorted({capability_id for capability_id in capability_ids if capability_id}),
        )
        self._broadcast_event(event.model_dump(mode="json"))

    def _broadcast_event(self, event: dict[str, object]) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(ws_manager.broadcast(event))
        else:
            asyncio.create_task(ws_manager.broadcast(event))

    def _capability_ids_for_provider(self, provider_id: str) -> list[str]:
        return sorted(
            {
                item.capabilityId
                for item in self.get_settings().capabilities
                if item.provider == provider_id
            }
        )

    def _capability_ids_for_model(self, payload: AIProviderModelUpsertInput) -> list[str]:
        capability_ids = {
            capability_id
            for capability_id in payload.defaultFor
            if capability_id in CAPABILITY_IDS
        }
        capability_types = {kind.strip() for kind in payload.capabilityKinds if kind.strip()}
        for capability_id in CAPABILITY_IDS:
            if _capability_type_for(capability_id) in capability_types:
                capability_ids.add(capability_id)
        return sorted(capability_ids)

    def _resolve_settings_version(
        self,
        capabilities: list[StoredAICapabilityConfig],
    ) -> str:
        provider_settings = self._repository.load_provider_settings()
        timestamps = [item.updated_at for item in capabilities]
        timestamps.extend(item.updated_at for item in provider_settings)
        timestamps.extend(item.updated_at for item in self._repository.load_provider_models())
        return max(timestamps, default=_utc_now())

    def _build_diagnostic_summary(
        self,
        providers: list[AIProviderSecretStatusDto],
    ) -> AIDiagnosticSummaryDto:
        configured = sum(1 for item in providers if item.configured)
        ready = sum(1 for item in providers if item.readiness == "ready")
        degraded = sum(
            1
            for item in providers
            if item.readiness in {"offline", "refresh_failed", "unsupported", "degraded"}
        )
        last_refresh = max((item.lastCheckedAt for item in providers if item.lastCheckedAt), default=None)
        return AIDiagnosticSummaryDto(
            configuredProviderCount=configured,
            readyProviderCount=ready,
            degradedProviderCount=degraded,
            lastHealthRefreshAt=last_refresh,
        )

    def get_provider_models(self, provider_id: str) -> list[AIModelCatalogItemDto]:
        _get_provider_catalog_metadata(provider_id)
        return [item for item in self._model_catalog() if item.provider == provider_id and item.enabled]

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
        receipt = AIProviderModelWriteReceiptDto(
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
        settings = self.get_settings()
        self._broadcast_ai_capability_changed(
            settings=settings,
            reason="provider_model_upserted",
            provider_ids=[provider_id],
            capability_ids=self._capability_ids_for_model(payload),
        )
        return receipt

    def refresh_provider_models(self, provider_id: str) -> AIModelCatalogRefreshResultDto:
        metadata = _get_provider_catalog_metadata(provider_id)
        if not bool(metadata["supports_model_discovery"]):
            return AIModelCatalogRefreshResultDto(
                provider=provider_id,
                status="static_catalog",
                message="当前 Provider 的模型目录仍使用内置注册表，暂不支持远端刷新。",
            )

        runtime = self.get_provider_runtime_config(provider_id)
        if bool(metadata["requires_base_url"]) and runtime.base_url.strip() == "":
            raise RuntimeHTTPException(
                status_code=400,
                detail="当前 Provider 必须先配置 Base URL，无法执行模型刷新。",
                error_code="provider.model.refresh_missing_base_url",
            )
        if bool(metadata["requires_secret"]) and not runtime.api_key:
            raise RuntimeHTTPException(
                status_code=400,
                detail="当前 Provider 尚未配置 API Key，无法执行模型刷新。",
                error_code="provider.model.refresh_missing_secret",
            )

        discovered = self._fetch_remote_provider_models(provider_id, runtime)
        if not discovered:
            raise RuntimeHTTPException(
                status_code=502,
                detail="远端模型目录未返回有效模型，请稍后重试。",
                error_code="provider.model.refresh_failed",
            )

        saved_count = 0
        disabled_models = {
            item.model_id
            for item in self._repository.load_provider_models(provider_id=provider_id)
            if not item.enabled
        }
        for item in discovered:
            if item.model_id in disabled_models:
                item = StoredAIProviderModel(
                    provider_id=item.provider_id,
                    model_id=item.model_id,
                    display_name=item.display_name,
                    capability_kinds=item.capability_kinds,
                    input_modalities=item.input_modalities,
                    output_modalities=item.output_modalities,
                    context_window=item.context_window,
                    default_for=item.default_for,
                    enabled=False,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            self._repository.upsert_provider_model(item)
            saved_count += 1

        settings = self.get_settings()
        self._broadcast_ai_capability_changed(
            settings=settings,
            reason="provider_models_refreshed",
            provider_ids=[provider_id],
            capability_ids=self._capability_ids_for_provider(provider_id),
        )
        return AIModelCatalogRefreshResultDto(
            provider=provider_id,
            status="refreshed",
            message=f"已从远端刷新 {saved_count} 个模型。",
        )

    def _fetch_remote_provider_models(
        self,
        provider_id: str,
        runtime: ProviderRuntimeConfig,
    ) -> list[StoredAIProviderModel]:
        if provider_id == "openrouter":
            return _fetch_openrouter_models(runtime)
        if provider_id == "ollama":
            return _fetch_ollama_models(runtime)
        metadata = _get_provider_catalog_metadata(provider_id)
        if metadata.get("protocol") == "openai_chat":
            return _fetch_openai_compatible_models(runtime)
        raise RuntimeHTTPException(
            status_code=400,
            detail="当前 Provider 暂不支持远端模型刷新。",
            error_code="provider.model.refresh_not_supported",
        )

    def get_capability_support_matrix(self) -> AICapabilitySupportMatrixDto:
        models = [item for item in self._model_catalog() if item.enabled]
        items: list[AICapabilitySupportItemDto] = []
        for capability_id in CAPABILITY_IDS:
            supported = [
                model
                for model in models
                if _model_supports_capability(model, capability_id)
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

        requested_model = (model or self._default_probe_model(provider_id)).strip()
        resolved_model = self.resolve_provider_model_id(
            provider_id,
            requested_model,
            required_capability_type="text_generation",
        )
        if resolved_model == "":
            return AIProviderHealthDto(
                provider=provider_id,
                status="misconfigured",
                message="当前 Provider 暂无可用于诊断的模型。",
                model=None,
                checkedAt=checked_at,
                latencyMs=None,
            )

        model_info = self._find_model(provider_id, resolved_model)
        if model_info is not None and "text_generation" not in model_info.capabilityTypes:
            return AIProviderHealthDto(
                provider=provider_id,
                status="unsupported",
                message="当前模型不是文本模型，暂不能用于通用连接检查；请改用文本模型或在对应能力中单独验证。",
                model=resolved_model,
                checkedAt=checked_at,
                latencyMs=None,
            )

        probe = self._probe_provider_connectivity(runtime, resolved_model)
        message = str(probe["message"])
        if _is_model_access_denied_message(message) and self._disable_provider_model(provider_id, resolved_model):
            message = f"{message} 已从可选模型中屏蔽，请刷新模型目录或改用已有权限的模型。"
            settings = self.get_settings()
            self._broadcast_ai_capability_changed(
                settings=settings,
                reason="provider_model_disabled",
                provider_ids=[provider_id],
                capability_ids=list(CAPABILITY_IDS),
            )
        return AIProviderHealthDto(
            provider=provider_id,
            status=str(probe["status"]),
            message=message,
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

    def resolve_provider_model_id(
        self,
        provider_id: str,
        model_id: str,
        *,
        capability_id: str | None = None,
        required_capability_type: str | None = None,
    ) -> str:
        requested_model = model_id.strip()
        if requested_model == "":
            return ""

        required_type = required_capability_type
        if required_type is None and capability_id in CAPABILITY_IDS:
            required_type = _capability_type_for(capability_id)

        enabled_models = [
            item
            for item in self._model_catalog()
            if item.provider == provider_id and item.enabled
        ]
        exact_enabled = next(
            (item for item in enabled_models if item.modelId == requested_model),
            None,
        )
        if exact_enabled is not None:
            return exact_enabled.modelId

        candidates = _resolve_model_alias_candidates(
            enabled_models,
            requested_model,
            required_capability_type=required_type,
        )
        if candidates:
            return candidates[0].modelId
        return requested_model

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
            supports_speech_to_text="speech_to_text" in metadata["capabilities"],
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
        static_models = _static_model_catalog()
        models = {
            (item.provider, item.modelId): item
            for item in static_models
        }
        remote_models = [
            self._to_model_dto(item)
            for item in self._repository.load_provider_models()
        ]
        for dto in remote_models:
            models[(dto.provider, dto.modelId)] = dto
        for item in static_models:
            key = (item.provider, item.modelId)
            current = models.get(key)
            if current is None or not current.enabled:
                continue
            if _is_static_model_superseded(item, remote_models):
                models.pop(key, None)
        return sorted(models.values(), key=lambda item: (item.provider, item.modelId))

    def _default_probe_model(self, provider_id: str) -> str:
        for item in self._model_catalog():
            if item.provider == provider_id and "text_generation" in item.capabilityTypes and item.enabled:
                return item.modelId
        return ""

    def _find_model(self, provider_id: str, model_id: str) -> AIModelCatalogItemDto | None:
        return next(
            (
                item
                for item in self._model_catalog()
                if item.provider == provider_id and item.modelId == model_id
            ),
            None,
        )

    def _disable_provider_model(self, provider_id: str, model_id: str) -> bool:
        model = self._find_model(provider_id, model_id)
        if model is None:
            return False

        now = _utc_now()
        self._repository.upsert_provider_model(
            StoredAIProviderModel(
                provider_id=model.provider,
                model_id=model.modelId,
                display_name=model.displayName,
                capability_kinds=model.capabilityTypes,
                input_modalities=model.inputModalities,
                output_modalities=model.outputModalities,
                context_window=model.contextWindow,
                default_for=model.defaultFor,
                enabled=False,
                created_at=now,
                updated_at=now,
            )
        )
        log.warning("AI Provider 模型被屏蔽 provider=%s model=%s", provider_id, model_id)
        return True

    def _load_or_create_capabilities(self) -> list[StoredAICapabilityConfig]:
        stored = self._repository.load_capabilities()
        if stored:
            known_stored = [item for item in stored if item.capability_id in CAPABILITY_IDS]
            configs_by_id = {
                item.capability_id: _with_default_prompt_fields(item)
                for item in known_stored
            }
            changed = len(known_stored) != len(stored)
            for capability_id in CAPABILITY_IDS:
                if capability_id not in configs_by_id:
                    configs_by_id[capability_id] = _default_capability_config(capability_id)
                    changed = True
            migrated = [configs_by_id[capability_id] for capability_id in CAPABILITY_IDS]
            if changed or migrated != stored:
                migrated = self._repository.save_capabilities(migrated)
            return migrated

        defaults = [
            _default_capability_config(capability_id)
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
            promptPreview={
                'agentRole': item.agent_role,
                'systemPrompt': item.system_prompt,
                'userPromptTemplate': item.user_prompt_template,
                'editable': False,
                'source': 'system_default',
            },
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


def _default_capability_config(capability_id: str) -> StoredAICapabilityConfig:
    return StoredAICapabilityConfig(
        capability_id=capability_id,
        enabled=capability_id in {"script_generation", "script_rewrite", "storyboard_generation"},
        provider=_default_provider_for_capability(capability_id),
        model=_default_model_for_capability(capability_id),
        agent_role=_default_agent_role(capability_id),
        system_prompt=_default_system_prompt(capability_id),
        user_prompt_template=_default_template(capability_id),
        updated_at=_utc_now(),
    )


def _default_provider_for_capability(capability_id: str) -> str:
    if capability_id == "asset_analysis":
        return "volcengine"
    if capability_id == "video_transcription":
        return "openai"
    return "openai"


def _default_model_for_capability(capability_id: str) -> str:
    if capability_id == "script_generation":
        return "gpt-5"
    if capability_id == "asset_analysis":
        return "doubao-seed-2.0-pro"
    if capability_id == "video_transcription":
        return "whisper-1"
    return "gpt-5-mini"


def _provider_catalog_metadata() -> dict[str, dict[str, object]]:
    return {
        "openai": _catalog_item(
            "OpenAI",
            "commercial",
            "TK_OPS_OPENAI_API_KEY",
            "TK_OPS_OPENAI_BASE_URL",
            "https://api.openai.com/v1/responses",
            ["text_generation", "vision", "tts", "speech_to_text"],
            category="model_hub",
            protocol="openai_responses",
            tags=["国际", "文本", "视觉", "TTS"],
        ),
        "openai_compatible": _catalog_item(
            "OpenAI-compatible",
            "openai_compatible",
            "TK_OPS_OPENAI_COMPATIBLE_API_KEY",
            "TK_OPS_OPENAI_COMPATIBLE_BASE_URL",
            "",
            ["text_generation", "vision", "speech_to_text"],
            requires_base_url=True,
            supports_model_discovery=True,
            category="custom",
            protocol="openai_chat",
            region="custom",
            tags=["自定义", "OpenAI 兼容", "文本", "视觉"],
        ),
        "anthropic": _catalog_item(
            "Anthropic",
            "commercial",
            "TK_OPS_ANTHROPIC_API_KEY",
            "TK_OPS_ANTHROPIC_BASE_URL",
            "https://api.anthropic.com/v1/messages",
            ["text_generation", "vision"],
            category="text",
            protocol="anthropic_messages",
            tags=["国际", "文本", "视觉"],
        ),
        "gemini": _catalog_item(
            "Google Gemini",
            "commercial",
            "TK_OPS_GEMINI_API_KEY",
            "TK_OPS_GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/models",
            ["text_generation", "vision", "asset_analysis"],
            category="model_hub",
            protocol="gemini_generate",
            tags=["国际", "文本", "视觉", "素材"],
        ),
        "deepseek": _catalog_item(
            "DeepSeek",
            "commercial",
            "TK_OPS_DEEPSEEK_API_KEY",
            "TK_OPS_DEEPSEEK_BASE_URL",
            "https://api.deepseek.com/v1",
            ["text_generation"],
            region="domestic",
            category="text",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本", "推理"],
        ),
        "qwen": _catalog_item(
            "通义千问",
            "commercial",
            "TK_OPS_QWEN_API_KEY",
            "TK_OPS_QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ["text_generation", "vision"],
            region="domestic",
            category="model_hub",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本", "视觉"],
        ),
        "kimi": _catalog_item(
            "Kimi",
            "commercial",
            "TK_OPS_KIMI_API_KEY",
            "TK_OPS_KIMI_BASE_URL",
            "https://api.moonshot.cn/v1",
            ["text_generation"],
            region="domestic",
            category="text",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本", "长上下文"],
        ),
        "zhipu": _catalog_item(
            "智谱 GLM",
            "commercial",
            "TK_OPS_ZHIPU_API_KEY",
            "TK_OPS_ZHIPU_BASE_URL",
            "https://open.bigmodel.cn/api/paas/v4",
            ["text_generation", "vision"],
            region="domestic",
            category="model_hub",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本", "视觉"],
        ),
        "volcengine": _catalog_item(
            "火山方舟",
            "commercial",
            "TK_OPS_VOLCENGINE_API_KEY",
            "TK_OPS_VOLCENGINE_BASE_URL",
            "https://ark.cn-beijing.volces.com/api/v3",
            ["text_generation", "vision", "asset_analysis", "video_generation", "tts"],
            region="domestic",
            category="model_hub",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本", "视觉", "视频理解", "视频", "TTS"],
        ),
        "baidu_qianfan": _catalog_item(
            "百度千帆",
            "commercial",
            "TK_OPS_BAIDU_QIANFAN_API_KEY",
            "TK_OPS_BAIDU_QIANFAN_BASE_URL",
            "https://qianfan.baidubce.com/v2",
            ["text_generation", "vision"],
            region="domestic",
            category="model_hub",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本", "视觉"],
        ),
        "tencent_hunyuan": _catalog_item(
            "腾讯混元",
            "commercial",
            "TK_OPS_TENCENT_HUNYUAN_API_KEY",
            "TK_OPS_TENCENT_HUNYUAN_BASE_URL",
            "https://api.hunyuan.cloud.tencent.com/v1",
            ["text_generation", "vision"],
            region="domestic",
            category="model_hub",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本", "视觉"],
        ),
        "xunfei_spark": _catalog_item(
            "讯飞星火",
            "commercial",
            "TK_OPS_XUNFEI_SPARK_API_KEY",
            "TK_OPS_XUNFEI_SPARK_BASE_URL",
            "",
            ["text_generation", "vision"],
            region="domestic",
            category="model_hub",
            protocol="openai_chat",
            requires_base_url=True,
            supports_model_discovery=True,
            tags=["国内", "文本", "视觉"],
        ),
        "minimax": _catalog_item(
            "MiniMax",
            "commercial",
            "TK_OPS_MINIMAX_API_KEY",
            "TK_OPS_MINIMAX_BASE_URL",
            "",
            ["text_generation", "tts", "video_generation"],
            region="domestic",
            category="model_hub",
            protocol="openai_chat",
            requires_base_url=True,
            supports_model_discovery=True,
            tags=["国内", "文本", "视频", "TTS"],
        ),
        "baichuan": _catalog_item(
            "百川智能",
            "commercial",
            "TK_OPS_BAICHUAN_API_KEY",
            "TK_OPS_BAICHUAN_BASE_URL",
            "https://api.baichuan-ai.com/v1",
            ["text_generation"],
            region="domestic",
            category="text",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本"],
        ),
        "lingyi": _catalog_item(
            "零一万物",
            "commercial",
            "TK_OPS_LINGYI_API_KEY",
            "TK_OPS_LINGYI_BASE_URL",
            "https://api.lingyiwanwu.com/v1",
            ["text_generation"],
            region="domestic",
            category="text",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本"],
        ),
        "stepfun": _catalog_item(
            "阶跃星辰",
            "commercial",
            "TK_OPS_STEPFUN_API_KEY",
            "TK_OPS_STEPFUN_BASE_URL",
            "https://api.stepfun.com/v1",
            ["text_generation", "vision"],
            region="domestic",
            category="model_hub",
            protocol="openai_chat",
            supports_model_discovery=True,
            tags=["国内", "文本", "视觉"],
        ),
        "sensecore": _catalog_item(
            "商汤日日新",
            "commercial",
            "TK_OPS_SENSECORE_API_KEY",
            "TK_OPS_SENSECORE_BASE_URL",
            "",
            ["text_generation", "vision"],
            region="domestic",
            category="model_hub",
            protocol="openai_chat",
            requires_base_url=True,
            supports_model_discovery=True,
            tags=["国内", "文本", "视觉"],
        ),
        "openrouter": _catalog_item(
            "OpenRouter",
            "aggregator",
            "TK_OPS_OPENROUTER_API_KEY",
            "TK_OPS_OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
            ["text_generation", "vision"],
            supports_model_discovery=True,
            category="aggregator",
            protocol="openai_chat",
            tags=["聚合", "文本", "视觉"],
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
            region="local",
            category="local",
            protocol="openai_chat",
            tags=["本地", "文本", "视觉"],
        ),
        "cohere": _catalog_item(
            "Cohere",
            "commercial",
            "TK_OPS_COHERE_API_KEY",
            "TK_OPS_COHERE_BASE_URL",
            "https://api.cohere.com/v2",
            ["text_generation"],
            category="text",
            protocol="cohere_chat",
            tags=["国际", "文本"],
        ),
        "azure_speech": _catalog_item(
            "Azure Speech",
            "media",
            "TK_OPS_AZURE_SPEECH_KEY",
            "TK_OPS_AZURE_SPEECH_BASE_URL",
            "",
            ["tts"],
            requires_base_url=True,
            category="tts",
            protocol="tts_openai",
            model_sync_mode="manual",
            tags=["国际", "TTS"],
        ),
        "elevenlabs": _catalog_item(
            "ElevenLabs",
            "media",
            "TK_OPS_ELEVENLABS_API_KEY",
            "TK_OPS_ELEVENLABS_BASE_URL",
            "https://api.elevenlabs.io/v1",
            ["tts"],
            category="tts",
            protocol="manual_catalog",
            model_sync_mode="manual",
            tags=["国际", "TTS"],
        ),
        "aliyun_tts": _catalog_item(
            "阿里云语音",
            "media",
            "TK_OPS_ALIYUN_TTS_API_KEY",
            "TK_OPS_ALIYUN_TTS_BASE_URL",
            "",
            ["tts"],
            region="domestic",
            category="tts",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "TTS"],
        ),
        "tencent_tts": _catalog_item(
            "腾讯云语音",
            "media",
            "TK_OPS_TENCENT_TTS_API_KEY",
            "TK_OPS_TENCENT_TTS_BASE_URL",
            "",
            ["tts"],
            region="domestic",
            category="tts",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "TTS"],
        ),
        "baidu_tts": _catalog_item(
            "百度智能语音",
            "media",
            "TK_OPS_BAIDU_TTS_API_KEY",
            "TK_OPS_BAIDU_TTS_BASE_URL",
            "",
            ["tts"],
            region="domestic",
            category="tts",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "TTS"],
        ),
        "xunfei_tts": _catalog_item(
            "讯飞语音",
            "media",
            "TK_OPS_XUNFEI_TTS_API_KEY",
            "TK_OPS_XUNFEI_TTS_BASE_URL",
            "",
            ["tts"],
            region="domestic",
            category="tts",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "TTS"],
        ),
        "volcengine_asr": _catalog_item(
            "火山语音识别",
            "media",
            "TK_OPS_VOLCENGINE_ASR_API_KEY",
            "TK_OPS_VOLCENGINE_ASR_BASE_URL",
            "",
            ["speech_to_text"],
            region="domestic",
            category="speech_to_text",
            protocol="domestic_asr",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "转录", "语音识别"],
        ),
        "aliyun_asr": _catalog_item(
            "阿里云语音识别",
            "media",
            "TK_OPS_ALIYUN_ASR_API_KEY",
            "TK_OPS_ALIYUN_ASR_BASE_URL",
            "",
            ["speech_to_text"],
            region="domestic",
            category="speech_to_text",
            protocol="domestic_asr",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "转录", "语音识别"],
        ),
        "tencent_asr": _catalog_item(
            "腾讯云语音识别",
            "media",
            "TK_OPS_TENCENT_ASR_API_KEY",
            "TK_OPS_TENCENT_ASR_BASE_URL",
            "",
            ["speech_to_text"],
            region="domestic",
            category="speech_to_text",
            protocol="domestic_asr",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "转录", "语音识别"],
        ),
        "baidu_asr": _catalog_item(
            "百度语音识别",
            "media",
            "TK_OPS_BAIDU_ASR_API_KEY",
            "TK_OPS_BAIDU_ASR_BASE_URL",
            "",
            ["speech_to_text"],
            region="domestic",
            category="speech_to_text",
            protocol="domestic_asr",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "转录", "语音识别"],
        ),
        "xunfei_asr": _catalog_item(
            "讯飞语音转写",
            "media",
            "TK_OPS_XUNFEI_ASR_API_KEY",
            "TK_OPS_XUNFEI_ASR_BASE_URL",
            "",
            ["speech_to_text"],
            region="domestic",
            category="speech_to_text",
            protocol="domestic_asr",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "转录", "语音识别"],
        ),
        "kling": _catalog_item(
            "可灵",
            "media",
            "TK_OPS_KLING_API_KEY",
            "TK_OPS_KLING_BASE_URL",
            "",
            ["video_generation"],
            region="domestic",
            category="video",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "视频"],
        ),
        "jimeng": _catalog_item(
            "即梦",
            "media",
            "TK_OPS_JIMENG_API_KEY",
            "TK_OPS_JIMENG_BASE_URL",
            "",
            ["video_generation"],
            region="domestic",
            category="video",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "视频"],
        ),
        "wanxiang": _catalog_item(
            "通义万相",
            "media",
            "TK_OPS_WANXIANG_API_KEY",
            "TK_OPS_WANXIANG_BASE_URL",
            "",
            ["video_generation"],
            region="domestic",
            category="video",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "视频"],
        ),
        "vidu": _catalog_item(
            "Vidu",
            "media",
            "TK_OPS_VIDU_API_KEY",
            "TK_OPS_VIDU_BASE_URL",
            "",
            ["video_generation"],
            region="domestic",
            category="video",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "视频"],
        ),
        "hailuo": _catalog_item(
            "海螺",
            "media",
            "TK_OPS_HAILUO_API_KEY",
            "TK_OPS_HAILUO_BASE_URL",
            "",
            ["video_generation"],
            region="domestic",
            category="video",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["国内", "视频"],
        ),
        "video_generation_provider": _catalog_item(
            "视频生成 Provider",
            "media",
            "TK_OPS_VIDEO_GENERATION_PROVIDER_API_KEY",
            "TK_OPS_VIDEO_GENERATION_PROVIDER_BASE_URL",
            "",
            ["video_generation"],
            requires_base_url=True,
            supports_model_discovery=True,
            region="custom",
            category="video",
            protocol="openai_chat",
            tags=["自定义", "视频", "远端同步"],
        ),
        "asset_analysis_provider": _catalog_item(
            "资产分析 Provider",
            "media",
            "TK_OPS_ASSET_ANALYSIS_PROVIDER_API_KEY",
            "TK_OPS_ASSET_ANALYSIS_PROVIDER_BASE_URL",
            "",
            ["asset_analysis"],
            requires_base_url=True,
            supports_model_discovery=True,
            region="custom",
            category="asset_analysis",
            protocol="openai_chat",
            tags=["自定义", "素材", "远端同步"],
        ),
        "custom_openai_compatible": _catalog_item(
            "自定义 OpenAI 兼容",
            "custom",
            "TK_OPS_CUSTOM_OPENAI_COMPATIBLE_API_KEY",
            "TK_OPS_CUSTOM_OPENAI_COMPATIBLE_BASE_URL",
            "",
            ["text_generation", "vision"],
            region="custom",
            category="custom",
            protocol="openai_chat",
            requires_base_url=True,
            supports_model_discovery=True,
            tags=["自定义", "OpenAI 兼容", "文本", "视觉"],
        ),
        "custom_video_provider": _catalog_item(
            "自定义视频 Provider",
            "custom",
            "TK_OPS_CUSTOM_VIDEO_PROVIDER_API_KEY",
            "TK_OPS_CUSTOM_VIDEO_PROVIDER_BASE_URL",
            "",
            ["video_generation"],
            region="custom",
            category="custom",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["自定义", "视频"],
        ),
        "custom_tts_provider": _catalog_item(
            "自定义 TTS Provider",
            "custom",
            "TK_OPS_CUSTOM_TTS_PROVIDER_API_KEY",
            "TK_OPS_CUSTOM_TTS_PROVIDER_BASE_URL",
            "",
            ["tts"],
            region="custom",
            category="custom",
            protocol="manual_catalog",
            requires_base_url=True,
            model_sync_mode="manual",
            tags=["自定义", "TTS"],
        ),
        "custom_transcription_provider": _catalog_item(
            "自定义转录 Provider",
            "custom",
            "TK_OPS_CUSTOM_TRANSCRIPTION_PROVIDER_API_KEY",
            "TK_OPS_CUSTOM_TRANSCRIPTION_PROVIDER_BASE_URL",
            "",
            ["speech_to_text"],
            region="custom",
            category="custom",
            protocol="openai_audio_transcriptions",
            requires_base_url=True,
            supports_model_discovery=True,
            tags=["自定义", "转录", "语音识别"],
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
    region: str = "global",
    category: str | None = None,
    protocol: str | None = None,
    model_sync_mode: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "label": label,
        "kind": kind,
        "region": region,
        "category": category or kind,
        "protocol": protocol or "manual_catalog",
        "model_sync_mode": model_sync_mode or ("remote" if supports_model_discovery else "static"),
        "tags": tags or [],
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


def _request_json_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers=headers or {},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8") if response.length != 0 else ""
    except urllib.error.HTTPError as exc:
        raise RuntimeHTTPException(
            status_code=502,
            detail=f"远端模型目录刷新失败：{_extract_remote_message(exc)}",
            error_code="provider.model.refresh_failed",
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeHTTPException(
            status_code=502,
            detail="无法连接远端模型目录，请检查网络、Base URL 或本地服务状态。",
            error_code="provider.model.refresh_failed",
        ) from exc

    if not body.strip():
        return {}

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeHTTPException(
            status_code=502,
            detail="远端模型目录返回了不可解析的数据。",
            error_code="provider.model.refresh_failed",
        ) from exc
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


def _fetch_openrouter_models(runtime: ProviderRuntimeConfig) -> list[StoredAIProviderModel]:
    endpoint = _normalize_endpoint(runtime.base_url, "/models")
    payload = _request_json_get(endpoint, headers=_build_headers(runtime.api_key))
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []

    now = _utc_now()
    models: list[StoredAIProviderModel] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id", "")).strip()
        if model_id == "":
            continue
        architecture = item.get("architecture")
        architecture = architecture if isinstance(architecture, dict) else {}
        input_modalities = _string_list(architecture.get("input_modalities"))
        output_modalities = _string_list(architecture.get("output_modalities"))
        capability_kinds = _capability_kinds_from_modalities(input_modalities, output_modalities)
        if not capability_kinds:
            capability_kinds = ["text_generation"]
        models.append(
            StoredAIProviderModel(
                provider_id="openrouter",
                model_id=model_id,
                display_name=str(item.get("name") or model_id).strip(),
                capability_kinds=capability_kinds,
                input_modalities=input_modalities or ["text"],
                output_modalities=output_modalities or ["text"],
                context_window=_coerce_int(item.get("context_length")),
                default_for=[],
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )
    return models


def _fetch_openai_compatible_models(runtime: ProviderRuntimeConfig) -> list[StoredAIProviderModel]:
    endpoint = _normalize_endpoint(runtime.base_url, "/models")
    payload = _request_json_get(endpoint, headers=_build_headers(runtime.api_key))
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []

    now = _utc_now()
    models: list[StoredAIProviderModel] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or item.get("model") or "").strip()
        if model_id == "":
            continue

        display_name = str(item.get("name") or item.get("display_name") or model_id).strip()
        architecture = item.get("architecture")
        architecture = architecture if isinstance(architecture, dict) else {}
        input_modalities = _string_list(item.get("input_modalities")) or _string_list(
            architecture.get("input_modalities")
        )
        output_modalities = _string_list(item.get("output_modalities")) or _string_list(
            architecture.get("output_modalities")
        )
        inferred_input_modalities, inferred_output_modalities = _infer_modalities_from_model_name(
            runtime.provider,
            model_id,
            display_name,
        )
        if not input_modalities:
            input_modalities = inferred_input_modalities
        if not output_modalities:
            output_modalities = inferred_output_modalities
        capability_kinds = _capability_kinds_from_value(item.get("capabilities"))
        if not capability_kinds:
            capability_kinds = _capability_kinds_from_modalities(input_modalities, output_modalities)
        if not capability_kinds:
            capability_kinds = ["text_generation"]
        if not input_modalities:
            input_modalities = ["text"]
        if not output_modalities:
            output_modalities = ["text"]

        models.append(
            StoredAIProviderModel(
                provider_id=runtime.provider,
                model_id=model_id,
                display_name=display_name,
                capability_kinds=capability_kinds,
                input_modalities=input_modalities,
                output_modalities=output_modalities,
                context_window=_coerce_int(
                    item.get("context_length")
                    or item.get("context_window")
                    or item.get("max_context_length")
                ),
                default_for=[],
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )
    return models


def _fetch_ollama_models(runtime: ProviderRuntimeConfig) -> list[StoredAIProviderModel]:
    endpoint_root = runtime.base_url.rstrip("/")
    if endpoint_root.endswith("/v1"):
        endpoint_root = endpoint_root[:-3]
    payload = _request_json_get(f"{endpoint_root}/api/tags")
    rows = payload.get("models")
    if not isinstance(rows, list):
        return []

    now = _utc_now()
    models: list[StoredAIProviderModel] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("model") or item.get("name") or "").strip()
        if model_id == "":
            continue
        details = item.get("details")
        details = details if isinstance(details, dict) else {}
        capability_kinds = ["text_generation"]
        input_modalities = ["text"]
        if _ollama_model_supports_vision(model_id, details):
            capability_kinds.append("vision")
            input_modalities.append("image")
        models.append(
            StoredAIProviderModel(
                provider_id="ollama",
                model_id=model_id,
                display_name=str(item.get("name") or model_id).strip(),
                capability_kinds=capability_kinds,
                input_modalities=input_modalities,
                output_modalities=["text"],
                context_window=_coerce_int(details.get("context_length")),
                default_for=[],
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )
    return models


def _capability_kinds_from_modalities(
    input_modalities: list[str],
    output_modalities: list[str],
) -> list[str]:
    normalized_inputs = {item.lower() for item in input_modalities}
    normalized_outputs = {item.lower() for item in output_modalities}
    capability_kinds: list[str] = []
    if "text" in normalized_outputs:
        capability_kinds.append("text_generation")
    if "image" in normalized_inputs and "video" not in normalized_outputs:
        capability_kinds.append("vision")
    if "audio" in normalized_inputs and "text" in normalized_outputs:
        capability_kinds.append("speech_to_text")
    if "video" in normalized_inputs and "text" in normalized_outputs:
        capability_kinds.append("asset_analysis")
    if "video" in normalized_outputs:
        capability_kinds.append("video_generation")
    if "audio" in normalized_outputs:
        capability_kinds.append("tts")
    return capability_kinds


def _infer_modalities_from_model_name(
    provider_id: str,
    model_id: str,
    display_name: str,
) -> tuple[list[str], list[str]]:
    token = f"{provider_id} {model_id} {display_name}".lower().replace("_", "-")
    alias_token = _normalize_model_alias_token(token)
    if provider_id == "volcengine" and any(
        marker in alias_token
        for marker in (
            "doubao-seed-2-0",
            "doubao-seed-1-8",
            "doubao-seed-1-6-vision",
            "doubao-1-5-vision",
        )
    ):
        return ["text", "image", "video"], ["text"]

    video_markers = (
        "seedance",
        "seaweed",
        "kling",
        "jimeng",
        "wanx",
        "vidu",
        "hailuo",
        "video",
        "t2v",
        "i2v",
        "text-to-video",
        "image-to-video",
    )
    tts_markers = ("tts", "speech", "voice", "cosyvoice", "audio")
    vision_markers = (
        "vision",
        "vl",
        "qwen-vl",
        "qwen2-vl",
        "qwen2.5-vl",
        "glm-4v",
        "visual",
    )

    if any(marker in token for marker in video_markers):
        return ["text", "image"], ["video"]
    if any(marker in token for marker in tts_markers):
        return ["text"], ["audio"]
    if any(marker in token for marker in vision_markers):
        return ["text", "image"], ["text"]
    return [], []


def _capability_kinds_from_value(value: object) -> list[str]:
    aliases = {
        "text": "text_generation",
        "text_generation": "text_generation",
        "chat": "text_generation",
        "vision": "vision",
        "image": "vision",
        "视觉": "vision",
        "视觉理解": "asset_analysis",
        "视频理解": "asset_analysis",
        "多模态": "asset_analysis",
        "video": "video_generation",
        "video_generation": "video_generation",
        "视频生成": "video_generation",
        "tts": "tts",
        "speech": "tts",
        "语音合成": "tts",
        "speech_to_text": "speech_to_text",
        "transcription": "speech_to_text",
        "audio_transcription": "speech_to_text",
        "asr": "speech_to_text",
        "语音识别": "speech_to_text",
        "音频转写": "speech_to_text",
        "语音转写": "speech_to_text",
        "asset_analysis": "asset_analysis",
        "subtitle_alignment": "subtitle_alignment",
    }
    kinds: list[str] = []
    for item in _string_list(value):
        kind = aliases.get(item.lower())
        if kind is not None and kind not in kinds:
            kinds.append(kind)
    return kinds


def _model_supports_capability(model: AIModelCatalogItemDto, capability_id: str) -> bool:
    if capability_id in model.defaultFor:
        return True

    capability_types = set(model.capabilityTypes)
    input_modalities = set(model.inputModalities)
    output_modalities = set(model.outputModalities)

    if capability_id in {"script_generation", "script_rewrite", "storyboard_generation"}:
        return "text_generation" in capability_types and "text" in output_modalities
    if capability_id == "tts_generation":
        return "tts" in capability_types or "audio" in output_modalities
    if capability_id == "subtitle_alignment":
        return (
            "subtitle_alignment" in capability_types
            or ("text_generation" in capability_types and "text" in output_modalities)
        )
    if capability_id == "video_transcription":
        return (
            "speech_to_text" in capability_types
            or (
                "text" in output_modalities
                and ("video" in input_modalities or "asset_analysis" in capability_types)
            )
        )
    if capability_id == "video_generation":
        return "video_generation" in capability_types or "video" in output_modalities
    if capability_id == "asset_analysis":
        return (
            "asset_analysis" in capability_types
            or (
                "text" in output_modalities
                and (
                    "vision" in capability_types
                    or "image" in input_modalities
                    or "video" in input_modalities
                )
            )
        )
    return _capability_type_for(capability_id) in capability_types


def _is_model_access_denied_message(message: str) -> bool:
    normalized = message.lower()
    access_markers = (
        "do not have access",
        "don't have access",
        "not have access",
        "does not exist",
        "model_not_found",
        "model or endpoint",
        "无权限",
        "没有权限",
        "不存在",
    )
    return "404" in normalized and any(marker in normalized for marker in access_markers)


def _resolve_model_alias_candidates(
    models: list[AIModelCatalogItemDto],
    requested_model: str,
    *,
    required_capability_type: str | None,
) -> list[AIModelCatalogItemDto]:
    requested_token = _normalize_model_alias_token(requested_model)
    if requested_token == "":
        return []

    matches: list[tuple[tuple[int, str], AIModelCatalogItemDto]] = []
    for item in models:
        if (
            required_capability_type is not None
            and required_capability_type not in item.capabilityTypes
        ):
            continue
        rank = _model_alias_match_rank(item, requested_token)
        if rank is None:
            continue
        matches.append(((rank, item.modelId), item))
    matches.sort(key=lambda entry: entry[1].modelId, reverse=True)
    matches.sort(key=lambda entry: entry[0][0])
    return [item for _, item in matches]


def _is_static_model_superseded(
    static_model: AIModelCatalogItemDto,
    remote_models: list[AIModelCatalogItemDto],
) -> bool:
    static_token = _normalize_model_alias_token(static_model.modelId)
    if static_token == "":
        return False

    for item in remote_models:
        if item.provider != static_model.provider or not item.enabled:
            continue
        if not set(item.capabilityTypes).intersection(static_model.capabilityTypes):
            continue
        rank = _model_alias_match_rank(item, static_token)
        if rank in {1, 2, 3}:
            return True
    return False


def _model_alias_match_rank(
    model: AIModelCatalogItemDto,
    requested_token: str,
) -> int | None:
    normalized_id = _normalize_model_alias_token(model.modelId)
    normalized_display = _normalize_model_alias_token(model.displayName)

    if normalized_id == requested_token:
        return 0
    if normalized_display == requested_token:
        return 1
    if _is_versioned_model_successor(normalized_id, requested_token):
        return 2
    if _is_versioned_model_successor(normalized_display, requested_token):
        return 3
    if normalized_id.startswith(f"{requested_token}-"):
        return 4
    if normalized_display.startswith(f"{requested_token}-"):
        return 5
    return None


def _is_versioned_model_successor(candidate_token: str, requested_token: str) -> bool:
    prefix = f"{requested_token}-"
    if not candidate_token.startswith(prefix):
        return False
    suffix = candidate_token[len(prefix) :]
    first_segment = suffix.split("-", 1)[0]
    return first_segment.isdigit() and len(first_segment) >= 6


def _normalize_model_alias_token(value: str) -> str:
    parts = re.split(r"[^a-z0-9]+", value.lower())
    return "-".join(part for part in parts if part)


def _ollama_model_supports_vision(model_id: str, details: dict[str, object]) -> bool:
    tokens = {model_id.lower()}
    family = details.get("family")
    if isinstance(family, str) and family.strip():
        tokens.add(family.lower())
    families = details.get("families")
    if isinstance(families, list):
        tokens.update(str(item).lower() for item in families if str(item).strip())
    vision_markers = ("llava", "bakllava", "moondream", "minicpm-v", "qwen2-vl", "qwen2.5-vl", "vl")
    return any(any(marker in token for marker in vision_markers) for token in tokens)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _capability_type_for(capability_id: str) -> str:
    return {
        "script_generation": "text_generation",
        "script_rewrite": "text_generation",
        "storyboard_generation": "text_generation",
        "tts_generation": "tts",
        "subtitle_alignment": "subtitle_alignment",
        "video_transcription": "speech_to_text",
        "video_generation": "video_generation",
        "asset_analysis": "asset_analysis",
    }[capability_id]


def _static_model_catalog() -> list[AIModelCatalogItemDto]:
    return [
        _model("openai", "gpt-5", "GPT-5", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation"]),
        _model("openai", "gpt-5.4", "GPT-5.4", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "script_rewrite", "storyboard_generation"]),
        _model("openai", "gpt-5-mini", "GPT-5 Mini", ["text_generation"], ["text"], ["text"], ["script_rewrite"]),
        _model("openai", "gpt-4o-mini-tts", "GPT-4o Mini TTS", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("openai", "whisper-1", "Whisper 1", ["speech_to_text"], ["audio", "video"], ["text"], ["video_transcription"]),
        _model("anthropic", "claude-sonnet", "Claude Sonnet", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "script_rewrite"]),
        _model("gemini", "gemini-pro", "Gemini Pro", ["text_generation", "vision", "asset_analysis"], ["text", "image", "video"], ["text"], ["storyboard_generation", "asset_analysis"]),
        _model("deepseek", "deepseek-chat", "DeepSeek Chat", ["text_generation"], ["text"], ["text"], ["script_generation", "script_rewrite"]),
        _model("qwen", "qwen-plus", "Qwen Plus", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "storyboard_generation"]),
        _model("kimi", "moonshot-v1", "Kimi", ["text_generation"], ["text"], ["text"], ["script_rewrite"]),
        _model("zhipu", "glm-4", "GLM-4", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation"]),
        _model("volcengine", "doubao-seed-1.6", "豆包 Seed 1.6", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "storyboard_generation"]),
        _model("volcengine", "doubao-seed-2.0-pro", "Doubao-Seed-2.0-pro", ["text_generation", "vision", "asset_analysis"], ["text", "image", "video"], ["text"], ["asset_analysis"]),
        _model("volcengine", "doubao-seed-2.0-lite", "Doubao-Seed-2.0-lite", ["text_generation", "vision", "asset_analysis"], ["text", "image", "video"], ["text"], ["asset_analysis"]),
        _model("volcengine", "seedance-2.0", "Seedance 2.0", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("volcengine", "doubao-tts", "豆包 TTS", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("baidu_qianfan", "ernie-4.5", "ERNIE 4.5", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "asset_analysis"]),
        _model("tencent_hunyuan", "hunyuan-turbos", "混元 TurboS", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation"]),
        _model("xunfei_spark", "spark-max", "讯飞星火 Max", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation"]),
        _model("minimax", "abab6.5", "MiniMax abab6.5", ["text_generation"], ["text"], ["text"], ["script_rewrite"]),
        _model("minimax", "speech-02", "MiniMax Speech 02", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("minimax", "hailuo-02", "海螺 02", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("baichuan", "baichuan4", "百川 4", ["text_generation"], ["text"], ["text"], ["script_generation"]),
        _model("lingyi", "yi-large", "Yi Large", ["text_generation"], ["text"], ["text"], ["script_rewrite"]),
        _model("stepfun", "step-2", "Step 2", ["text_generation", "vision"], ["text", "image"], ["text"], ["storyboard_generation"]),
        _model("sensecore", "sensechat-5", "SenseChat 5", ["text_generation", "vision"], ["text", "image"], ["text"], ["asset_analysis"]),
        _model("cohere", "command-r-plus", "Command R+", ["text_generation"], ["text"], ["text"], ["script_rewrite"]),
        _model("openrouter", "openrouter/auto", "OpenRouter Auto", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "storyboard_generation"]),
        _model("ollama", "llama3.1", "Llama 3.1", ["text_generation"], ["text"], ["text"], ["script_generation"]),
        _model("ollama", "llava", "LLaVA", ["text_generation", "vision"], ["text", "image"], ["text"], ["asset_analysis"]),
        _model("azure_speech", "azure-neural-voice", "Azure Neural Voice", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("elevenlabs", "eleven-multilingual", "Eleven Multilingual", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("aliyun_tts", "cosyvoice-v2", "CosyVoice V2", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("tencent_tts", "tencent-cloud-tts", "腾讯云 TTS", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("baidu_tts", "baidu-speech-tts", "百度智能语音 TTS", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("xunfei_tts", "xunfei-tts", "讯飞语音 TTS", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("volcengine_asr", "volcengine-asr", "火山语音识别", ["speech_to_text"], ["audio", "video"], ["text"], ["video_transcription"]),
        _model("aliyun_asr", "aliyun-file-transcription", "阿里云文件转写", ["speech_to_text"], ["audio", "video"], ["text"], []),
        _model("tencent_asr", "tencent-asr", "腾讯云语音识别", ["speech_to_text"], ["audio", "video"], ["text"], []),
        _model("baidu_asr", "baidu-speech-asr", "百度语音识别", ["speech_to_text"], ["audio", "video"], ["text"], []),
        _model("xunfei_asr", "xunfei-lfasr", "讯飞长语音转写", ["speech_to_text"], ["audio", "video"], ["text"], []),
        _model("kling", "kling-v1.6", "可灵 1.6", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("jimeng", "jimeng-video", "即梦视频", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("wanxiang", "wanx2.1", "通义万相 2.1", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("vidu", "vidu-2.0", "Vidu 2.0", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("hailuo", "hailuo-02", "海螺 02", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("video_generation_provider", "video-default", "默认视频生成模型", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("asset_analysis_provider", "asset-analysis-default", "默认资产分析模型", ["asset_analysis"], ["text", "image", "video"], ["text"], ["asset_analysis"]),
        _model("openai_compatible", "custom-compatible-model", "自定义兼容模型", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "storyboard_generation"]),
        _model("openai_compatible", "custom-transcription-model", "自定义转录模型", ["speech_to_text"], ["audio", "video"], ["text"], ["video_transcription"]),
        _model("custom_openai_compatible", "custom-compatible-model", "自定义兼容模型", ["text_generation", "vision"], ["text", "image"], ["text"], ["script_generation", "storyboard_generation"]),
        _model("custom_video_provider", "custom-video-model", "自定义视频模型", ["video_generation"], ["text", "image"], ["video"], ["video_generation"]),
        _model("custom_tts_provider", "custom-tts-model", "自定义 TTS 模型", ["tts"], ["text"], ["audio"], ["tts_generation"]),
        _model("custom_transcription_provider", "custom-transcription-model", "自定义转录模型", ["speech_to_text"], ["audio", "video"], ["text"], ["video_transcription"]),
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
    return _default_agent_role_from_config(capability_id)


_LEGACY_DEFAULT_TEMPLATES: dict[str, set[str]] = {
    "script_generation": {"主题：{{topic}}"},
    "script_rewrite": {"原脚本：\n{{script}}\n\n改写要求：{{instructions}}"},
    "storyboard_generation": {"脚本内容：\n{{script}}"},
    "tts_generation": {"脚本内容：\n{{script}}"},
    "subtitle_alignment": {"脚本内容：\n{{script}}"},
    "video_transcription": {"{{media_file}}"},
    "video_generation": {"分镜内容：\n{{storyboard}}"},
    "asset_analysis": {"素材内容：\n{{assets}}"},
}

_MOJIBAKE_MARKERS = ("锛", "歿", "鑴", "涓", "瀛", "瑙", "绱", "鍥", "銆", "乀")


def _looks_like_legacy_default_capability(item: StoredAICapabilityConfig) -> bool:
    if item.user_prompt_template.strip() in _LEGACY_DEFAULT_TEMPLATES.get(item.capability_id, set()):
        return True

    if _looks_like_legacy_video_transcription_prompt(item):
        return True

    if _looks_like_legacy_asset_analysis_prompt(item):
        return True

    combined = "\n".join((item.agent_role, item.system_prompt, item.user_prompt_template))
    return any(marker in combined for marker in _MOJIBAKE_MARKERS)


def _looks_like_legacy_video_transcription_prompt(item: StoredAICapabilityConfig) -> bool:
    if item.capability_id != "video_transcription":
        return False
    return (
        item.agent_role.strip() == "视频转录 Agent"
        and "# 视频转录 Agent" in item.system_prompt
        and "{{media_file}}" in item.user_prompt_template
    )


def _looks_like_legacy_asset_analysis_prompt(item: StoredAICapabilityConfig) -> bool:
    if item.capability_id != "asset_analysis":
        return False
    return (
        item.agent_role.strip() == "素材分析 Agent"
        and "# 素材分析 Agent" in item.system_prompt
        and "请分析以下素材内容" in item.user_prompt_template
        and "{{content}}" in item.user_prompt_template
    )


def _migrate_default_capability(item: StoredAICapabilityConfig) -> StoredAICapabilityConfig:
    if item.capability_id not in CAPABILITY_IDS:
        return item
    if not _looks_like_legacy_default_capability(item):
        return item
    return StoredAICapabilityConfig(
        capability_id=item.capability_id,
        enabled=item.enabled,
        provider=item.provider,
        model=item.model,
        agent_role=_default_agent_role(item.capability_id),
        system_prompt=_default_system_prompt(item.capability_id),
        user_prompt_template=_default_template(item.capability_id),
        updated_at=_utc_now(),
    )


def _with_default_prompt_fields(item: StoredAICapabilityConfig) -> StoredAICapabilityConfig:
    if item.capability_id not in CAPABILITY_IDS:
        return item
    return StoredAICapabilityConfig(
        capability_id=item.capability_id,
        enabled=item.enabled,
        provider=item.provider,
        model=item.model,
        agent_role=_default_agent_role(item.capability_id),
        system_prompt=_default_system_prompt(item.capability_id),
        user_prompt_template=_default_template(item.capability_id),
        updated_at=item.updated_at,
    )


def _default_system_prompt(capability_id: str) -> str:
    return _default_system_prompt_from_config(capability_id)


def _default_template(capability_id: str) -> str:
    return _default_user_prompt_template_from_config(capability_id)


def _mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"


def _protocol_family_for(provider_id: str) -> str:
    try:
        return str(_get_provider_catalog_metadata(provider_id).get("protocol", "unknown"))
    except HTTPException:
        return "unknown"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
