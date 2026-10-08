from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from threading import Event


class ProviderFailureCategory(StrEnum):
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    SERVER = "server"
    INVALID_REQUEST = "invalid_request"
    CONTENT_REJECTED = "content_rejected"
    INVALID_RESPONSE = "invalid_response"
    CANCELLED = "cancelled"


class ValidationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CancelOutcome(StrEnum):
    REMOTE_CANCELLED = "remote_cancelled"
    LOCAL_TRANSPORT_CLOSED = "local_transport_closed"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class ProviderRevisionConfig:
    provider_profile_id: str
    provider_revision_id: str
    revision: int
    adapter_type: str
    base_url: str
    credential: str | None
    timeout_seconds: float
    max_concurrency: int
    extra_params: Mapping[str, object]
    cost_policy: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ModelRevisionConfig:
    model_profile_id: str
    model_revision_id: str
    revision: int
    model_id: str
    provider: ProviderRevisionConfig


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    input_units: int | None
    output_units: int | None
    cached_units: int | None
    total_units: int | None

    @property
    def reported(self) -> bool:
        return self.input_units is not None and self.output_units is not None

    def to_dict(self) -> dict[str, int | None]:
        return {
            "inputUnits": self.input_units,
            "outputUnits": self.output_units,
            "cachedUnits": self.cached_units,
            "totalUnits": self.total_units,
        }


@dataclass(frozen=True, slots=True)
class ProviderStageEvidence:
    stage: str
    status: ValidationStatus
    duration_ms: int
    request_hash: str | None = None
    response_hash: str | None = None
    response_id_hash: str | None = None
    usage: ProviderUsage | None = None
    error_category: ProviderFailureCategory | None = None
    provider_status_code: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderHealthResult:
    stages: tuple[ProviderStageEvidence, ...]


@dataclass(frozen=True, slots=True)
class DiscoveredProviderModel:
    model_id: str
    display_name: str
    context_window: int | None = None


@dataclass(frozen=True, slots=True)
class ModelDiscoveryResult:
    models: tuple[DiscoveredProviderModel, ...]
    evidence: ProviderStageEvidence


@dataclass(frozen=True, slots=True)
class CapabilityValidationResult:
    capability_key: str
    evidence: ProviderStageEvidence
    output_type: str
    schema_valid: bool


@dataclass(frozen=True, slots=True)
class AIProviderRequest:
    capability_key: str
    model: ModelRevisionConfig
    messages: Sequence[Mapping[str, object]] = field(default_factory=tuple)
    input_value: object | None = None
    max_output_units: int = 1
    temperature: float = 0.0
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class AIProviderResult:
    output_text: str
    request_hash: str
    response_hash: str
    response_id_hash: str | None
    finish_reason: str
    usage: ProviderUsage
    duration_ms: int


@dataclass(frozen=True, slots=True)
class ProviderCallHandle:
    call_id: str


class CancellationToken:
    """线程安全的协作取消令牌。"""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


class ProviderCallError(RuntimeError):
    """只携带安全分类和摘要，不保留外部响应正文。"""

    def __init__(
        self,
        category: ProviderFailureCategory,
        message: str,
        *,
        status_code: int | None = None,
        request_sent: bool = False,
        retry_after_seconds: float | None = None,
        request_hash: str | None = None,
        response_hash: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.status_code = status_code
        self.request_sent = request_sent
        self.retry_after_seconds = retry_after_seconds
        self.request_hash = request_hash
        self.response_hash = response_hash
