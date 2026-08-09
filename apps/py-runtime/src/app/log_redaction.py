from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

SENSITIVE_KEY_PARTS: tuple[str, ...] = (
    "authorization",
    "credential",
    "secret",
    "api_key",
    "apikey",
    "token",
    "password",
    "prompt",
    "license_key",
    "activation_code",
)
SAFE_TRACE_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "provider_profile_id",
        "model_profile_id",
        "prompt_profile_id",
        "prompt_version",
    }
)
SAFE_ROUTE_CONTEXT_KEYS: frozenset[str] = frozenset(
    {"path", "request_path", "route", "route_path"}
)
REDACTION_MARKER = "[已脱敏]"
LOCAL_PATH_MARKER = "[本地路径已隐藏]"
_CONTROLLED_TRACE_KEY_PATTERN = (
    r"(?:"
    r"request[_-]?id"
    r"|operation[_-]?id"
    r"|log[_-]?id"
    r"|error[_-]?code"
    r"|account[_-]?id"
    r"|resource[_-]?(?:type|id)"
    r"|task[_-]?id"
    r"|stage"
    r"|provider[_-]?profile[_-]?id"
    r"|model[_-]?profile[_-]?id"
    r"|capability[_-]?key"
    r"|prompt[_-]?(?:profile[_-]?id|version)"
    r"|config[_-]?revision"
    r"|retry[_-]?of"
    r")"
)
_CONTROLLED_TRACE_ASSIGNMENT_PATTERN = (
    r"[,;，；]\s*(?:"
    + r'"'
    + _CONTROLLED_TRACE_KEY_PATTERN
    + r'"'
    + r"|'"
    + _CONTROLLED_TRACE_KEY_PATTERN
    + r"'"
    + r"|"
    + _CONTROLLED_TRACE_KEY_PATTERN
    + r")\s*[:=]"
)
_UNQUOTED_SENSITIVE_VALUE_PATTERN = (
    r"(?:(?!"
    + _CONTROLLED_TRACE_ASSIGNMENT_PATTERN
    + r")[^\r\n])+"
)
_SENSITIVE_BODY_PATTERN = re.compile(
    r"""
    (?P<quote>["']?)
    (?P<key>
        (?:system[\s_-]*|user[\s_-]*)?prompt
        (?:[\s_-]*(?:text|body|content))?
        |
        provider[\s_-]*
        (?:
            (?:request|response)
            (?:[\s_-]*(?:body|payload|input))?
            | body
            | payload
            | input
        )
        |
        request[\s_-]*(?:body|payload)
    )
    (?P=quote)
    (?P<separator>\s*[:=]\s*)
    (?P<value>
        "(?:\\.|[^"\\\r\n])*"
        | '(?:\\.|[^'\\\r\n])*'
        | \{[^\r\n]*\}
        | \[[^\r\n]*\]
        |
    """
    + _UNQUOTED_SENSITIVE_VALUE_PATTERN
    + r"""
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"""
    (?P<quote>["']?)
    (?P<key>
        credential
        | secret
        | api[\s_-]*key
        | access[\s_-]*token
        | refresh[\s_-]*token
        | session[\s_-]*token
        | token
        | password
        | passphrase
        | license[\s_-]*key
        | activation[\s_-]*code
    )
    (?P=quote)
    (?P<separator>\s*[:=]\s*)
    (?P<value>
        "(?:\\.|[^"\\\r\n])*"
        | '(?:\\.|[^'\\\r\n])*'
        | \[[^\r\n\]]+\]
        |
    """
    + _UNQUOTED_SENSITIVE_VALUE_PATTERN
    + r"""
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
_AUTHORIZATION_PATTERN = re.compile(
    r"""
    (?P<quote>["']?)
    (?P<key>authorization)
    (?P=quote)
    (?P<separator>\s*[:=]\s*)
    (?P<scheme>bearer\s+)?
    (?P<value>
        "(?:\\.|[^"\\\r\n])*"
        | '(?:\\.|[^'\\\r\n])*'
        | \[[^\r\n\]]+\]
        |
    """
    + _UNQUOTED_SENSITIVE_VALUE_PATTERN
    + r"""
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
_BEARER_PATTERN = re.compile(
    r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+",
)
_QUOTED_WINDOWS_PATH_PATTERN = re.compile(
    r"""(?ix)
    (?P<quote>["'])
    (?:
        file:///?[A-Za-z]:[\\/]
        | [A-Za-z]:[\\/]
        | \\\\[^\\/\r\n]+[\\/]
    )
    [^"'\r\n]+
    (?P=quote)
    """
)
_WINDOWS_PATH_PATTERN = re.compile(
    r"""(?ix)
    (?<![A-Za-z0-9])
    (?:
        file:///?[A-Za-z]:[\\/]
        | [A-Za-z]:[\\/]
        | \\\\[^\\/\s]+[\\/]
    )
    [^\s\r\n,;，；)}\]]+
    """
)
_QUOTED_POSIX_PATH_PATTERN = re.compile(
    r"""(?ix)
    (?P<quote>["'])
    /
    (?!/)
    [^"'\r\n]+
    (?P=quote)
    """
)
_POSIX_PATH_PATTERN = re.compile(
    r"""(?ix)
    (?<![:/A-Za-z0-9])
    /
    (?!/)
    (?:[^\s,;，；)}\]/]+/)+
    [^\s,;，；)}\]/]+
    """
)
_SAFE_API_ROUTE_PATTERN = re.compile(
    r"^/api(?:/[A-Za-z0-9](?:[A-Za-z0-9._~-]*[A-Za-z0-9_~-])?)*?/?$"
)


def redact_log_text(value: object) -> str:
    text = str(value)
    if not text:
        return text
    json_payload = _redact_json_text(text)
    if json_payload is not None:
        return json_payload
    redacted = _QUOTED_WINDOWS_PATH_PATTERN.sub(
        lambda match: f"{match.group('quote')}{LOCAL_PATH_MARKER}{match.group('quote')}",
        text,
    )
    redacted = _QUOTED_POSIX_PATH_PATTERN.sub(
        lambda match: f"{match.group('quote')}{LOCAL_PATH_MARKER}{match.group('quote')}",
        redacted,
    )
    redacted = _WINDOWS_PATH_PATTERN.sub(LOCAL_PATH_MARKER, redacted)
    redacted = _POSIX_PATH_PATTERN.sub(LOCAL_PATH_MARKER, redacted)
    redacted = _AUTHORIZATION_PATTERN.sub(
        _replace_authorization_match,
        redacted,
    )
    redacted = _BEARER_PATTERN.sub(f"Bearer {REDACTION_MARKER}", redacted)
    redacted = _SENSITIVE_BODY_PATTERN.sub(_replace_sensitive_match, redacted)
    redacted = _SENSITIVE_ASSIGNMENT_PATTERN.sub(
        _replace_sensitive_match,
        redacted,
    )
    return redacted


def redact_log_value(value: object, *, parent_key: str = "") -> object:
    normalized_key = re.sub(
        r"[^a-z0-9]+",
        "_",
        parent_key.casefold(),
    ).strip("_")
    if (
        isinstance(value, str)
        and normalized_key in SAFE_ROUTE_CONTEXT_KEYS
        and _is_safe_api_route(value)
    ):
        return value
    if _is_sensitive_key(normalized_key):
        return REDACTION_MARKER

    if isinstance(value, Mapping):
        redacted_mapping: dict[str, object] = {}
        for key, item in value.items():
            key_text = str(key)
            safe_key = redact_log_text(key_text)
            redacted_mapping[safe_key] = redact_log_value(
                item,
                parent_key=key_text,
            )
        return redacted_mapping
    if isinstance(value, (list, tuple, set, frozenset)):
        return [
            redact_log_value(item, parent_key=parent_key)
            for item in value
        ]
    if isinstance(value, str):
        return redact_log_text(value)
    if isinstance(value, Path):
        return LOCAL_PATH_MARKER
    if isinstance(value, bytes):
        return "[二进制内容已隐藏]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return f"[{type(value).__name__} 对象已隐藏]"


def safe_exception_summary(
    exc_info: tuple[type[BaseException], BaseException, object] | tuple[None, None, None],
) -> str:
    exception = exc_info[1]
    if exception is None:
        return "Exception: 异常详情已脱敏"
    type_name = type(exception).__name__
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,127}", type_name):
        type_name = "Exception"
    return f"{type_name}: 异常详情已脱敏"


def _is_sensitive_key(normalized_key: str) -> bool:
    if not normalized_key or normalized_key in SAFE_TRACE_METADATA_KEYS:
        return False
    if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
        return True
    provider_body_parts = ("request", "response", "body", "payload", "input")
    return "provider" in normalized_key and any(
        part in normalized_key
        for part in provider_body_parts
    )


def _redact_json_text(text: str) -> str | None:
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        payload = json.loads(stripped)
    except (json.JSONDecodeError, RecursionError):
        return None
    if not isinstance(payload, (Mapping, list)):
        return None
    redacted = redact_log_value(payload)
    return json.dumps(redacted, ensure_ascii=False, separators=(",", ":"))


def _is_safe_api_route(value: str) -> bool:
    return (
        len(value) <= 512
        and ".." not in value
        and "\\" not in value
        and "file://" not in value.casefold()
        and _SAFE_API_ROUTE_PATTERN.fullmatch(value) is not None
    )


def _replace_sensitive_match(match: re.Match[str]) -> str:
    quote = match.group("quote")
    value = match.group("value")
    marker = REDACTION_MARKER
    if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
        marker = f"{value[0]}{REDACTION_MARKER}{value[0]}"
    return (
        f"{quote}{match.group('key')}{quote}"
        f"{match.group('separator')}{marker}"
    )


def _replace_authorization_match(match: re.Match[str]) -> str:
    quote = match.group("quote")
    value = match.group("value")
    has_bearer_scheme = bool(match.group("scheme"))
    value_quote = ""
    if len(value) >= 2 and value[0] in {'"', "'"} and value[-1] == value[0]:
        value_quote = value[0]
        has_bearer_scheme = value[1:-1].casefold().startswith("bearer ")
    scheme = "Bearer " if has_bearer_scheme else ""
    marker = f"{value_quote}{scheme}{REDACTION_MARKER}{value_quote}"
    return (
        f"{quote}{match.group('key')}{quote}"
        f"{match.group('separator')}{marker}"
    )
