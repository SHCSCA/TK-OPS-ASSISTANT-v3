from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Mapping

from ai.providers.errors import ProviderHTTPException

log = logging.getLogger(__name__)


def request_json(
    url: str,
    *,
    payload: Mapping[str, object] | None = None,
    timeout: float = 60.0,
    method: str = "POST",
    bearer_token: str | None = None,
    headers: Mapping[str, str] | None = None,
    api_key: str | None = None,
    api_key_header_name: str | None = None,
    api_key_query_name: str | None = None,
) -> dict[str, object]:
    request = _build_request(
        url,
        payload=payload,
        timeout=timeout,
        method=method,
        bearer_token=bearer_token,
        headers=headers,
        api_key=api_key,
        api_key_header_name=api_key_header_name,
        api_key_query_name=api_key_query_name,
        content_type="application/json",
    )
    body = _execute(request, timeout=timeout)
    if not body:
        raise ProviderHTTPException(
            status_code=502,
            detail="AI Provider 空响应或无效 JSON 响应。",
            error_code="ai_provider_empty_response",
        )
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        log.exception("AI Provider JSON 响应解析失败")
        raise ProviderHTTPException(
            status_code=502,
            detail="AI Provider 空响应或无效 JSON 响应。",
            error_code="ai_provider_empty_response",
        ) from exc
    if not isinstance(parsed, dict):
        raise ProviderHTTPException(
            status_code=502,
            detail="AI Provider 空响应或无效 JSON 响应。",
            error_code="ai_provider_empty_response",
        )
    return parsed


def request_bytes(
    url: str,
    *,
    payload: Mapping[str, object] | None = None,
    timeout: float = 60.0,
    method: str = "POST",
    bearer_token: str | None = None,
    headers: Mapping[str, str] | None = None,
    api_key: str | None = None,
    api_key_header_name: str | None = None,
    api_key_query_name: str | None = None,
) -> bytes:
    request = _build_request(
        url,
        payload=payload,
        timeout=timeout,
        method=method,
        bearer_token=bearer_token,
        headers=headers,
        api_key=api_key,
        api_key_header_name=api_key_header_name,
        api_key_query_name=api_key_query_name,
        content_type="application/json" if payload is not None else None,
    )
    return _execute(request, timeout=timeout)


def _build_request(
    url: str,
    *,
    payload: Mapping[str, object] | None,
    timeout: float,
    method: str,
    bearer_token: str | None,
    headers: Mapping[str, str] | None,
    api_key: str | None,
    api_key_header_name: str | None,
    api_key_query_name: str | None,
    content_type: str | None,
) -> urllib.request.Request:
    final_url = _append_query_auth(url, api_key=api_key, api_key_query_name=api_key_query_name)
    request_headers = _build_headers(
        bearer_token=bearer_token,
        headers=headers,
        api_key=api_key,
        api_key_header_name=api_key_header_name,
        content_type=content_type,
    )
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        final_url,
        data=body,
        headers=request_headers,
        method=method,
    )
    request.timeout = timeout  # type: ignore[attr-defined]
    return request


def _build_headers(
    *,
    bearer_token: str | None,
    headers: Mapping[str, str] | None,
    api_key: str | None,
    api_key_header_name: str | None,
    content_type: str | None,
) -> dict[str, str]:
    request_headers: dict[str, str] = {}
    if bearer_token:
        request_headers["Authorization"] = f"Bearer {bearer_token}"
    if headers:
        request_headers.update(headers)
    if api_key and api_key_header_name:
        request_headers[api_key_header_name] = api_key
    if content_type:
        request_headers["Content-Type"] = content_type
    return request_headers


def _append_query_auth(
    url: str,
    *,
    api_key: str | None,
    api_key_query_name: str | None,
) -> str:
    if not api_key or not api_key_query_name:
        return url
    parsed = urllib.parse.urlsplit(url)
    query_items = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query_items.append((api_key_query_name, api_key))
    rebuilt = parsed._replace(query=urllib.parse.urlencode(query_items))
    return urllib.parse.urlunsplit(rebuilt)


def _execute(request: urllib.request.Request, *, timeout: float) -> bytes:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = _read_error_body(exc)
        remote_message = _message_from_error_body(body)
        error_code, message = _error_info_from_status(exc.code)
        detail = _compose_detail(message, remote_message)
        log.warning(
            "AI Provider 返回 HTTP 错误: status=%s, code=%s, remote_message=%s",
            exc.code,
            error_code,
            remote_message or "",
        )
        raise ProviderHTTPException(status_code=502, detail=detail, error_code=error_code) from exc
    except (TimeoutError, socket.timeout) as exc:
        log.exception("AI Provider 请求超时")
        raise ProviderHTTPException(
            status_code=502,
            detail="AI Provider 请求超时，请稍后重试。",
            error_code="ai_provider_timeout",
        ) from exc
    except urllib.error.URLError as exc:
        if _is_timeout_reason(exc.reason):
            log.exception("AI Provider 请求超时")
            raise ProviderHTTPException(
                status_code=502,
                detail="AI Provider 请求超时，请稍后重试。",
                error_code="ai_provider_timeout",
            ) from exc
        log.exception("AI Provider 无法连接")
        raise ProviderHTTPException(
            status_code=502,
            detail="无法连接 AI Provider，请检查网络或地址配置。",
            error_code="ai_provider_unreachable",
        ) from exc
    except ProviderHTTPException:
        raise
    except Exception as exc:  # pragma: no cover - 防御性边界
        log.exception("AI Provider 请求失败")
        raise ProviderHTTPException(
            status_code=502,
            detail="AI Provider 请求失败，请稍后重试。",
            error_code="ai_provider_server_error",
        ) from exc


def _read_error_body(exc: urllib.error.HTTPError) -> bytes:
    try:
        return exc.read()
    except Exception:  # pragma: no cover - 防御性边界
        return b""


def _message_from_error_body(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return None


def _error_info_from_status(status_code: int) -> tuple[str, str]:
    if status_code == 400:
        return "request.invalid_payload", "AI Provider 接口参数有误，请检查配置。"
    if status_code == 404:
        return "runtime.resource_not_found", "AI Provider 目标资源不存在，请检查接口地址。"
    if status_code == 405:
        return "runtime.method_not_allowed", "AI Provider 接口方法不正确，请检查协议。"
    if status_code == 409:
        return "task.conflict", "AI Provider 当前状态冲突，请稍后重试。"
    if status_code == 422:
        return "request.validation_failed", "AI Provider 请求内容校验失败，请检查参数。"
    if status_code in {401, 403}:
        return "ai_provider_auth_failed", "AI Provider 认证失败，请检查 API Key。"
    if status_code == 429:
        return "ai_provider_rate_limited", "AI Provider 请求过于频繁，请稍后重试。"
    if status_code >= 500:
        return "ai_provider_server_error", "AI Provider 服务暂时不可用，请稍后重试。"
    return "ai_provider_server_error", "AI Provider 请求失败，请稍后重试。"


def _compose_detail(message: str, remote_message: str | None) -> str:
    if remote_message:
        return f"{message} 上游返回：{remote_message}"
    return message


def _is_timeout_reason(reason: object) -> bool:
    return isinstance(reason, (TimeoutError, socket.timeout))
