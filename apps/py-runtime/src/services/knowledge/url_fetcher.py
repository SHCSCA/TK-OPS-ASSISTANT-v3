from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from collections.abc import Callable
from urllib.parse import quote, urljoin, urlsplit

from errors import DomainError, ErrorCode
from services.knowledge.index_policy import KnowledgeIndexPolicy
from services.knowledge.ports import ResolvedKnowledgeContent
from services.knowledge.source_validation import normalize_public_https_url

HostAddressResolver = Callable[[str, int], tuple[str, ...]]
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_READ_CHUNK_SIZE = 64 * 1024


class SecureKnowledgeUrlFetcher:
    """以固定公共地址、TLS 主机校验和有界读取获取 URL 来源。"""

    def __init__(
        self,
        *,
        address_resolver: HostAddressResolver | None = None,
    ) -> None:
        self._address_resolver = address_resolver or _resolve_host_addresses
        self._ssl_context = ssl.create_default_context()

    def fetch(
        self,
        url: str,
        *,
        policy: KnowledgeIndexPolicy,
    ) -> ResolvedKnowledgeContent:
        current = normalize_public_https_url(url)
        for redirect_count in range(policy.max_redirects + 1):
            response, connection = self._open(current, policy=policy)
            try:
                if response.status in _REDIRECT_STATUSES:
                    if redirect_count >= policy.max_redirects:
                        raise _index_error("URL 来源重定向次数超过限制")
                    location = response.getheader("Location")
                    if not location:
                        raise _index_error("URL 来源重定向缺少目标地址")
                    current = normalize_public_https_url(
                        urljoin(current, location)
                    )
                    continue
                if not 200 <= response.status < 300:
                    raise _index_error("URL 来源返回不可用的 HTTP 状态")
                content = _read_bounded(
                    response,
                    max_bytes=policy.max_source_bytes,
                )
                return ResolvedKnowledgeContent(
                    data=content,
                    media_type=response.getheader("Content-Type"),
                )
            except DomainError:
                raise
            except (
                OSError,
                TimeoutError,
                ssl.SSLError,
                http.client.HTTPException,
            ) as exc:
                raise _index_error("URL 来源连接或读取失败") from exc
            finally:
                response.close()
                connection.close()
        raise _index_error("URL 来源重定向次数超过限制")

    def _open(
        self,
        url: str,
        *,
        policy: KnowledgeIndexPolicy,
    ) -> tuple[http.client.HTTPResponse, "_PinnedHTTPSConnection"]:
        parsed = urlsplit(url)
        host = parsed.hostname
        if host is None:
            raise _index_error("URL 来源缺少主机名")
        try:
            port = parsed.port or 443
        except ValueError as exc:
            raise _index_error("URL 来源端口格式无效") from exc
        addresses = self._address_resolver(host, port)
        _require_public_addresses(addresses)
        connection = _PinnedHTTPSConnection(
            host,
            port=port,
            address=addresses[0],
            timeout=policy.url_timeout_seconds,
            context=self._ssl_context,
        )
        try:
            connection.request(
                "GET",
                _request_target(url),
                headers={
                    "Accept-Encoding": "identity",
                    "User-Agent": "TK-OPS-KnowledgeIndexer/1",
                },
            )
            return connection.getresponse(), connection
        except (OSError, TimeoutError, ssl.SSLError, http.client.HTTPException) as exc:
            connection.close()
            raise _index_error("URL 来源连接或读取失败") from exc


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        *,
        port: int,
        address: str,
        timeout: int,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(
            host,
            port=port,
            timeout=timeout,
            context=context,
        )
        self._address = address

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self._address, self.port),
            self.timeout,
            self.source_address,
        )
        try:
            self.sock = self._context.wrap_socket(
                raw_socket,
                server_hostname=self.host,
            )
        except Exception:
            raw_socket.close()
            raise


def _resolve_host_addresses(host: str, port: int) -> tuple[str, ...]:
    try:
        rows = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise _index_error("URL 来源主机无法解析") from exc
    addresses = tuple(dict.fromkeys(row[4][0] for row in rows))
    if not addresses:
        raise _index_error("URL 来源主机没有可用地址")
    return addresses


def _require_public_addresses(addresses: tuple[str, ...]) -> None:
    if not addresses:
        raise _index_error("URL 来源主机没有可用地址")
    try:
        parsed = [
            ipaddress.ip_address(value.split("%", 1)[0])
            for value in addresses
        ]
    except ValueError as exc:
        raise _index_error("URL 来源主机解析结果无效") from exc
    if any(not address.is_global for address in parsed):
        raise _index_error("URL 来源不能解析到本机或私有网络")


def _request_target(url: str) -> str:
    parsed = urlsplit(url)
    path = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
    query = quote(parsed.query, safe="=&%:@!$'()*+,;/?-._~")
    return path if not query else f"{path}?{query}"


def _read_bounded(
    response: http.client.HTTPResponse,
    *,
    max_bytes: int,
) -> bytes:
    declared_length = response.getheader("Content-Length")
    if declared_length is not None:
        try:
            parsed_length = int(declared_length)
        except ValueError as exc:
            raise _index_error("URL 来源响应大小标记无效") from exc
        if parsed_length < 0 or parsed_length > max_bytes:
            raise _index_error("URL 来源响应超过配置的大小限制")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(_READ_CHUNK_SIZE, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise _index_error("URL 来源响应超过配置的大小限制")
        chunks.append(chunk)
    return b"".join(chunks)


def _index_error(message: str) -> DomainError:
    return DomainError(
        ErrorCode.KNOWLEDGE_INDEX_FAILED,
        message,
        status_code=422,
        loggable=True,
    )
