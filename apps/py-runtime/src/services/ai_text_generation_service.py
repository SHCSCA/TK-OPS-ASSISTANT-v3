from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from fastapi import HTTPException

from repositories.ai_job_repository import AIJobRepository
from services.ai_capability_service import AICapabilityService


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
    ) -> GeneratedTextResult:
        capability = self._capability_service.get_capability(capability_id)
        if not capability.enabled:
            raise HTTPException(status_code=400, detail='Selected AI capability is disabled.')

        provider_runtime = self._capability_service.get_provider_runtime_config(capability.provider)
        if not provider_runtime.supports_text_generation:
            raise HTTPException(
                status_code=400,
                detail='Selected provider is registered but not wired for text generation in this milestone.',
            )
        if not provider_runtime.api_key:
            raise HTTPException(status_code=400, detail='Provider API key is not configured.')
        if provider_runtime.provider == 'openai_compatible' and provider_runtime.base_url.strip() == '':
            raise HTTPException(status_code=400, detail='Base URL is required for OpenAI-compatible providers.')

        prompt = _render_template(capability.userPromptTemplate, variables)
        instructions = '\n\n'.join(
            [item for item in (capability.agentRole.strip(), capability.systemPrompt.strip()) if item]
        )
        job = self._ai_job_repository.create_running(
            project_id=project_id,
            capability_id=capability_id,
            provider=capability.provider,
            model=capability.model,
        )
        started_at = time.perf_counter()

        try:
            if provider_runtime.provider == 'openai':
                output_text = _call_openai_responses(
                    base_url=provider_runtime.base_url,
                    api_key=provider_runtime.api_key,
                    model=capability.model,
                    instructions=instructions,
                    prompt=prompt,
                    request_id=request_id,
                )
            elif provider_runtime.provider == 'openai_compatible':
                output_text = _call_openai_compatible_chat(
                    base_url=provider_runtime.base_url,
                    api_key=provider_runtime.api_key,
                    model=capability.model,
                    instructions=instructions,
                    prompt=prompt,
                    request_id=request_id,
                )
            else:
                raise HTTPException(status_code=400, detail='Provider is not available for text generation.')
        except HTTPException as exc:
            self._ai_job_repository.mark_failed(
                job.id,
                error=str(exc.detail),
                duration_ms=int((time.perf_counter() - started_at) * 1000),
            )
            raise
        except Exception as exc:  # pragma: no cover - defensive branch
            self._ai_job_repository.mark_failed(
                job.id,
                error=str(exc),
                duration_ms=int((time.perf_counter() - started_at) * 1000),
            )
            raise HTTPException(status_code=502, detail='AI provider request failed.') from exc

        self._ai_job_repository.mark_succeeded(
            job.id,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        return GeneratedTextResult(
            text=output_text,
            provider=capability.provider,
            model=capability.model,
            ai_job_id=job.id,
        )


def _render_template(template: str, variables: dict[str, str]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f'{{{{{key}}}}}', value)
    return rendered


def _call_openai_responses(
    *,
    base_url: str,
    api_key: str,
    model: str,
    instructions: str,
    prompt: str,
    request_id: str | None,
) -> str:
    payload = _post_json(
        base_url,
        api_key,
        {
            'model': model,
            'instructions': instructions,
            'input': prompt,
        },
        request_id=request_id,
    )
    texts: list[str] = []
    if isinstance(payload.get('output_text'), str):
        texts.append(str(payload['output_text']))
    for item in payload.get('output', []):
        if item.get('type') != 'message':
            continue
        for content in item.get('content', []):
            if content.get('type') in {'output_text', 'text'} and content.get('text'):
                texts.append(str(content['text']))
    text = '\n'.join(part.strip() for part in texts if part and part.strip()).strip()
    if not text:
        raise HTTPException(status_code=502, detail='OpenAI returned an empty text response.')
    return text


def _call_openai_compatible_chat(
    *,
    base_url: str,
    api_key: str,
    model: str,
    instructions: str,
    prompt: str,
    request_id: str | None,
) -> str:
    payload = _post_json(
        base_url.rstrip('/') + '/chat/completions',
        api_key,
        {
            'model': model,
            'messages': [
                {'role': 'system', 'content': instructions},
                {'role': 'user', 'content': prompt},
            ],
        },
        request_id=request_id,
    )
    choices = payload.get('choices', [])
    if not choices:
        raise HTTPException(status_code=502, detail='OpenAI-compatible provider returned no choices.')
    content = choices[0].get('message', {}).get('content', '')
    if isinstance(content, list):
        text = '\n'.join(str(item.get('text', '')).strip() for item in content if item.get('text'))
    else:
        text = str(content).strip()
    if not text:
        raise HTTPException(status_code=502, detail='OpenAI-compatible provider returned empty content.')
    return text


def _post_json(
    url: str,
    api_key: str,
    payload: dict[str, object],
    *,
    request_id: str | None,
) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'X-Request-ID': request_id or '',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode('utf-8'))
            message = payload.get('error', {}).get('message') or payload.get('message')
        except Exception:  # pragma: no cover - defensive fallback
            message = None
        raise HTTPException(status_code=502, detail=message or 'AI provider returned an HTTP error.') from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail='Unable to reach the AI provider.') from exc
