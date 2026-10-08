from __future__ import annotations

from collections.abc import Mapping

from errors import DomainError, ErrorCode
from services.ai_execution_v1.openai_compatible import (
    OpenAICompatibleProviderPort,
)
from services.ai_execution_v1.provider_ports import AIProviderPort


class AIProviderPortRegistry:
    """只负责 adapter 到端口的注册，不参与业务路由。"""

    def __init__(
        self,
        *,
        response_max_bytes: int,
        ports: Mapping[str, AIProviderPort] | None = None,
    ) -> None:
        self._ports = dict(
            ports
            or {
                "openai_compatible": OpenAICompatibleProviderPort(
                    response_max_bytes=response_max_bytes,
                )
            }
        )

    def require(self, adapter_type: str) -> AIProviderPort:
        port = self._ports.get(adapter_type)
        if port is None:
            raise DomainError(
                ErrorCode.PROVIDER_ADAPTER_UNSUPPORTED,
                "Provider 适配器尚未接入真实执行端口",
                status_code=422,
            )
        return port

    def resolve(self, adapter_type: str) -> AIProviderPort | None:
        return self._ports.get(adapter_type)


__all__ = ["AIProviderPortRegistry"]
