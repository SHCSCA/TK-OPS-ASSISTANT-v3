from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from errors import DomainError, ErrorCode

_FORBIDDEN_KEYS = frozenset(
    {
        "credential",
        "credentialref",
        "apikey",
        "authorization",
        "headers",
        "prompt",
        "input",
        "rawrequest",
        "rawresponse",
        "absolutepath",
        "userprofile",
        "cookie",
        "token",
    }
)
_VALUE_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(?:sk|pk|api)[-_][A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/@]+:[^\s/@]+@"),
    re.compile(r"(?i)(?:^|[\s\"'])[A-Z]:[\\/][^\s\"']+"),
    re.compile(r"(?:^|[\s\"'])(?:\\\\[^\s\\]+\\[^\s]+|/(?:home|Users|var|tmp|etc)/[^\s\"']+)"),
    re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    re.compile(r"(?<![A-Za-z0-9_])@[A-Za-z0-9_.-]{2,24}\b"),
)


def assert_safe_evidence(value: object) -> None:
    """阻止敏感字段或值进入日志、事件与 evidence 出口。"""
    if _contains_sensitive_value(value):
        raise DomainError(
            ErrorCode.AI_EVIDENCE_REDACTION_FAILED,
            "AI 执行证据未通过脱敏检查",
            status_code=500,
            loggable=True,
        )


def _contains_sensitive_value(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized in _FORBIDDEN_KEYS:
                return True
            if _contains_sensitive_value(item):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return any(_contains_sensitive_value(item) for item in value)
    if isinstance(value, str):
        return any(pattern.search(value) is not None for pattern in _VALUE_PATTERNS)
    return False


__all__ = ["assert_safe_evidence"]
