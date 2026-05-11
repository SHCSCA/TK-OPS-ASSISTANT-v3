from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from schemas.voice import VoiceProfileCreateInput
from services.ai_capability_service import ProviderRuntimeConfig

log = logging.getLogger(__name__)

VOLCENGINE_TTS_PROVIDER = "volcengine_tts"
_VOLCENGINE_OPEN_API_ENDPOINT = "https://open.volcengineapi.com"
_VOLCENGINE_LIST_SPEAKERS_VERSION = "2025-05-20"
_VOLCENGINE_LIST_SPEAKERS_ACTION = "ListSpeakers"
_VOLCENGINE_LIST_SPEAKERS_SERVICE = "speech_saas_prod"
_DEFAULT_REGION = "cn-beijing"
# 优先使用 seed-tts-2.0，仅获取与 2.0 资源匹配的音色
_DEFAULT_RESOURCE_IDS = ("seed-tts-2.0",)


@dataclass(frozen=True, slots=True)
class _VolcengineOpenApiCredentials:
    access_key: str
    secret_key: str
    region: str


def fetch_provider_voice_profiles(
    provider_id: str,
    runtime: ProviderRuntimeConfig | None,
) -> list[VoiceProfileCreateInput]:
    if provider_id != VOLCENGINE_TTS_PROVIDER:
        raise HTTPException(status_code=400, detail="当前 Provider 暂不支持远端音色同步。")
    if runtime is None:
        raise HTTPException(status_code=400, detail="请先配置火山豆包语音 Provider 后再同步音色。")
    return fetch_volcengine_tts_voice_profiles(runtime)


def fetch_volcengine_tts_voice_profiles(
    runtime: ProviderRuntimeConfig,
) -> list[VoiceProfileCreateInput]:
    credentials = _resolve_open_api_credentials(runtime.api_key or "")
    if credentials is None:
        return _builtin_volcengine_tts_voice_profiles()

    raw_profiles: list[dict[str, Any]] = []
    for resource_id in _DEFAULT_RESOURCE_IDS:
        for speaker in _list_speakers(credentials, resource_id):
            speaker["_queried_resource"] = resource_id
            raw_profiles.append(speaker)

    profiles: list[VoiceProfileCreateInput] = []
    seen: set[str] = set()
    for item in raw_profiles:
        voice_type = str(item.get("VoiceType") or "").strip()
        if not voice_type or voice_type in seen:
            continue
        if not _is_2_0_compatible(voice_type, item):
            continue
        seen.add(voice_type)
        profiles.append(
            VoiceProfileCreateInput(
                provider=VOLCENGINE_TTS_PROVIDER,
                voiceId=voice_type,
                displayName=_string_value(item.get("Name"), fallback=voice_type),
                locale=_locale_from_speaker(item),
                tags=_tags_from_speaker(item),
                enabled=True,
            )
        )
    return profiles


def _is_2_0_compatible(voice_type: str, speaker: dict[str, Any]) -> bool:
    """判断音色是否与 seed-tts-2.0 兼容。
    API 查询已使用 ResourceIDs=["seed-tts-2.0"]，返回结果即为 2.0 兼容音色。
    仅在 API 明确返回非 2.0 ResourceID 时排除。
    """
    api_resource = _string_value(speaker.get("ResourceID")).lower()
    if api_resource and "2.0" not in api_resource:
        return False
    # API 用 seed-tts-2.0 查询返回的、或无 ResourceID 标注的音色，均视为 2.0 兼容
    return True


def _resolve_open_api_credentials(raw_secret: str) -> _VolcengineOpenApiCredentials | None:
    options = _parse_secret_options(raw_secret)
    access_key = (
        _option_value(options, "access_key", "accessKey", "openApiAccessKey", "open_api_access_key", "ak")
        or os.getenv("TK_OPS_VOLCENGINE_TTS_ACCESS_KEY", "").strip()
        or os.getenv("TK_OPS_VOLCENGINE_ACCESS_KEY", "").strip()
    )
    secret_key = (
        _option_value(options, "secret_key", "secretKey", "openApiSecretKey", "open_api_secret_key", "sk")
        or os.getenv("TK_OPS_VOLCENGINE_TTS_SECRET_KEY", "").strip()
        or os.getenv("TK_OPS_VOLCENGINE_SECRET_KEY", "").strip()
    )
    region = (
        _option_value(options, "region", "openApiRegion", "open_api_region")
        or os.getenv("TK_OPS_VOLCENGINE_TTS_REGION", "").strip()
        or _DEFAULT_REGION
    )
    if not access_key or not secret_key:
        return None
    return _VolcengineOpenApiCredentials(
        access_key=access_key,
        secret_key=secret_key,
        region=region,
    )


def _builtin_volcengine_tts_voice_profiles() -> list[VoiceProfileCreateInput]:
    """内置 seed-tts-2.0 兼容音色（仅含 uranus 系列）。
    无 OpenAPI 凭据时使用此硬编码列表作为兜底。
    """
    voices = [
        ("zh_female_vv_uranus_bigtts", "Vivi 2.0", "zh-CN", ["豆包", "2.0", "中文", "英语"]),
        ("zh_female_xiaohe_uranus_bigtts", "小何 2.0", "zh-CN", ["豆包", "2.0", "中文"]),
        ("zh_male_m191_uranus_bigtts", "云舟 2.0", "zh-CN", ["豆包", "2.0", "中文", "男声"]),
        ("zh_male_taocheng_uranus_bigtts", "小天 2.0", "zh-CN", ["豆包", "2.0", "中文", "男声"]),
    ]
    return [
        VoiceProfileCreateInput(
            provider=VOLCENGINE_TTS_PROVIDER,
            voiceId=voice_id,
            displayName=display_name,
            locale=locale,
            tags=tags,
            enabled=True,
        )
        for voice_id, display_name, locale, tags in voices
    ]


def _list_speakers(
    credentials: _VolcengineOpenApiCredentials,
    resource_id: str,
) -> list[dict[str, Any]]:
    page = 1
    limit = 100
    total = 0
    speakers: list[dict[str, Any]] = []
    while page == 1 or len(speakers) < total:
        payload = {
            "ResourceIDs": [resource_id],
            "Page": page,
            "Limit": limit,
        }
        response = _signed_open_api_request(credentials, payload)
        result = response.get("Result")
        if not isinstance(result, dict):
            break
        total = _int_value(result.get("Total"))
        rows = result.get("Speakers")
        if not isinstance(rows, list):
            break
        for row in rows:
            if isinstance(row, dict):
                speakers.append(row)
        if len(rows) < limit:
            break
        page += 1
    return speakers


def _signed_open_api_request(
    credentials: _VolcengineOpenApiCredentials,
    payload: dict[str, Any],
) -> dict[str, Any]:
    query = f"Action={_VOLCENGINE_LIST_SPEAKERS_ACTION}&Version={_VOLCENGINE_LIST_SPEAKERS_VERSION}"
    url = f"{_VOLCENGINE_OPEN_API_ENDPOINT}/?{query}"
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    request_time = datetime.now(UTC)
    x_date = request_time.strftime("%Y%m%dT%H%M%SZ")
    short_date = request_time.strftime("%Y%m%d")
    signed_headers = "host;x-content-sha256;x-date"
    canonical_headers = (
        f"host:open.volcengineapi.com\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{x_date}\n"
    )
    canonical_request = "\n".join(
        [
            "POST",
            "/",
            query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = (
        f"{short_date}/{credentials.region}/{_VOLCENGINE_LIST_SPEAKERS_SERVICE}/request"
    )
    string_to_sign = "\n".join(
        [
            "HMAC-SHA256",
            x_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature_key = _sign(
        _sign(
            _sign(
                _sign(credentials.secret_key.encode("utf-8"), short_date),
                credentials.region,
            ),
            _VOLCENGINE_LIST_SPEAKERS_SERVICE,
        ),
        "request",
    )
    signature = hmac.new(signature_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        "HMAC-SHA256 "
        f"Credential={credentials.access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    request = urllib.request.Request(
        url,
        data=payload_bytes,
        method="POST",
        headers={
            "Authorization": authorization,
            "Content-Type": "application/json; charset=UTF-8",
            "Host": "open.volcengineapi.com",
            "X-Content-Sha256": payload_hash,
            "X-Date": x_date,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read()
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("同步火山豆包语音音色失败")
        raise HTTPException(status_code=502, detail="同步火山豆包语音音色失败，请稍后重试。") from exc

    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="火山豆包语音音色接口返回无法解析。") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="火山豆包语音音色接口返回无法解析。")
    metadata = parsed.get("ResponseMetadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("Error"), dict):
        message = _string_value(metadata["Error"].get("Message"), fallback="远端返回错误。")
        raise HTTPException(status_code=502, detail=f"火山豆包语音音色同步失败：{message}")
    return parsed


def _sign(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _parse_secret_options(raw_secret: str) -> dict[str, str]:
    secret = (raw_secret or "").strip()
    if not secret.startswith("{"):
        return {}
    try:
        payload = json.loads(secret)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(key): str(value).strip()
        for key, value in payload.items()
        if value is not None and str(value).strip()
    }


def _option_value(options: dict[str, str], *keys: str) -> str:
    lowered = {key.lower(): value for key, value in options.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value:
            return value
    return ""


def _string_value(value: object, *, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _locale_from_speaker(item: dict[str, Any]) -> str:
    languages = item.get("Languages")
    if isinstance(languages, list):
        for language in languages:
            if not isinstance(language, dict):
                continue
            value = _string_value(language.get("Language")).lower()
            if value in {"zh", "zh-cn", "cn", "chinese"}:
                return "zh-CN"
            if value:
                return value
    return "zh-CN"


def _tags_from_speaker(item: dict[str, Any]) -> list[str]:
    tags = ["豆包"]
    for key in ("Gender", "Age", "ResourceID"):
        value = _string_value(item.get(key))
        if value and value not in tags:
            tags.append(value)
    for key in ("Categories", "NormalLabels", "SpecialLabels"):
        value = item.get(key)
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    for nested in entry.values():
                        _append_tag_values(tags, nested)
                else:
                    _append_tag_values(tags, entry)
    return tags[:8]


def _append_tag_values(tags: list[str], value: object) -> None:
    if isinstance(value, list):
        for item in value:
            _append_tag_values(tags, item)
        return
    text = _string_value(value)
    if text and text not in tags:
        tags.append(text)
