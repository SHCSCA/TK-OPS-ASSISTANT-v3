from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from fastapi import HTTPException

from ai import providers as ai_providers
from ai.providers.base import TextGenerationMediaInput, TextGenerationRequest
from ai.providers.errors import ProviderHTTPException
from repositories.ai_job_repository import AIJobRepository
from services.ai_capability_service import AICapabilityService

log = logging.getLogger(__name__)

TEXT_GENERATION_TIMEOUT_SECONDS = 60.0
MEDIA_TEXT_GENERATION_TIMEOUT_SECONDS = 180.0


@dataclass(frozen=True, slots=True)
class GeneratedTextResult:
    text: str
    provider: str
    model: str
    ai_job_id: str


class AITextGenerationService:
    def __init__(
        self,
        capability_service: AICapabilityService,
        ai_job_repository: AIJobRepository,
    ) -> None:
        self._capability_service = capability_service
        self._ai_job_repository = ai_job_repository

    def generate_text(
        self,
        capability_id: str,
        variables: dict[str, str],
        *,
        project_id: str | None = None,
        request_id: str | None = None,
        media_inputs: tuple[TextGenerationMediaInput, ...] = (),
    ) -> GeneratedTextResult:
        capability = self._capability_service.get_capability(capability_id)
        if not capability.enabled:
            raise ProviderHTTPException(
                status_code=400,
                detail='当前 AI 能力已停用。',
                error_code='ai_capability_disabled',
            )

        provider_runtime = self._capability_service.get_provider_runtime_config(capability.provider)
        if not provider_runtime.supports_text_generation:
            raise ProviderHTTPException(
                status_code=400,
                detail='当前 Provider 尚未接入文本生成。',
                error_code='ai_provider_unsupported',
            )
        if provider_runtime.provider == 'openai_compatible' and provider_runtime.base_url.strip() == '':
            raise ProviderHTTPException(
                status_code=400,
                detail='OpenAI-compatible Provider 必须先配置 Base URL。',
                error_code='ai_provider_base_url_missing',
            )
        if provider_runtime.requires_secret and not provider_runtime.api_key:
            raise ProviderHTTPException(
                status_code=400,
                detail='Provider API Key 尚未配置。',
                error_code='ai_provider_not_configured',
            )

        prompt = _render_template(capability.userPromptTemplate, variables)
        instructions = '\n\n'.join(
            [item for item in (capability.agentRole.strip(), capability.systemPrompt.strip()) if item]
        )
        required_capability_type = (
            'asset_analysis'
            if media_inputs and capability_id == 'video_transcription'
            else None
        )
        resolved_model = self._capability_service.resolve_provider_model_id(
            capability.provider,
            capability.model,
            capability_id=capability_id,
            required_capability_type=required_capability_type,
        )
        job = self._ai_job_repository.create_running(
            project_id=project_id,
            capability_id=capability_id,
            provider=capability.provider,
            model=resolved_model,
        )
        started_at = time.perf_counter()

        try:
            output = ai_providers.dispatch_text_generation(
                provider_runtime,
                TextGenerationRequest(
                    model=resolved_model,
                    system_prompt=instructions,
                    user_prompt=prompt,
                    request_id=request_id,
                    timeout_seconds=_timeout_seconds_for(media_inputs),
                    media_inputs=media_inputs,
                ),
            )
            output_text = output.text
        except ProviderHTTPException as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            self._ai_job_repository.mark_failed(
                job.id,
                error=str(exc.detail),
                duration_ms=duration_ms,
            )
            log.warning(
                'AI 文本生成 Provider 异常 capability=%s provider=%s code=%s detail=%s',
                capability_id,
                provider_runtime.provider,
                exc.error_code,
                exc.detail,
            )
            raise
        except HTTPException as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            self._ai_job_repository.mark_failed(
                job.id,
                error=str(exc.detail),
                duration_ms=duration_ms,
            )
            log.warning(
                'AI 文本生成请求异常 capability=%s provider=%s detail=%s',
                capability_id,
                provider_runtime.provider,
                exc.detail,
            )
            raise
        except Exception as exc:  # pragma: no cover - 防御性兜底
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            self._ai_job_repository.mark_failed(
                job.id,
                error=str(exc),
                duration_ms=duration_ms,
            )
            log.exception('AI 文本生成失败 capability=%s provider=%s', capability_id, provider_runtime.provider)
            raise ProviderHTTPException(
                status_code=502,
                detail='AI Provider 请求失败，请稍后重试。',
                error_code='ai_provider_server_error',
            ) from exc

        self._ai_job_repository.mark_succeeded(
            job.id,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        return GeneratedTextResult(
            text=output_text,
            provider=capability.provider,
            model=resolved_model,
            ai_job_id=job.id,
        )


def _render_template(template: str, variables: dict[str, str]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f'{{{{{key}}}}}', value)
    return rendered


def _timeout_seconds_for(media_inputs: tuple[TextGenerationMediaInput, ...]) -> float:
    return MEDIA_TEXT_GENERATION_TIMEOUT_SECONDS if media_inputs else TEXT_GENERATION_TIMEOUT_SECONDS
