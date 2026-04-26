from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from ai.providers.base import TextGenerationMediaInput, TextGenerationResponse
from ai.providers.errors import ProviderHTTPException
from ai.providers.openai_responses import OpenAIResponsesTextGenerationAdapter
from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.ai_job_repository import AIJobRepository
from services.ai_capability_service import ProviderRuntimeConfig
from services.ai_text_generation_service import AITextGenerationService


@dataclass(frozen=True, slots=True)
class _FakeCapability:
    enabled: bool
    provider: str
    model: str
    agentRole: str
    systemPrompt: str
    userPromptTemplate: str


class _FakeCapabilityService:
    def __init__(
        self,
        capability: _FakeCapability,
        runtime: ProviderRuntimeConfig,
        *,
        resolved_model: str | None = None,
        capability_id: str = 'script_generation',
    ) -> None:
        self._capability = capability
        self._runtime = runtime
        self._resolved_model = resolved_model
        self._capability_id = capability_id

    def get_capability(self, capability_id: str) -> _FakeCapability:
        assert capability_id == self._capability_id
        return self._capability

    def get_provider_runtime_config(self, provider_id: str) -> ProviderRuntimeConfig:
        assert provider_id == self._capability.provider
        return self._runtime

    def resolve_provider_model_id(
        self,
        provider_id: str,
        model_id: str,
        *,
        capability_id: str | None = None,
        required_capability_type: str | None = None,
    ) -> str:
        assert provider_id == self._capability.provider
        assert model_id == self._capability.model
        assert capability_id in {self._capability_id, None}
        assert required_capability_type in {'text_generation', 'asset_analysis', None}
        return self._resolved_model or model_id


def _make_service(
    tmp_path: Path,
    capability: _FakeCapability,
    runtime: ProviderRuntimeConfig,
    *,
    resolved_model: str | None = None,
    capability_id: str = 'script_generation',
) -> AITextGenerationService:
    engine = create_runtime_engine(tmp_path / 'runtime.db')
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    job_repository = AIJobRepository(session_factory=session_factory)
    return AITextGenerationService(
        capability_service=_FakeCapabilityService(
            capability,
            runtime,
            resolved_model=resolved_model,
            capability_id=capability_id,
        ),
        ai_job_repository=job_repository,
    )


def _make_runtime(provider: str, *, supports_text_generation: bool = True) -> ProviderRuntimeConfig:
    return ProviderRuntimeConfig(
        provider=provider,
        label=provider,
        api_key='test-api-key',
        base_url='https://example.com/v1',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=supports_text_generation,
        supports_tts=False,
        protocol_family='openai_chat' if provider != 'openai' else 'openai_responses',
    )


def test_generate_text_dispatches_openai_via_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_service(
        tmp_path,
        _FakeCapability(
            enabled=True,
            provider='openai',
            model='gpt-5',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='主题：{{topic}}',
        ),
        _make_runtime('openai'),
    )

    captured: dict[str, object] = {}

    def fake_dispatch(runtime_config, request):
        captured['provider'] = runtime_config.provider
        captured['protocol_family'] = runtime_config.protocol_family
        captured['request_model'] = request.model
        captured['request_system'] = request.system_prompt
        captured['request_user'] = request.user_prompt
        return TextGenerationResponse(
            text='mocked-output',
            provider='openai',
            model='gpt-5',
        )

    monkeypatch.setattr('ai.providers.dispatch_text_generation', fake_dispatch)

    result = service.generate_text(
        'script_generation',
        {'topic': 'TK-OPS'},
    )

    assert result.provider == 'openai'
    assert result.text == 'mocked-output'
    assert result.model == 'gpt-5'
    assert captured['provider'] == 'openai'
    assert captured['protocol_family'] == 'openai_responses'
    assert captured['request_model'] == 'gpt-5'
    assert captured['request_user'] == '主题：TK-OPS'

    recent_jobs = service._ai_job_repository.list_recent(
        project_id=None,
        capability_ids=('script_generation',),
    )
    assert recent_jobs[0].status == 'succeeded'


def test_generate_text_uses_registry_and_adapter_generate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_service(
        tmp_path,
        _FakeCapability(
            enabled=True,
            provider='openai',
            model='gpt-5',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='主题：{{topic}}',
        ),
        ProviderRuntimeConfig(
            provider='openai',
            label='OpenAI',
            api_key='test-api-key',
            base_url='https://api.openai.com/v1/responses',
            secret_source='test',
            requires_secret=True,
            supports_text_generation=True,
            supports_tts=True,
            protocol_family='openai_responses',
        ),
    )

    captured: dict[str, object] = {}

    def fake_generate(self, request):
        captured['adapter'] = self.__class__.__name__
        captured['request_model'] = request.model
        captured['request_user'] = request.user_prompt
        return TextGenerationResponse(
            text='registry-output',
            provider='openai',
            model=request.model,
        )

    monkeypatch.setattr(OpenAIResponsesTextGenerationAdapter, 'generate', fake_generate)

    result = service.generate_text(
        'script_generation',
        {'topic': 'TK-OPS'},
    )

    assert result.text == 'registry-output'
    assert captured['adapter'] == 'OpenAIResponsesTextGenerationAdapter'
    assert captured['request_model'] == 'gpt-5'
    assert captured['request_user'] == '主题：TK-OPS'


def test_generate_text_dispatches_openai_compatible_via_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_service(
        tmp_path,
        _FakeCapability(
            enabled=True,
            provider='openai_compatible',
            model='custom-model',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='主题：{{topic}}',
        ),
        ProviderRuntimeConfig(
            provider='openai_compatible',
            label='OpenAI-compatible',
            api_key='test-api-key',
            base_url='https://example.com/v1',
            secret_source='test',
            requires_secret=True,
            supports_text_generation=True,
            supports_tts=False,
            protocol_family='openai_chat',
        ),
    )

    captured: dict[str, object] = {}

    def fake_dispatch(runtime_config, request):
        captured['provider'] = runtime_config.provider
        captured['protocol_family'] = runtime_config.protocol_family
        captured['request_model'] = request.model
        captured['request_system'] = request.system_prompt
        captured['request_user'] = request.user_prompt
        return TextGenerationResponse(
            text='mocked-compatible-output',
            provider='openai_compatible',
            model='custom-model',
        )

    monkeypatch.setattr('ai.providers.dispatch_text_generation', fake_dispatch)

    result = service.generate_text(
        'script_generation',
        {'topic': 'TK-OPS'},
    )

    assert result.provider == 'openai_compatible'
    assert result.text == 'mocked-compatible-output'
    assert result.model == 'custom-model'
    assert captured['provider'] == 'openai_compatible'
    assert captured['protocol_family'] == 'openai_chat'
    assert captured['request_model'] == 'custom-model'
    assert captured['request_user'] == '主题：TK-OPS'

    recent_jobs = service._ai_job_repository.list_recent(
        project_id=None,
        capability_ids=('script_generation',),
    )
    assert recent_jobs[0].status == 'succeeded'


def test_generate_text_uses_resolved_runtime_model_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_service(
        tmp_path,
        _FakeCapability(
            enabled=True,
            provider='volcengine',
            model='doubao-seed-1.6',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='主题：{{topic}}',
        ),
        _make_runtime('volcengine'),
        resolved_model='doubao-seed-1-6-251015',
    )

    captured: dict[str, object] = {}

    def fake_dispatch(runtime_config, request):
        captured['provider'] = runtime_config.provider
        captured['request_model'] = request.model
        return TextGenerationResponse(
            text='resolved-output',
            provider='volcengine',
            model=request.model,
        )

    monkeypatch.setattr('ai.providers.dispatch_text_generation', fake_dispatch)

    result = service.generate_text(
        'script_generation',
        {'topic': 'TK-OPS'},
    )

    assert captured == {
        'provider': 'volcengine',
        'request_model': 'doubao-seed-1-6-251015',
    }
    assert result.provider == 'volcengine'
    assert result.model == 'doubao-seed-1-6-251015'


def test_generate_text_extends_timeout_for_media_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_service(
        tmp_path,
        _FakeCapability(
            enabled=True,
            provider='volcengine',
            model='doubao-seed-2-0-pro-260215',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='拆解：{{media_file}}',
        ),
        _make_runtime('volcengine'),
        capability_id='video_transcription',
    )

    captured: dict[str, object] = {}

    def fake_dispatch(runtime_config, request):
        captured['timeout_seconds'] = request.timeout_seconds
        captured['media_inputs'] = request.media_inputs
        return TextGenerationResponse(
            text='{"segments":[{"startMs":0,"endMs":1000,"visual":"画面"}]}',
            provider='volcengine',
            model=request.model,
        )

    monkeypatch.setattr('ai.providers.dispatch_text_generation', fake_dispatch)

    service.generate_text(
        'video_transcription',
        {'media_file': '请拆解视频'},
        media_inputs=(
            TextGenerationMediaInput(
                kind='video',
                url='data:video/mp4;base64,AAAA',
                mime_type='video/mp4',
                filename='sample.mp4',
            ),
        ),
    )

    assert captured['timeout_seconds'] == 180.0
    assert len(captured['media_inputs']) == 1


def test_generate_text_keeps_chinese_error_when_provider_does_not_support_text_generation(
    tmp_path: Path,
) -> None:
    service = _make_service(
        tmp_path,
        _FakeCapability(
            enabled=True,
            provider='cohere',
            model='command-r-plus',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='主题：{{topic}}',
        ),
        ProviderRuntimeConfig(
            provider='cohere',
            label='Cohere',
            api_key='test-api-key',
            base_url='https://example.com/v2',
            secret_source='test',
            requires_secret=True,
            supports_text_generation=False,
            supports_tts=False,
            protocol_family='cohere_chat',
        ),
    )

    with pytest.raises(Exception) as exc_info:
        service.generate_text('script_generation', {'topic': 'TK-OPS'})

    assert getattr(exc_info.value, 'status_code', None) == 400
    assert 'Provider' in str(getattr(exc_info.value, 'detail', exc_info.value))


def test_generate_text_marks_jobs_succeeded_and_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_service(
        tmp_path,
        _FakeCapability(
            enabled=True,
            provider='openai',
            model='gpt-5',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='主题：{{topic}}',
        ),
        _make_runtime('openai'),
    )

    def success_dispatch(runtime_config, request):
        return TextGenerationResponse(
            text='generated text',
            provider='openai',
            model='gpt-5',
        )

    monkeypatch.setattr('ai.providers.dispatch_text_generation', success_dispatch)

    success_result = service.generate_text(
        'script_generation',
        {'topic': 'TK-OPS'},
    )
    assert success_result.text == 'generated text'
    success_jobs = service._ai_job_repository.list_recent(
        project_id=None,
        capability_ids=('script_generation',),
    )
    assert success_jobs[0].status == 'succeeded'

    failed_service = _make_service(
        tmp_path / 'failed',
        _FakeCapability(
            enabled=True,
            provider='openai',
            model='gpt-5',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='主题：{{topic}}',
        ),
        _make_runtime('openai'),
    )

    def failing_dispatch(runtime_config, request):
        raise ProviderHTTPException(
            status_code=502,
            detail='AI Provider 请求失败。',
            error_code='ai_provider_server_error',
        )

    monkeypatch.setattr('ai.providers.dispatch_text_generation', failing_dispatch)

    with pytest.raises(ProviderHTTPException):
        failed_service.generate_text(
            'script_generation',
            {'topic': 'TK-OPS'},
        )

    failed_jobs = failed_service._ai_job_repository.list_recent(
        project_id=None,
        capability_ids=('script_generation',),
    )
    assert failed_jobs[0].status == 'failed'
    assert failed_jobs[0].error == 'AI Provider 请求失败。'


def test_generate_text_wraps_generic_adapter_errors_with_structured_error_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_service(
        tmp_path,
        _FakeCapability(
            enabled=True,
            provider='openai',
            model='gpt-5',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='主题：{{topic}}',
        ),
        _make_runtime('openai'),
    )

    def failing_generate(self, request):
        raise RuntimeError('boom')

    monkeypatch.setattr(OpenAIResponsesTextGenerationAdapter, 'generate', failing_generate)

    with pytest.raises(ProviderHTTPException) as exc_info:
        service.generate_text(
            'script_generation',
            {'topic': 'TK-OPS'},
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.error_code == 'ai_provider_server_error'
    assert 'AI Provider 请求失败' in str(exc_info.value.detail)

    recent_jobs = service._ai_job_repository.list_recent(
        project_id=None,
        capability_ids=('script_generation',),
    )
    assert recent_jobs[0].status == 'failed'


def test_generate_text_allows_secretless_local_provider_without_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_service(
        tmp_path,
        _FakeCapability(
            enabled=True,
            provider='ollama',
            model='llama3.1',
            agentRole='角色',
            systemPrompt='系统',
            userPromptTemplate='主题：{{topic}}',
        ),
        ProviderRuntimeConfig(
            provider='ollama',
            label='Ollama',
            api_key=None,
            base_url='http://127.0.0.1:11434/v1',
            secret_source='none',
            requires_secret=False,
            supports_text_generation=True,
            supports_tts=False,
            protocol_family='openai_chat',
        ),
    )

    captured: dict[str, object] = {}

    def fake_dispatch(runtime_config, request):
        captured['requires_secret'] = runtime_config.requires_secret
        captured['api_key'] = runtime_config.api_key
        captured['base_url'] = runtime_config.base_url
        return TextGenerationResponse(
            text='local-output',
            provider='ollama',
            model='llama3.1',
        )

    monkeypatch.setattr('ai.providers.dispatch_text_generation', fake_dispatch)

    result = service.generate_text(
        'script_generation',
        {'topic': 'TK-OPS'},
    )

    assert result.provider == 'ollama'
    assert result.text == 'local-output'
    assert captured['requires_secret'] is False
    assert captured['api_key'] is None
    assert captured['base_url'] == 'http://127.0.0.1:11434/v1'

    recent_jobs = service._ai_job_repository.list_recent(
        project_id=None,
        capability_ids=('script_generation',),
    )
    assert recent_jobs[0].status == 'succeeded'
