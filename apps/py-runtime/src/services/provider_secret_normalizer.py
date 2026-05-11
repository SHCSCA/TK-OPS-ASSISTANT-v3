from __future__ import annotations

import json

from fastapi import HTTPException


VOLCENGINE_TTS_PROVIDER_ID = "volcengine_tts"


def normalize_provider_secret_for_storage(
    provider_id: str,
    *,
    existing_secret: str | None,
    api_key: str | None,
    access_token: str | None,
    app_id: str | None,
    open_api_access_key: str | None,
    open_api_secret_key: str | None,
    open_api_region: str | None,
) -> str:
    if provider_id != VOLCENGINE_TTS_PROVIDER_ID:
        normalized = _clean_secret_value(api_key)
        if not normalized:
            raise HTTPException(status_code=400, detail="Provider API Key 不能为空。")
        return normalized

    return _normalize_volcengine_tts_secret(
        existing_secret=existing_secret,
        api_key=api_key,
        access_token=access_token,
        app_id=app_id,
        open_api_access_key=open_api_access_key,
        open_api_secret_key=open_api_secret_key,
        open_api_region=open_api_region,
    )


def _normalize_volcengine_tts_secret(
    *,
    existing_secret: str | None,
    api_key: str | None,
    access_token: str | None,
    app_id: str | None,
    open_api_access_key: str | None,
    open_api_secret_key: str | None,
    open_api_region: str | None,
) -> str:
    existing = _parse_secret_json(existing_secret)
    raw_existing = _clean_secret_value(existing_secret)
    if not existing and raw_existing and not raw_existing.startswith("{"):
        existing["api_key"] = raw_existing

    token = _first_secret_value(
        access_token,
        api_key,
        _secret_option(existing, "api_key", "token", "access_token", "accessToken"),
    )
    resolved_app_id = _first_secret_value(
        app_id,
        _secret_option(existing, "app_id", "appid", "appId"),
    )
    access_key = _first_secret_value(
        open_api_access_key,
        _secret_option(
            existing,
            "access_key",
            "accessKey",
            "openApiAccessKey",
            "open_api_access_key",
            "ak",
        ),
    )
    secret_key = _first_secret_value(
        open_api_secret_key,
        _secret_option(
            existing,
            "secret_key",
            "secretKey",
            "openApiSecretKey",
            "open_api_secret_key",
            "sk",
        ),
    )
    region = _first_secret_value(
        open_api_region,
        _secret_option(existing, "region", "openApiRegion", "open_api_region"),
        "cn-beijing" if access_key or secret_key else "",
    )

    canonical: dict[str, str] = {}
    if token:
        canonical["api_key"] = token
    if resolved_app_id:
        canonical["app_id"] = resolved_app_id
    if access_key:
        canonical["access_key"] = access_key
    if secret_key:
        canonical["secret_key"] = secret_key
    if region:
        canonical["region"] = region

    if not canonical:
        raise HTTPException(status_code=400, detail="火山豆包语音凭据不能为空。")
    return json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))


def _parse_secret_json(raw_secret: str | None) -> dict[str, str]:
    secret = _clean_secret_value(raw_secret)
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


def _secret_option(options: dict[str, str], *keys: str) -> str:
    lowered = {key.lower(): value for key, value in options.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value:
            return value
    return ""


def _first_secret_value(*values: str | None) -> str:
    for value in values:
        cleaned = _clean_secret_value(value)
        if cleaned:
            return cleaned
    return ""


def _clean_secret_value(value: str | None) -> str:
    return (value or "").strip()

