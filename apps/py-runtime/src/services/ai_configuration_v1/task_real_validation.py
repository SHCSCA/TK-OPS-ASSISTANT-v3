from __future__ import annotations

from collections.abc import Sequence

from errors import DomainError, ErrorCode
from services.ai_execution_v1.types import (
    CapabilityValidationResult,
    ModelDiscoveryResult,
    ProviderCallError,
    ProviderFailureCategory,
    ProviderHealthResult,
    ProviderStageEvidence,
    ValidationStatus,
)

from .json_codec import dump_json
from .provider_adapters import DiscoveredModel
from .task_adapter_results import NormalizedCapability
from .validation_writer import ValidationEvidenceEntry


def select_health_entries(
    result: ProviderHealthResult,
    requested_stages: Sequence[str],
) -> tuple[ValidationEvidenceEntry, ...]:
    by_stage = {item.stage: item for item in result.stages}
    entries: list[ValidationEvidenceEntry] = []
    for stage in requested_stages:
        evidence = by_stage.get(stage)
        if evidence is None:
            raise DomainError(
                ErrorCode.AI_PROVIDER_RESPONSE_INVALID,
                "Provider 检查未返回完整阶段证据",
                status_code=502,
                loggable=True,
            )
        entries.append(ValidationEvidenceEntry(evidence=evidence))
    return tuple(entries)


def require_verified_entries(
    entries: Sequence[ValidationEvidenceEntry],
) -> None:
    for entry in entries:
        evidence = entry.evidence
        if evidence.status is ValidationStatus.CANCELLED:
            raise provider_error_to_domain(
                ProviderCallError(
                    ProviderFailureCategory.CANCELLED,
                    "Provider 调用已取消",
                )
            )
        if evidence.status is ValidationStatus.FAILED:
            raise provider_error_to_domain(
                _error_from_evidence(evidence)
            )


def discovery_models(
    result: ModelDiscoveryResult,
) -> tuple[DiscoveredModel, ...]:
    return tuple(
        DiscoveredModel(
            model_id=item.model_id,
            display_name=item.display_name,
            context_window=item.context_window,
        )
        for item in result.models
    )


def discovery_entries(
    result: ModelDiscoveryResult,
) -> tuple[ValidationEvidenceEntry, ...]:
    return (ValidationEvidenceEntry(evidence=result.evidence),)


def real_capability(
    result: CapabilityValidationResult,
) -> NormalizedCapability:
    verified = (
        result.evidence.status is ValidationStatus.VERIFIED
        and result.schema_valid
    )
    return NormalizedCapability(
        capability_key=result.capability_key,
        declared_supported=True,
        adapter_supported=True,
        contract_verified=verified,
        input_modalities_json=dump_json(["text"]),
        output_modalities_json=dump_json([result.output_type]),
        parameter_schema_json=dump_json({}),
        known_limits_json=dump_json({"validationMode": "real_small_call"}),
    )


def contract_only_capabilities(
    values: Sequence[NormalizedCapability],
) -> tuple[NormalizedCapability, ...]:
    return tuple(
        NormalizedCapability(
            capability_key=item.capability_key,
            declared_supported=item.declared_supported,
            adapter_supported=item.adapter_supported,
            contract_verified=False,
            input_modalities_json=item.input_modalities_json,
            output_modalities_json=item.output_modalities_json,
            parameter_schema_json=item.parameter_schema_json,
            known_limits_json=item.known_limits_json,
        )
        for item in values
    )


def capability_entry(
    result: CapabilityValidationResult,
) -> ValidationEvidenceEntry:
    return ValidationEvidenceEntry(
        evidence=result.evidence,
        capability_key=result.capability_key,
    )


def failure_entry(
    stage: str,
    error: Exception,
    *,
    capability_key: str | None = None,
) -> ValidationEvidenceEntry:
    call_error = (
        error
        if isinstance(error, ProviderCallError)
        else ProviderCallError(
            ProviderFailureCategory.NETWORK,
            "Provider 调用失败",
        )
    )
    return ValidationEvidenceEntry(
        evidence=ProviderStageEvidence(
            stage=stage,
            status=(
                ValidationStatus.CANCELLED
                if call_error.category is ProviderFailureCategory.CANCELLED
                else ValidationStatus.FAILED
            ),
            duration_ms=0,
            request_hash=call_error.request_hash,
            response_hash=call_error.response_hash,
            error_category=call_error.category,
            provider_status_code=call_error.status_code,
        ),
        capability_key=capability_key,
    )


def provider_error_to_domain(error: Exception) -> DomainError:
    if isinstance(error, DomainError):
        return error
    if not isinstance(error, ProviderCallError):
        return DomainError(
            ErrorCode.PROVIDER_CONNECTION_FAILED,
            "Provider 调用失败，请检查配置和网络",
            status_code=502,
            loggable=True,
        )
    mapping = {
        ProviderFailureCategory.AUTHENTICATION: (
            ErrorCode.AI_PROVIDER_AUTH_FAILED,
            "Provider 鉴权失败，请轮换凭据后重试",
            502,
        ),
        ProviderFailureCategory.RATE_LIMIT: (
            ErrorCode.AI_PROVIDER_RATE_LIMITED,
            "Provider 暂时限流，请稍后重试",
            429,
        ),
        ProviderFailureCategory.TIMEOUT: (
            ErrorCode.AI_PROVIDER_RESULT_UNKNOWN
            if error.request_sent
            else ErrorCode.AI_PROVIDER_TIMEOUT,
            "Provider 调用超时，远端结果可能未知"
            if error.request_sent
            else "Provider 调用超时",
            502 if error.request_sent else 504,
        ),
        ProviderFailureCategory.INVALID_REQUEST: (
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "Provider 配置或调用参数无效",
            422,
        ),
        ProviderFailureCategory.CONTENT_REJECTED: (
            ErrorCode.AI_CONTENT_REJECTED,
            "Provider 拒绝了本次内容",
            422,
        ),
        ProviderFailureCategory.INVALID_RESPONSE: (
            ErrorCode.AI_PROVIDER_RESPONSE_INVALID,
            "Provider 返回了无法识别的响应",
            502,
        ),
        ProviderFailureCategory.CANCELLED: (
            ErrorCode.TASK_STATE_CONFLICT,
            "Provider 调用已取消",
            409,
        ),
    }
    code, message, status = mapping.get(
        error.category,
        (
            ErrorCode.PROVIDER_CONNECTION_FAILED,
            "Provider 连接失败，请检查配置和网络",
            502,
        ),
    )
    headers = (
        {"Retry-After": str(max(0, round(error.retry_after_seconds)))}
        if error.retry_after_seconds is not None
        else None
    )
    return DomainError(
        code,
        message,
        status_code=status,
        loggable=True,
        headers=headers,
    )


def _error_from_evidence(
    evidence: ProviderStageEvidence,
) -> ProviderCallError:
    return ProviderCallError(
        evidence.error_category or ProviderFailureCategory.NETWORK,
        "Provider 阶段检查失败",
        status_code=evidence.provider_status_code,
        request_sent=evidence.stage == "real_small_call",
        request_hash=evidence.request_hash,
        response_hash=evidence.response_hash,
    )


__all__ = [
    "capability_entry",
    "contract_only_capabilities",
    "discovery_entries",
    "discovery_models",
    "failure_entry",
    "provider_error_to_domain",
    "real_capability",
    "require_verified_entries",
    "select_health_entries",
]
