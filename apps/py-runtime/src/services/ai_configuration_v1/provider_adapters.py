from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)

from errors import DomainError, ErrorCode

log = logging.getLogger(__name__)
_MAX_RESPONSE_BYTES = 1_048_576


@dataclass(frozen=True, slots=True)
class ProviderConnection:
    adapter_type: str
    base_url: str
    credential: str | None
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class DiscoveredModel:
    model_id: str
    display_name: str
    context_window: int | None = None


@dataclass(frozen=True, slots=True)
class CapabilityProbe:
    capability_key: str
    declared_supported: bool
    adapter_supported: bool
    contract_verified: bool
    input_modalities: tuple[str, ...]
    output_modalities: tuple[str, ...]
    parameter_schema: Mapping[str, object]
    known_limits: Mapping[str, object]


class ProviderAdapter(Protocol):
    def check_health(self, connection: ProviderConnection) -> None: ...

    def discover_models(
        self,
        connection: ProviderConnection,
    ) -> Sequence[DiscoveredModel]: ...

    def probe_capabilities(
        self,
        connection: ProviderConnection,
        *,
        model_id: str,
        capability_keys: Sequence[str],
    ) -> Sequence[CapabilityProbe]: ...


class ProviderAdapterRegistry:
    def __init__(
        self,
        adapters: Mapping[str, ProviderAdapter] | None = None,
    ) -> None:
        default = {
            "direct_api": GenericHTTPProviderAdapter(),
            "openai_compatible": OpenAICompatibleProviderAdapter(),
            "comfyui": ComfyUIProviderAdapter(),
            "runninghub": GenericHTTPProviderAdapter(),
        }
        self._adapters = dict(adapters or default)

    def require(self, adapter_type: str) -> ProviderAdapter:
        adapter = self._adapters.get(adapter_type)
        if adapter is None:
            raise DomainError(
                ErrorCode.PROVIDER_ADAPTER_UNSUPPORTED,
                "Provider 适配器尚未接入",
                status_code=422,
            )
        return adapter


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


class GenericHTTPProviderAdapter:
    def check_health(self, connection: ProviderConnection) -> None:
        _request_json(
            connection,
            path="",
            allow_non_json=True,
        )

    def discover_models(
        self,
        connection: ProviderConnection,
    ) -> Sequence[DiscoveredModel]:
        payload = _request_json(connection, path="/models")
        return _parse_models(payload)

    def probe_capabilities(
        self,
        connection: ProviderConnection,
        *,
        model_id: str,
        capability_keys: Sequence[str],
    ) -> Sequence[CapabilityProbe]:
        del model_id
        self.check_health(connection)
        return tuple(
            _generic_probe(capability_key, verified=False)
            for capability_key in capability_keys
        )


class OpenAICompatibleProviderAdapter(GenericHTTPProviderAdapter):
    _SUPPORTED_CAPABILITIES = frozenset(
        {
            "topic_generation",
            "script_generation",
            "script_rewrite",
            "storyboard_generation",
            "video_deconstruction",
            "speech_to_text",
            "image_generation",
            "tts",
            "asset_analysis",
            "embedding",
        }
    )

    def check_health(self, connection: ProviderConnection) -> None:
        _request_json(connection, path="/models")

    def probe_capabilities(
        self,
        connection: ProviderConnection,
        *,
        model_id: str,
        capability_keys: Sequence[str],
    ) -> Sequence[CapabilityProbe]:
        del model_id
        self.check_health(connection)
        return tuple(
            _generic_probe(
                capability_key,
                verified=False,
                adapter_supported=(
                    capability_key in self._SUPPORTED_CAPABILITIES
                ),
            )
            for capability_key in capability_keys
        )


class ComfyUIProviderAdapter(GenericHTTPProviderAdapter):
    _SUPPORTED_CAPABILITIES = frozenset(
        {
            "image_generation",
            "text_to_video",
            "image_to_video",
        }
    )

    def check_health(self, connection: ProviderConnection) -> None:
        _request_json(connection, path="/system_stats")

    def discover_models(
        self,
        connection: ProviderConnection,
    ) -> Sequence[DiscoveredModel]:
        self.check_health(connection)
        return ()

    def probe_capabilities(
        self,
        connection: ProviderConnection,
        *,
        model_id: str,
        capability_keys: Sequence[str],
    ) -> Sequence[CapabilityProbe]:
        del model_id
        self.check_health(connection)
        return tuple(
            _generic_probe(
                capability_key,
                verified=False,
                adapter_supported=(
                    capability_key in self._SUPPORTED_CAPABILITIES
                ),
            )
            for capability_key in capability_keys
        )


def _request_json(
    connection: ProviderConnection,
    *,
    path: str,
    allow_non_json: bool = False,
) -> object:
    url = urljoin(f"{connection.base_url.rstrip('/')}/", path.lstrip("/"))
    headers = {"Accept": "application/json"}
    if connection.credential:
        headers["Authorization"] = f"Bearer {connection.credential}"
    request = Request(url, headers=headers, method="GET")
    opener = build_opener(_NoRedirectHandler())
    try:
        with opener.open(
            request,
            timeout=connection.timeout_seconds,
        ) as response:
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        log.warning(
            "Provider HTTP 检查失败",
            extra={"http_status": exc.code},
        )
        raise DomainError(
            ErrorCode.PROVIDER_CONNECTION_FAILED,
            "Provider 连接检查失败",
            status_code=502,
            loggable=True,
        ) from exc
    except (TimeoutError, URLError, OSError) as exc:
        log.warning("Provider 网络检查失败", exc_info=True)
        raise DomainError(
            ErrorCode.PROVIDER_CONNECTION_FAILED,
            "无法连接 Provider，请检查地址、凭据和网络",
            status_code=502,
            loggable=True,
        ) from exc
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise DomainError(
            ErrorCode.PROVIDER_CONNECTION_FAILED,
            "Provider 响应超过安全上限",
            status_code=502,
            loggable=True,
        )
    if allow_non_json and not raw.strip():
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        if allow_non_json:
            return {}
        raise DomainError(
            ErrorCode.PROVIDER_CONNECTION_FAILED,
            "Provider 返回了无法识别的响应",
            status_code=502,
            loggable=True,
        ) from exc


def _parse_models(payload: object) -> tuple[DiscoveredModel, ...]:
    rows: object
    if isinstance(payload, dict):
        rows = payload.get("data", payload.get("models", []))
    else:
        rows = payload
    if not isinstance(rows, list):
        raise DomainError(
            ErrorCode.PROVIDER_CONNECTION_FAILED,
            "Provider 模型清单格式无效",
            status_code=502,
            loggable=True,
        )
    models: list[DiscoveredModel] = []
    seen: set[str] = set()
    for item in rows[:5_000]:
        if isinstance(item, str):
            model_id = item.strip()
            display_name = model_id
        elif isinstance(item, dict):
            raw_id = item.get("id", item.get("name"))
            if not isinstance(raw_id, str):
                continue
            model_id = raw_id.strip()
            raw_name = item.get("display_name", item.get("name"))
            display_name = (
                raw_name.strip()
                if isinstance(raw_name, str) and raw_name.strip()
                else model_id
            )
        else:
            continue
        if not model_id or model_id in seen or len(model_id) > 256:
            continue
        seen.add(model_id)
        models.append(
            DiscoveredModel(
                model_id=model_id,
                display_name=display_name,
            )
        )
    return tuple(models)


def _generic_probe(
    capability_key: str,
    *,
    verified: bool,
    adapter_supported: bool = True,
) -> CapabilityProbe:
    return CapabilityProbe(
        capability_key=capability_key,
        declared_supported=True,
        adapter_supported=adapter_supported,
        contract_verified=verified,
        input_modalities=(),
        output_modalities=(),
        parameter_schema={},
        known_limits={},
    )
