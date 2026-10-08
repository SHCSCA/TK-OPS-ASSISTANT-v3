from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from domain.models.ai_execution_evidence import AIProviderValidationRun
from errors import ErrorCode
from services.ai_execution_v1.types import (
    ProviderFailureCategory,
    ProviderStageEvidence,
    ValidationStatus,
)

from .json_codec import dump_json
from .mutation_helpers import utc_now
from .task_execution_context import (
    ModelExecutionConfig,
    ProviderExecutionConfig,
)
from .unit_of_work import AIConfigurationTransaction


@dataclass(frozen=True, slots=True)
class ValidationEvidenceEntry:
    evidence: ProviderStageEvidence
    capability_key: str | None = None


def save_validation_entries(
    transaction: AIConfigurationTransaction,
    *,
    provider: ProviderExecutionConfig,
    model: ModelExecutionConfig | None,
    task_id: str,
    entries: tuple[ValidationEvidenceEntry, ...],
) -> tuple[AIProviderValidationRun, ...]:
    saved: list[AIProviderValidationRun] = []
    now = utc_now()
    for entry in entries:
        evidence = entry.evidence
        usage_json = (
            None
            if evidence.usage is None
            else dump_json(evidence.usage.to_dict())
        )
        row = AIProviderValidationRun(
            id=f"pval_{uuid4().hex}",
            provider_profile_id=provider.id,
            provider_revision=provider.revision,
            model_profile_id=None if model is None else model.id,
            model_revision=None if model is None else model.revision,
            capability_key=entry.capability_key,
            stage=evidence.stage,
            status=evidence.status.value,
            task_id=task_id,
            request_hash=evidence.request_hash,
            response_hash=evidence.response_hash,
            response_id_hash=evidence.response_id_hash,
            usage_json=usage_json,
            duration_ms=evidence.duration_ms,
            error_code=_evidence_error_code(evidence),
            error_log_id=None,
            verified_at=(
                now if evidence.status is ValidationStatus.VERIFIED else None
            ),
            created_at=now,
        )
        saved.append(
            transaction.ai.validation_runs.add(transaction.session, row)
        )
    return tuple(saved)


def _evidence_error_code(evidence: ProviderStageEvidence) -> str | None:
    category = evidence.error_category
    if category is None:
        return None
    mapping = {
        ProviderFailureCategory.AUTHENTICATION: ErrorCode.AI_PROVIDER_AUTH_FAILED,
        ProviderFailureCategory.RATE_LIMIT: ErrorCode.AI_PROVIDER_RATE_LIMITED,
        ProviderFailureCategory.TIMEOUT: ErrorCode.AI_PROVIDER_TIMEOUT,
        ProviderFailureCategory.INVALID_RESPONSE: ErrorCode.AI_PROVIDER_RESPONSE_INVALID,
        ProviderFailureCategory.CONTENT_REJECTED: ErrorCode.AI_CONTENT_REJECTED,
        ProviderFailureCategory.CANCELLED: ErrorCode.TASK_NOT_CANCELLABLE,
    }
    return mapping.get(category, ErrorCode.PROVIDER_CONNECTION_FAILED).value


__all__ = ["ValidationEvidenceEntry", "save_validation_entries"]
