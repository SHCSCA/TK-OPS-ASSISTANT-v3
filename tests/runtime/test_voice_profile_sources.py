from __future__ import annotations

import json

import pytest

from services.ai_capability_service import ProviderRuntimeConfig
from services.voice_profile_sources import fetch_volcengine_tts_voice_profiles


def test_volcengine_tts_voice_source_uses_seed_tts_2_and_nested_categories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider="volcengine_tts",
        label="火山豆包语音",
        api_key=json.dumps(
            {
                "api_key": "tts-token-test",
                "openApiAccessKey": "openapi-ak-test",
                "openApiSecretKey": "openapi-sk-test",
                "openApiRegion": "cn-beijing",
            },
            ensure_ascii=False,
        ),
        base_url="https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse",
        secret_source="test",
        requires_secret=True,
        supports_text_generation=False,
        supports_tts=True,
        protocol_family="volcengine_tts",
    )
    captured_payloads: list[dict[str, object]] = []

    def fake_signed_request(credentials, payload: dict[str, object]) -> dict[str, object]:
        captured_payloads.append(payload)
        assert credentials.access_key == "openapi-ak-test"
        assert credentials.secret_key == "openapi-sk-test"
        return {
            "Result": {
                "Total": 1,
                "Speakers": [
                    {
                        "VoiceType": "zh_female_tianmei_moon_bigtts",
                        "Name": "豆包甜美女声",
                        "ResourceID": "seed-tts-2.0",
                        "Gender": "女声",
                        "Age": "青年",
                        "Languages": [{"Language": "zh"}],
                        "Categories": [{"Categories": ["视频配音", "通用场景"]}],
                        "NormalLabels": [{"Labels": ["自然口播"]}],
                        "SpecialLabels": [{"Labels": ["明亮"]}],
                    }
                ],
            }
        }

    monkeypatch.setattr(
        "services.voice_profile_sources._signed_open_api_request",
        fake_signed_request,
    )

    profiles = fetch_volcengine_tts_voice_profiles(runtime)

    assert captured_payloads == [
        {"ResourceIDs": ["seed-tts-2.0"], "Page": 1, "Limit": 100}
    ]
    assert len(profiles) == 1
    assert profiles[0].provider == "volcengine_tts"
    assert profiles[0].voiceId == "zh_female_tianmei_moon_bigtts"
    assert profiles[0].displayName == "豆包甜美女声"
    assert profiles[0].locale == "zh-CN"
    assert "视频配音" in profiles[0].tags
    assert "通用场景" in profiles[0].tags
    assert "自然口播" in profiles[0].tags

