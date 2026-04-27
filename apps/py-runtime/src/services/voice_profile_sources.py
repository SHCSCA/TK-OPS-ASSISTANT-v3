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
_DEFAULT_RESOURCE_IDS = ("seed-tts-1.0", "seed-tts-2.0")


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
        raw_profiles.extend(_list_speakers(credentials, resource_id))

    profiles: list[VoiceProfileCreateInput] = []
    seen: set[str] = set()
    for item in raw_profiles:
        voice_type = str(item.get("VoiceType") or "").strip()
        if not voice_type or voice_type in seen:
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


def _resolve_open_api_credentials(raw_secret: str) -> _VolcengineOpenApiCredentials | None:
    options = _parse_secret_options(raw_secret)
    access_key = (
        _option_value(options, "access_key", "accessKey", "ak")
        or os.getenv("TK_OPS_VOLCENGINE_TTS_ACCESS_KEY", "").strip()
        or os.getenv("TK_OPS_VOLCENGINE_ACCESS_KEY", "").strip()
    )
    secret_key = (
        _option_value(options, "secret_key", "secretKey", "sk")
        or os.getenv("TK_OPS_VOLCENGINE_TTS_SECRET_KEY", "").strip()
        or os.getenv("TK_OPS_VOLCENGINE_SECRET_KEY", "").strip()
    )
    region = (
        _option_value(options, "region")
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
    voices = [
        ("zh_female_vv_uranus_bigtts", "Vivi 2.0", "zh-CN", ["豆包", "2.0", "中文", "英语"]),
        ("zh_female_xiaohe_uranus_bigtts", "小何 2.0", "zh-CN", ["豆包", "2.0", "中文"]),
        ("zh_male_m191_uranus_bigtts", "云舟 2.0", "zh-CN", ["豆包", "2.0", "中文", "男声"]),
        ("zh_male_taocheng_uranus_bigtts", "小天 2.0", "zh-CN", ["豆包", "2.0", "中文", "男声"]),
        ("en_male_miller", "Miller (English)", "en-US", ["豆包", "美语", "男声"]),
        ("en_female_alice", "Alice (English)", "en-US", ["豆包", "美语", "女声"]),
        ("en_male_jerry", "Jerry (English)", "en-US", ["豆包", "美语", "活力"]),
        ("en_female_sarah", "Sarah (English)", "en-US", ["豆包", "美语", "温柔"]),
        ("en_female_emily", "Emily (English)", "en-US", ["豆包", "美语", "童声"]),
        ("zh_female_common_iv_bigtts", "多语言女声", "zh-CN", ["豆包", "1.0", "中英双语", "女声"]),
        ("zh_male_common_iv_bigtts", "多语言男声", "zh-CN", ["豆包", "1.0", "中英双语", "男声"]),
        ("zh_male_lengkugege_emo_v2_mars_bigtts", "冷酷哥哥（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "男声"]),
        ("zh_female_tianxinxiaomei_emo_v2_mars_bigtts", "甜心小美（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "女声"]),
        ("zh_female_gaolengyujie_emo_v2_mars_bigtts", "高冷御姐（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "女声"]),
        ("zh_male_aojiaobazong_emo_v2_mars_bigtts", "傲娇霸总（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "男声"]),
        ("zh_male_jingqiangkanye_emo_mars_bigtts", "京腔侃爷（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "北京口音"]),
        ("zh_female_linjuayi_emo_v2_mars_bigtts", "邻居阿姨（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "女声"]),
        ("zh_male_yourougongzi_emo_v2_mars_bigtts", "优柔公子（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "男声"]),
        ("zh_male_ruyayichen_emo_v2_mars_bigtts", "儒雅男友（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "男声"]),
        ("zh_male_junlangnanyou_emo_v2_mars_bigtts", "俊朗男友（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "男声"]),
        ("zh_male_beijingxiaoye_emo_v2_mars_bigtts", "北京小爷（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "北京口音"]),
        ("zh_female_roumeinvyou_emo_v2_mars_bigtts", "柔美女友（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "女声"]),
        ("zh_male_yangguangqingnian_emo_v2_mars_bigtts", "阳光青年（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "男声"]),
        ("zh_female_meilinvyou_emo_v2_mars_bigtts", "魅力女友（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "女声"]),
        ("zh_female_shuangkuaisisi_emo_v2_mars_bigtts", "爽快思思（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "女声"]),
        ("zh_male_shenyeboke_emo_v2_mars_bigtts", "深夜播客（多情感）", "zh-CN", ["豆包", "1.0", "多情感", "播客"]),
        ("zh_female_vv_mars_bigtts", "Vivi", "zh-CN", ["豆包", "1.0", "中文", "通用"]),
        ("zh_female_qinqienvsheng_moon_bigtts", "亲切女声", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_xudong_conversation_wvae_bigtts", "快乐小东", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_female_sophie_conversation_wvae_bigtts", "魅力苏菲", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_female_tianmeitaozi_mars_bigtts", "甜美桃子", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_female_qingxinnvsheng_mars_bigtts", "清新女声", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_female_zhixingnvsheng_mars_bigtts", "知性女声", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_qingshuangnanda_mars_bigtts", "清爽男大", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_female_linjianvhai_moon_bigtts", "邻家女孩", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_yuanboxiaoshu_moon_bigtts", "渊博小叔", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_male_yangguangqingnian_moon_bigtts", "阳光青年", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_female_tianmeixiaoyuan_moon_bigtts", "甜美小源", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_female_qingchezizi_moon_bigtts", "清澈梓梓", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_jieshuoxiaoming_moon_bigtts", "解说小明", "zh-CN", ["豆包", "1.0", "中文", "解说"]),
        ("zh_female_kailangjiejie_moon_bigtts", "开朗姐姐", "zh-CN", ["豆包", "1.0", "中文", "自然口播"]),
        ("zh_male_linjiananhai_moon_bigtts", "邻家男孩", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_female_tianmeiyueyue_moon_bigtts", "甜美悦悦", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_female_xinlingjitang_moon_bigtts", "心灵鸡汤", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_female_daimengchuanmei_moon_bigtts", "呆萌川妹", "zh-CN", ["豆包", "1.0", "四川口音", "女声"]),
        ("zh_male_guangxiyuanzhou_moon_bigtts", "广西远舟", "zh-CN", ["豆包", "1.0", "广西口音", "男声"]),
        ("zh_male_zhoujielun_emo_v2_mars_bigtts", "双节棍小哥", "zh-CN", ["豆包", "1.0", "台湾口音", "男声"]),
        ("zh_female_wanwanxiaohe_moon_bigtts", "湾湾小何", "zh-CN", ["豆包", "1.0", "台湾口音", "女声"]),
        ("zh_female_wanqudashu_moon_bigtts", "湾区大叔", "zh-CN", ["豆包", "1.0", "广东口音"]),
        ("zh_male_guozhoudege_moon_bigtts", "广州德哥", "zh-CN", ["豆包", "1.0", "广东口音", "男声"]),
        ("zh_male_haoyuxiaoge_moon_bigtts", "浩宇小哥", "zh-CN", ["豆包", "1.0", "青岛口音", "男声"]),
        ("zh_male_beijingxiaoye_moon_bigtts", "北京小爷", "zh-CN", ["豆包", "1.0", "北京口音", "男声"]),
        ("zh_male_jingqiangkanye_moon_bigtts", "京腔侃爷", "zh-CN", ["豆包", "1.0", "北京口音", "男声"]),
        ("zh_female_meituojieer_moon_bigtts", "妹坨洁儿", "zh-CN", ["豆包", "1.0", "长沙口音", "女声"]),
        ("zh_female_popo_mars_bigtts", "婆婆", "zh-CN", ["豆包", "1.0", "中文", "角色"]),
        ("zh_female_gaolengyujie_moon_bigtts", "高冷御姐", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_aojiaobazong_moon_bigtts", "傲娇霸总", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_female_meilinvyou_moon_bigtts", "魅力女友", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_shenyeboke_moon_bigtts", "深夜播客", "zh-CN", ["豆包", "1.0", "中文", "播客"]),
        ("zh_female_sajiaonvyou_moon_bigtts", "柔美女友", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_female_yuanqinvyou_moon_bigtts", "撒娇学妹", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_dongfanghaoran_moon_bigtts", "东方浩然", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_female_wenrouxiaoya_moon_bigtts", "温柔小雅", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_tiancaitongsheng_mars_bigtts", "天才童声", "zh-CN", ["豆包", "1.0", "中文", "童声"]),
        ("zh_male_sunwukong_mars_bigtts", "猴哥", "zh-CN", ["豆包", "1.0", "中文", "角色"]),
        ("zh_male_xionger_mars_bigtts", "熊二", "zh-CN", ["豆包", "1.0", "中文", "角色"]),
        ("zh_female_peiqi_mars_bigtts", "佩奇猪", "zh-CN", ["豆包", "1.0", "中文", "角色"]),
        ("zh_female_wuzetian_mars_bigtts", "武则天", "zh-CN", ["豆包", "1.0", "中文", "角色"]),
        ("zh_female_yingtaowanzi_mars_bigtts", "樱桃丸子", "zh-CN", ["豆包", "1.0", "中文", "角色"]),
        ("zh_male_chunhui_mars_bigtts", "广告解说", "zh-CN", ["豆包", "1.0", "中文", "广告"]),
        ("zh_female_shaoergushi_mars_bigtts", "少儿故事", "zh-CN", ["豆包", "1.0", "中文", "故事"]),
        ("zh_male_silang_mars_bigtts", "四郎", "zh-CN", ["豆包", "1.0", "中文", "角色"]),
        ("zh_female_qiaopinvsheng_mars_bigtts", "俏皮女声", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_jieshuonansheng_mars_bigtts", "磁性解说男声", "zh-CN", ["豆包", "1.0", "中文", "解说"]),
        ("zh_female_jitangmeimei_mars_bigtts", "鸡汤妹妹", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_female_tiexinnvsheng_mars_bigtts", "贴心女声", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_changtianyi_mars_bigtts", "悬疑解说", "zh-CN", ["豆包", "1.0", "中文", "悬疑"]),
        ("zh_male_ruyaqingnian_mars_bigtts", "儒雅青年", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_male_baqiqingshu_mars_bigtts", "霸气青叔", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_male_qingcang_mars_bigtts", "擎苍", "zh-CN", ["豆包", "1.0", "中文", "旁白"]),
        ("zh_male_yangguangqingnian_mars_bigtts", "活力小哥", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
        ("zh_female_gufengshaoyu_mars_bigtts", "古风少御", "zh-CN", ["豆包", "1.0", "中文", "古风"]),
        ("zh_female_wenroushunv_mars_bigtts", "温柔淑女", "zh-CN", ["豆包", "1.0", "中文", "女声"]),
        ("zh_male_fanjuanqingnian_mars_bigtts", "反卷青年", "zh-CN", ["豆包", "1.0", "中文", "男声"]),
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
