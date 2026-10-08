from __future__ import annotations

from dataclasses import dataclass

from errors import ErrorCode

from .types import ProviderCallError, ProviderFailureCategory


@dataclass(frozen=True, slots=True)
class ProviderFailureDecision:
    error_code: str
    safe_summary: str
    failure_kind: str
    retryable: bool
    fallback_allowed: bool
    result_unknown: bool


def map_provider_failure(error: ProviderCallError) -> ProviderFailureDecision:
    category = error.category
    if error.request_sent and category in {
        ProviderFailureCategory.NETWORK,
        ProviderFailureCategory.TIMEOUT,
    }:
        return ProviderFailureDecision(
            error_code=ErrorCode.AI_PROVIDER_RESULT_UNKNOWN.value,
            safe_summary="Provider 请求已发送，但远端终态与费用无法确认",
            failure_kind="result_unknown",
            retryable=False,
            fallback_allowed=False,
            result_unknown=True,
        )
    mapping = {
        ProviderFailureCategory.NETWORK: (
            ErrorCode.PROVIDER_CONNECTION_FAILED.value,
            "Provider 连接失败，请稍后重试",
            True,
            True,
        ),
        ProviderFailureCategory.AUTHENTICATION: (
            ErrorCode.AI_PROVIDER_AUTH_FAILED.value,
            "Provider 鉴权失败，请轮换凭据后重新验证",
            False,
            False,
        ),
        ProviderFailureCategory.RATE_LIMIT: (
            ErrorCode.AI_PROVIDER_RATE_LIMITED.value,
            "Provider 暂时限流",
            True,
            True,
        ),
        ProviderFailureCategory.TIMEOUT: (
            ErrorCode.AI_PROVIDER_TIMEOUT.value,
            "Provider 调用在发送前超时",
            True,
            True,
        ),
        ProviderFailureCategory.SERVER: (
            ErrorCode.PROVIDER_CONNECTION_FAILED.value,
            "Provider 明确返回可恢复服务错误",
            True,
            True,
        ),
        ProviderFailureCategory.INVALID_REQUEST: (
            ErrorCode.AI_EXECUTION_INVALID.value,
            "Provider 拒绝当前请求参数",
            False,
            False,
        ),
        ProviderFailureCategory.CONTENT_REJECTED: (
            ErrorCode.AI_CONTENT_REJECTED.value,
            "Provider 拒绝当前内容",
            False,
            False,
        ),
        ProviderFailureCategory.INVALID_RESPONSE: (
            ErrorCode.AI_PROVIDER_RESPONSE_INVALID.value,
            "Provider 返回无法解析或不符合契约",
            False,
            True,
        ),
        ProviderFailureCategory.CANCELLED: (
            ErrorCode.TASK_STATE_CONFLICT.value,
            "Provider 调用已取消",
            False,
            False,
        ),
    }
    code, summary, retryable, fallback = mapping[category]
    return ProviderFailureDecision(
        error_code=code,
        safe_summary=summary,
        failure_kind="error",
        retryable=retryable,
        fallback_allowed=fallback,
        result_unknown=False,
    )


__all__ = ["ProviderFailureDecision", "map_provider_failure"]
