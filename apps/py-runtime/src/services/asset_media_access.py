from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any

log = logging.getLogger(__name__)

MEDIA_ACCESS_TOKEN_TTL_SECONDS = 15 * 60
_MEDIA_ACCESS_SECRET = secrets.token_bytes(32)


def create_asset_media_token(
    asset_id: str,
    *,
    project_id: str | None,
    expires_in_seconds: int = MEDIA_ACCESS_TOKEN_TTL_SECONDS,
) -> str:
    expires_at = int(time.time()) + expires_in_seconds
    payload = {
        "assetId": asset_id,
        "projectId": project_id,
        "exp": expires_at,
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded_payload = _encode(payload_bytes)
    signature = _sign(encoded_payload.encode("ascii"))
    return f"{encoded_payload}.{signature}"


def validate_asset_media_token(
    token: str | None,
    *,
    asset_id: str,
    project_id: str | None,
) -> bool:
    if not token:
        return False

    try:
        encoded_payload, signature = token.split(".", 1)
        expected_signature = _sign(encoded_payload.encode("ascii"))
        if not hmac.compare_digest(signature, expected_signature):
            return False

        payload = json.loads(_decode(encoded_payload))
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        log.warning("资产媒体访问令牌解析失败 asset_id=%s error=%s", asset_id, exc)
        return False

    return _payload_matches(payload, asset_id=asset_id, project_id=project_id)


def _payload_matches(payload: Any, *, asset_id: str, project_id: str | None) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("assetId") != asset_id:
        return False
    if payload.get("projectId") != project_id:
        return False
    try:
        expires_at = int(payload.get("exp"))
    except (TypeError, ValueError):
        return False
    return expires_at >= int(time.time())


def _sign(payload: bytes) -> str:
    digest = hmac.new(_MEDIA_ACCESS_SECRET, payload, hashlib.sha256).digest()
    return _encode(digest)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}").decode("utf-8")
