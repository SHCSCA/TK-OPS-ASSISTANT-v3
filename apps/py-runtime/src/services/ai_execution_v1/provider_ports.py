from __future__ import annotations

from typing import Protocol

from services.ai_execution_v1.types import (
    AIProviderRequest,
    AIProviderResult,
    CancellationToken,
    CancelOutcome,
    CapabilityValidationResult,
    ModelDiscoveryResult,
    ModelRevisionConfig,
    ProviderCallHandle,
    ProviderHealthResult,
    ProviderRevisionConfig,
)


class AIProviderPort(Protocol):
    def health(
        self,
        provider: ProviderRevisionConfig,
        *,
        deadline_monotonic: float,
        cancel_token: CancellationToken,
    ) -> ProviderHealthResult: ...

    def discover_models(
        self,
        provider: ProviderRevisionConfig,
        *,
        page_limit: int,
        deadline_monotonic: float,
        cancel_token: CancellationToken,
    ) -> ModelDiscoveryResult: ...

    def validate_capability(
        self,
        model: ModelRevisionConfig,
        *,
        capability_key: str,
        max_output_units: int,
        deadline_monotonic: float,
        cancel_token: CancellationToken,
    ) -> CapabilityValidationResult: ...

    def execute(
        self,
        request: AIProviderRequest,
        *,
        deadline_monotonic: float,
        cancel_token: CancellationToken,
    ) -> AIProviderResult: ...

    def cancel(self, handle: ProviderCallHandle) -> CancelOutcome: ...


__all__ = ["AIProviderPort"]
