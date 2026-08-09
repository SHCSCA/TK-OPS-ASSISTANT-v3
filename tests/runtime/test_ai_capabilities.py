from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from services.ai_default_prompts import DEFAULT_AGENT_PROMPT_CONFIG
from services.video_deconstruction_prompt import (
    VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT,
    VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT,
)

EXPECTED_CAPABILITY_IDS = {
    "script_generation",
    "script_rewrite",
    "storyboard_generation",
    "tts_generation",
    "subtitle_alignment",
    "video_transcription",
    "video_generation",
    "asset_analysis",
    "magic_cut",
}

LEGACY_AI_WRITES = (
    ("PUT", "/api/settings/ai-capabilities"),
    ("PUT", "/api/settings/ai-capabilities/providers/openai/secret"),
    ("POST", "/api/settings/ai-capabilities/providers/openai/health-check"),
    ("POST", "/api/settings/ai-providers/openai/models/refresh"),
    ("POST", "/api/ai-providers/health/refresh"),
    ("PUT", "/api/ai-providers/openai/models/gpt-5.4"),
)


def test_ai_capabilities_return_read_only_defaults_without_plaintext_secret(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/settings/ai-capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["scope"] == "runtime_local"
    assert payload["data"]["configVersion"]
    assert set(payload["data"]["diagnosticSummary"]) == {
        "configuredProviderCount",
        "readyProviderCount",
        "degradedProviderCount",
        "lastHealthRefreshAt",
    }

    capabilities = {
        item["capabilityId"]: item
        for item in payload["data"]["capabilities"]
    }
    assert set(capabilities) == EXPECTED_CAPABILITY_IDS

    providers = {
        item["provider"]: item for item in payload["data"]["providers"]
    }
    assert set(providers) == {
        "openai",
        "deepseek",
        "volcengine",
        "volcengine_tts",
    }
    assert providers["openai"]["configured"] is False
    assert providers["openai"]["maskedSecret"] == ""
    assert providers["openai"]["readiness"] == "not_configured"
    assert providers["openai"]["scope"] == "runtime_local"
    assert "apiKey" not in providers["openai"]

    assert capabilities["tts_generation"]["provider"] == "volcengine_tts"
    assert capabilities["tts_generation"]["model"] == "seed-tts-2.0"
    assert capabilities["asset_analysis"]["provider"] == "volcengine"
    assert capabilities["asset_analysis"]["model"] == "doubao-seed-2.0-pro"
    assert capabilities["video_transcription"]["provider"] == "volcengine"
    assert capabilities["video_transcription"]["model"] == "doubao-seed-2.0-pro"
    assert (
        capabilities["magic_cut"]["provider"],
        capabilities["magic_cut"]["model"],
    ) in {
        ("deepseek", "deepseek-chat"),
        ("volcengine", "doubao-seed-1.6"),
    }
    assert capabilities["magic_cut"]["enabled"] is False


def test_ai_capability_read_snapshot_uses_current_default_prompts(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/settings/ai-capabilities")

    assert response.status_code == 200
    capabilities = {
        item["capabilityId"]: item
        for item in response.json()["data"]["capabilities"]
    }

    for capability_id, actual in capabilities.items():
        expected = DEFAULT_AGENT_PROMPT_CONFIG[capability_id]
        assert actual["agentRole"] == expected["agent_role"]
        assert actual["systemPrompt"] == expected["system_prompt"]
        assert actual["userPromptTemplate"] == expected["user_prompt_template"]

    assert "quality_review" in DEFAULT_AGENT_PROMPT_CONFIG
    assert "quality_review" not in capabilities
    assert "{{voice_id}}" in capabilities["tts_generation"]["userPromptTemplate"]
    assert "{{audio_url}}" in capabilities["subtitle_alignment"]["userPromptTemplate"]
    assert "{{media_file}}" in capabilities["video_transcription"]["userPromptTemplate"]

    script_prompt = (
        capabilities["script_generation"]["systemPrompt"]
        + capabilities["script_generation"]["userPromptTemplate"]
    )
    assert "前 3 秒强钩子" in script_prompt
    assert "每 5-8 秒" in script_prompt
    assert "手机竖屏" in script_prompt
    assert "严格 JSON" in script_prompt

    video_prompt = (
        capabilities["video_transcription"]["systemPrompt"]
        + capabilities["video_transcription"]["userPromptTemplate"]
    )
    assert VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT in video_prompt
    assert VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT in video_prompt

    asset_prompt = (
        capabilities["asset_analysis"]["systemPrompt"]
        + capabilities["asset_analysis"]["userPromptTemplate"]
    )
    assert VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT in asset_prompt
    assert VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT in asset_prompt
    assert "脚本文案" in asset_prompt
    assert "视频关键帧" in asset_prompt
    assert "内容结构" in asset_prompt
    assert "严格 JSON" in asset_prompt


@pytest.mark.parametrize(
    ("method", "path"),
    LEGACY_AI_WRITES,
    ids=lambda value: str(value),
)
def test_legacy_ai_writes_are_rejected_before_body_parsing(
    runtime_client: TestClient,
    method: str,
    path: str,
) -> None:
    response = runtime_client.request(
        method,
        path,
        content=b"{ definitely-not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_legacy_ai_write_rejection_does_not_change_read_snapshot(
    runtime_client: TestClient,
) -> None:
    before = runtime_client.get("/api/settings/ai-capabilities")
    assert before.status_code == 200

    rejected = runtime_client.put(
        "/api/settings/ai-capabilities",
        json={"capabilities": []},
    )

    assert rejected.status_code == 410
    after = runtime_client.get("/api/settings/ai-capabilities")
    assert after.status_code == 200
    assert after.json()["data"] == before.json()["data"]


def test_provider_runtime_config_exposes_protocol_family_and_media_flags(
    runtime_app,
) -> None:
    service = runtime_app.state.ai_capability_service

    openai_runtime = service.get_provider_runtime_config("openai")
    deepseek_runtime = service.get_provider_runtime_config("deepseek")
    volcengine_runtime = service.get_provider_runtime_config("volcengine")
    volcengine_tts_runtime = service.get_provider_runtime_config("volcengine_tts")

    assert openai_runtime.protocol_family == "openai_responses"
    assert openai_runtime.supports_tts is False
    assert openai_runtime.supports_speech_to_text is True
    assert openai_runtime.requires_secret is True
    assert deepseek_runtime.protocol_family == "openai_chat"
    assert deepseek_runtime.supports_tts is False
    assert volcengine_runtime.protocol_family == "openai_chat"
    assert volcengine_runtime.supports_tts is False
    assert volcengine_runtime.supports_text_generation is True
    assert volcengine_tts_runtime.protocol_family == "volcengine_tts"
    assert volcengine_tts_runtime.supports_tts is True
    assert volcengine_tts_runtime.supports_text_generation is False
    with pytest.raises(HTTPException):
        service.get_provider_runtime_config("ollama")


def test_legacy_provider_catalog_and_model_reads_remain_available(
    runtime_client: TestClient,
) -> None:
    catalog_response = runtime_client.get("/api/settings/ai-providers/catalog")

    assert catalog_response.status_code == 200
    providers = {
        item["provider"]: item for item in catalog_response.json()["data"]
    }
    assert set(providers) == {
        "openai",
        "deepseek",
        "volcengine",
        "volcengine_tts",
    }
    assert providers["openai"]["kind"] == "commercial"
    assert providers["deepseek"]["region"] == "domestic"
    assert providers["volcengine"]["category"] == "model_hub"
    assert providers["volcengine_tts"]["category"] == "tts"
    assert providers["volcengine_tts"]["capabilities"] == ["tts"]
    assert "apiKey" not in providers["openai"]

    volcengine_models = runtime_client.get(
        "/api/settings/ai-providers/volcengine/models"
    )
    assert volcengine_models.status_code == 200
    models = volcengine_models.json()["data"]
    assert models
    assert all(item["provider"] == "volcengine" for item in models)
    assert any(
        "video_generation" in item["capabilityTypes"] for item in models
    )

    tts_models = runtime_client.get(
        "/api/settings/ai-providers/volcengine_tts/models"
    )
    assert tts_models.status_code == 200
    tts_model_ids = {item["modelId"] for item in tts_models.json()["data"]}
    assert "seed-tts-2.0" in tts_model_ids
    assert "seed-tts-1.0" not in tts_model_ids

    hidden_models = runtime_client.get(
        "/api/settings/ai-providers/ollama/models"
    )
    assert hidden_models.status_code == 404


def test_unconnected_media_and_custom_providers_are_hidden(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/settings/ai-providers/catalog")

    assert response.status_code == 200
    providers = {item["provider"]: item for item in response.json()["data"]}
    assert set(providers) == {
        "openai",
        "deepseek",
        "volcengine",
        "volcengine_tts",
    }
    assert "custom_tts_provider" not in providers
    assert "video_generation_provider" not in providers
    assert "volcengine_asr" not in providers


def test_ai_capability_support_matrix_limits_models_by_capability(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get(
        "/api/settings/ai-capabilities/support-matrix"
    )

    assert response.status_code == 200
    capabilities = {
        item["capabilityId"]: item
        for item in response.json()["data"]["capabilities"]
    }
    assert set(capabilities) == EXPECTED_CAPABILITY_IDS
    assert "openai" in capabilities["script_generation"]["providers"]
    assert "volcengine_tts" in capabilities["tts_generation"]["providers"]
    assert "volcengine" not in capabilities["tts_generation"]["providers"]
    assert all(
        "tts" in item["capabilityTypes"]
        or item["provider"].endswith("_speech")
        for item in capabilities["tts_generation"]["models"]
    )
    assert any(
        item["provider"] == "volcengine"
        and item["modelId"] == "seedance-2.0"
        for item in capabilities["video_generation"]["models"]
    )
    assert set(capabilities["video_transcription"]["providers"]) <= {
        "openai",
        "volcengine",
    }
    assert any(
        item["provider"] == "volcengine"
        and item["modelId"] == "doubao-seed-2.0-pro"
        for item in capabilities["video_transcription"]["models"]
    )
    assert all(
        "text_generation" in item["capabilityTypes"]
        and "video_generation" not in item["capabilityTypes"]
        for item in capabilities["magic_cut"]["models"]
    )
    assert {"openai", "volcengine"} <= set(
        capabilities["asset_analysis"]["providers"]
    )


def test_magic_cut_unknown_model_is_not_treated_as_supported(runtime_app) -> None:
    service = runtime_app.state.ai_capability_service

    assert service.model_supports_capability(
        "openai",
        "unknown-magic-cut-model",
        "magic_cut",
    ) is False
