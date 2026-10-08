from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import socket
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from services.ai_execution_v1.types import (
    AIProviderRequest,
    AIProviderResult,
    CancellationToken,
    CancelOutcome,
    CapabilityValidationResult,
    ModelDiscoveryResult,
    ModelRevisionConfig,
    ProviderCallError,
    ProviderCallHandle,
    ProviderFailureCategory,
    ProviderHealthResult,
    ProviderRevisionConfig,
    ProviderStageEvidence,
    ValidationStatus,
)
from services.ai_execution_v1.openai_protocol import (
    chat_body,
    parse_generation_result,
    parse_models,
    protocol_variant,
    responses_body,
)

log = logging.getLogger(__name__)
_MODEL_HARD_LIMIT = 5_000
_VALIDATION_PROMPT = "Reply with exactly OK."
_TEXT_CAPABILITIES = frozenset(
    {
        "topic_generation",
        "script_generation",
        "script_rewrite",
        "storyboard_generation",
        "video_deconstruction",
        "subtitle_alignment",
        "asset_analysis",
    }
)


@dataclass(frozen=True, slots=True)
class _HTTPResult:
    payload: dict[str, object]
    request_hash: str
    response_hash: str
    duration_ms: int


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        del req, fp, code, msg, headers, newurl
        return None


class OpenAICompatibleProviderPort:
    """实现显式 chat-completions 或 responses 协议。"""

    def __init__(self, *, response_max_bytes: int) -> None:
        if response_max_bytes < 1_024:
            raise ValueError("Provider 响应上限配置无效")
        self._response_max_bytes = response_max_bytes
        self._opener = build_opener(_NoRedirectHandler())

    def health(
        self,
        provider: ProviderRevisionConfig,
        *,
        deadline_monotonic: float,
        cancel_token: CancellationToken,
    ) -> ProviderHealthResult:
        started = time.monotonic()
        try:
            result = self._request_json(
                provider,
                method="GET",
                path="/models",
                body=None,
                deadline_monotonic=deadline_monotonic,
                cancel_token=cancel_token,
            )
        except ProviderCallError as exc:
            duration = _elapsed_ms(started)
            if exc.category is ProviderFailureCategory.AUTHENTICATION:
                stages = (
                    _stage("network", ValidationStatus.VERIFIED, duration),
                    _failure_stage("authentication", exc, duration),
                )
            elif exc.category is ProviderFailureCategory.CANCELLED:
                stages = (
                    _failure_stage("network", exc, duration),
                    _stage("authentication", ValidationStatus.CANCELLED, duration),
                )
            else:
                stages = (
                    _failure_stage("network", exc, duration),
                    _stage("authentication", ValidationStatus.PARTIAL, duration),
                )
            return ProviderHealthResult(stages=stages)
        evidence = _stage(
            "network",
            ValidationStatus.VERIFIED,
            result.duration_ms,
            request_hash=result.request_hash,
            response_hash=result.response_hash,
        )
        authentication = _stage(
            "authentication",
            ValidationStatus.VERIFIED,
            result.duration_ms,
            request_hash=result.request_hash,
            response_hash=result.response_hash,
        )
        return ProviderHealthResult(stages=(evidence, authentication))

    def discover_models(
        self,
        provider: ProviderRevisionConfig,
        *,
        page_limit: int,
        deadline_monotonic: float,
        cancel_token: CancellationToken,
    ) -> ModelDiscoveryResult:
        if page_limit < 1:
            raise ValueError("模型发现条数上限无效")
        result = self._request_json(
            provider,
            method="GET",
            path="/models",
            body=None,
            deadline_monotonic=deadline_monotonic,
            cancel_token=cancel_token,
        )
        try:
            models = parse_models(
                result.payload,
                limit=min(page_limit, _MODEL_HARD_LIMIT),
            )
        except ProviderCallError as exc:
            raise ProviderCallError(
                exc.category,
                str(exc),
                request_sent=False,
                request_hash=result.request_hash,
                response_hash=result.response_hash,
            ) from None
        return ModelDiscoveryResult(
            models=models,
            evidence=_stage(
                "model_discovery",
                ValidationStatus.VERIFIED,
                result.duration_ms,
                request_hash=result.request_hash,
                response_hash=result.response_hash,
            ),
        )

    def validate_capability(
        self,
        model: ModelRevisionConfig,
        *,
        capability_key: str,
        max_output_units: int,
        deadline_monotonic: float,
        cancel_token: CancellationToken,
    ) -> CapabilityValidationResult:
        if capability_key not in _TEXT_CAPABILITIES:
            raise ProviderCallError(
                ProviderFailureCategory.INVALID_REQUEST,
                "当前 OpenAI-compatible 文本端口不支持该能力实测",
            )
        request = AIProviderRequest(
            capability_key=capability_key,
            model=model,
            input_value=_VALIDATION_PROMPT,
            max_output_units=min(max(1, max_output_units), 8),
            temperature=0.0,
        )
        result = self.execute(
            request,
            deadline_monotonic=deadline_monotonic,
            cancel_token=cancel_token,
        )
        status = (
            ValidationStatus.VERIFIED
            if result.usage.reported
            else ValidationStatus.PARTIAL
        )
        return CapabilityValidationResult(
            capability_key=capability_key,
            evidence=_stage(
                "real_small_call",
                status,
                result.duration_ms,
                request_hash=result.request_hash,
                response_hash=result.response_hash,
                response_id_hash=result.response_id_hash,
                usage=result.usage,
            ),
            output_type="text",
            schema_valid=bool(result.output_text.strip()),
        )

    def execute(
        self,
        request: AIProviderRequest,
        *,
        deadline_monotonic: float,
        cancel_token: CancellationToken,
    ) -> AIProviderResult:
        protocol = protocol_variant(request.model.provider)
        if protocol == "chat_completions":
            path = "/chat/completions"
            body = chat_body(request)
        else:
            path = "/responses"
            body = responses_body(request)
        result = self._request_json(
            request.model.provider,
            method="POST",
            path=path,
            body=body,
            deadline_monotonic=deadline_monotonic,
            cancel_token=cancel_token,
        )
        raw_id = result.payload.get("id")
        response_id_hash = (
            _sha256(raw_id.encode("utf-8"))
            if isinstance(raw_id, str)
            else None
        )
        try:
            return parse_generation_result(
                result.payload,
                protocol=protocol,
                expected_model_id=request.model.model_id,
                response_hash=result.response_hash,
                request_hash=result.request_hash,
                duration_ms=result.duration_ms,
                response_id_hash=response_id_hash,
            )
        except ProviderCallError as exc:
            raise ProviderCallError(
                exc.category,
                str(exc),
                status_code=exc.status_code,
                request_sent=True,
                retry_after_seconds=exc.retry_after_seconds,
                request_hash=result.request_hash,
                response_hash=result.response_hash,
            ) from None

    def cancel(self, handle: ProviderCallHandle) -> CancelOutcome:
        del handle
        return CancelOutcome.UNSUPPORTED

    def _request_json(
        self,
        provider: ProviderRevisionConfig,
        *,
        method: str,
        path: str,
        body: dict[str, object] | None,
        deadline_monotonic: float,
        cancel_token: CancellationToken,
    ) -> _HTTPResult:
        _raise_if_cancelled(cancel_token)
        timeout = min(
            provider.timeout_seconds,
            deadline_monotonic - time.monotonic(),
        )
        if timeout <= 0:
            raise ProviderCallError(
                ProviderFailureCategory.TIMEOUT,
                "Provider 调用已超过总时限",
            )
        url = _provider_url(provider.base_url, path)
        raw_body = None if body is None else _canonical_json(body)
        headers = {"Accept": "application/json"}
        if raw_body is not None:
            headers["Content-Type"] = "application/json"
        if provider.credential:
            headers["Authorization"] = f"Bearer {provider.credential}"
        request_hash = _sha256(raw_body or b"")
        request = Request(url, data=raw_body, headers=headers, method=method)
        started = time.monotonic()
        try:
            with self._opener.open(request, timeout=timeout) as response:
                raw_response = response.read(self._response_max_bytes + 1)
        except HTTPError as exc:
            error = _http_error(
                exc,
                request_sent=raw_body is not None,
                request_hash=request_hash,
            )
            exc.close()
            raise error from None
        except (TimeoutError, socket.timeout) as exc:
            del exc
            raise ProviderCallError(
                ProviderFailureCategory.TIMEOUT,
                "Provider 调用超时",
                request_sent=raw_body is not None,
                request_hash=request_hash,
            ) from None
        except (URLError, OSError) as exc:
            del exc
            raise ProviderCallError(
                ProviderFailureCategory.NETWORK,
                "Provider 网络连接失败",
                request_sent=raw_body is not None,
                request_hash=request_hash,
            ) from None
        _raise_if_cancelled(cancel_token)
        if len(raw_response) > self._response_max_bytes:
            raise ProviderCallError(
                ProviderFailureCategory.INVALID_RESPONSE,
                "Provider 响应超过安全上限",
                request_sent=raw_body is not None,
                request_hash=request_hash,
                response_hash=_sha256(raw_response),
            )
        try:
            payload = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderCallError(
                ProviderFailureCategory.INVALID_RESPONSE,
                "Provider 返回了无法识别的响应",
                request_sent=raw_body is not None,
                request_hash=request_hash,
                response_hash=_sha256(raw_response),
            ) from None
        if not isinstance(payload, dict):
            raise ProviderCallError(
                ProviderFailureCategory.INVALID_RESPONSE,
                "Provider 响应结构无效",
                request_sent=raw_body is not None,
                request_hash=request_hash,
                response_hash=_sha256(raw_response),
            )
        return _HTTPResult(
            payload=payload,
            request_hash=request_hash,
            response_hash=_sha256(raw_response),
            duration_ms=_elapsed_ms(started),
        )


def _provider_url(base_url: str, path: str) -> str:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ProviderCallError(
            ProviderFailureCategory.INVALID_REQUEST,
            "Provider Base URL 不符合安全规则",
        )
    if parsed.scheme == "http" and not _is_loopback(parsed.hostname):
        raise ProviderCallError(
            ProviderFailureCategory.INVALID_REQUEST,
            "非本机 Provider 必须使用 HTTPS",
        )
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _is_loopback(hostname: str) -> bool:
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _http_error(
    error: HTTPError,
    *,
    request_sent: bool,
    request_hash: str,
) -> ProviderCallError:
    status = int(error.code)
    if status in {401, 403}:
        category = ProviderFailureCategory.AUTHENTICATION
    elif status == 429:
        category = ProviderFailureCategory.RATE_LIMIT
    elif status in {408, 504}:
        category = ProviderFailureCategory.TIMEOUT
    elif status >= 500:
        category = ProviderFailureCategory.SERVER
    elif 400 <= status < 500:
        category = ProviderFailureCategory.INVALID_REQUEST
    else:
        category = ProviderFailureCategory.INVALID_RESPONSE
    return ProviderCallError(
        category,
        "Provider 返回失败状态",
        status_code=status,
        request_sent=request_sent,
        retry_after_seconds=_retry_after(error.headers.get("Retry-After")),
        request_hash=request_hash,
    )


def _retry_after(raw: object) -> float | None:
    try:
        value = float(str(raw))
    except (TypeError, ValueError):
        try:
            parsed = parsedate_to_datetime(str(raw))
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        value = (parsed - datetime.now(UTC)).total_seconds()
    return max(0.0, min(value, 60.0))


def _stage(
    stage: str,
    status: ValidationStatus,
    duration_ms: int,
    **kwargs: object,
) -> ProviderStageEvidence:
    return ProviderStageEvidence(stage=stage, status=status, duration_ms=duration_ms, **kwargs)


def _failure_stage(
    stage: str,
    error: ProviderCallError,
    duration_ms: int,
) -> ProviderStageEvidence:
    return _stage(
        stage,
        ValidationStatus.FAILED,
        duration_ms,
        error_category=error.category,
        provider_status_code=error.status_code,
        request_hash=error.request_hash,
        response_hash=error.response_hash,
    )


def _raise_if_cancelled(token: CancellationToken) -> None:
    if token.is_cancelled():
        raise ProviderCallError(
            ProviderFailureCategory.CANCELLED,
            "Provider 调用已取消",
        )


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1_000))
