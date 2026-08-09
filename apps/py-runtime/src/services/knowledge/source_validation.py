from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

from errors import DomainError, ErrorCode

CONTROLLED_FILE_REF_PATTERN = re.compile(
    r"^file_ref_[A-Za-z0-9_-]{8,128}$"
)


def require_controlled_file_ref(value: str) -> str:
    reference = value.strip()
    if not CONTROLLED_FILE_REF_PATTERN.fullmatch(reference):
        raise DomainError(
            ErrorCode.CONTROLLED_FILE_REF_INVALID,
            "文件引用不是受控文件选择器生成的令牌",
            status_code=422,
        )
    return reference


def normalize_public_https_url(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        port_value = parsed.port
    except ValueError as exc:
        raise _invalid_url("URL 来源地址格式无效") from exc
    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise _invalid_url("URL 来源必须是不含凭据和片段的 HTTPS 地址")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise _invalid_url("URL 来源不能指向本机或私有网络")
    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise _invalid_url("URL 来源主机名格式无效") from exc
    port = "" if port_value in (None, 443) else f":{port_value}"
    return urlunsplit(
        (
            "https",
            f"{hostname}{port}",
            parsed.path or "/",
            parsed.query,
            "",
        )
    )


def _invalid_url(message: str) -> DomainError:
    return DomainError(
        ErrorCode.KNOWLEDGE_SOURCE_INVALID,
        message,
        status_code=422,
    )
