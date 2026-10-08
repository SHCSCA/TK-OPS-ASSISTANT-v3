from __future__ import annotations

from collections.abc import Mapping, Sequence

from domain.models.ai_execution import AIExecution, AIExecutionJob
from domain.models.ai_execution_evidence import (
    AIErrorEvidence,
    AIExecutionOutput,
    AIUsageRecord,
)
from domain.models.ai_execution_snapshot import (
    AIExecutionCandidate,
    AIExecutionSnapshot,
)
from domain.models.runtime_task import RuntimeTask
from services.ai_configuration_v1.json_codec import load_object


def execution_summary(
    execution: AIExecution,
    snapshot: AIExecutionSnapshot,
) -> dict[str, object]:
    return {
        "id": execution.id,
        "accountId": execution.account_id,
        "capabilityKey": execution.capability_key,
        "status": execution.status,
        "completionKind": execution.completion_kind,
        "failureKind": execution.failure_kind,
        "taskId": execution.runtime_task_id,
        "snapshotHash": snapshot.snapshot_hash,
        "costMicros": execution.cost_micros,
        "costStatus": execution.cost_status,
        "outputCount": int(execution.output_count),
        "errorCode": execution.error_code,
        "logId": execution.error_log_id,
        "revision": int(execution.revision),
        "createdAt": execution.created_at,
        "startedAt": execution.started_at,
        "completedAt": execution.completed_at,
        "updatedAt": execution.updated_at,
    }


def execution_detail(
    execution: AIExecution,
    snapshot: AIExecutionSnapshot,
    task: RuntimeTask,
    *,
    candidates: Sequence[AIExecutionCandidate],
    jobs: Sequence[AIExecutionJob],
    usage: Sequence[AIUsageRecord],
    outputs: Sequence[AIExecutionOutput],
    errors: Sequence[AIErrorEvidence],
) -> dict[str, object]:
    error_by_job = {
        item.job_id: item for item in errors if item.job_id is not None
    }
    result = execution_summary(execution, snapshot)
    result.update(
        {
            "retryOfExecutionId": execution.retry_of_execution_id,
            "progress": float(task.progress),
            "cancellable": bool(task.cancellable)
            and execution.status in {"queued", "running", "cancelling"},
            "snapshot": snapshot_summary(snapshot),
            "candidates": [candidate_summary(item) for item in candidates],
            "jobs": [
                job_summary(item, error=error_by_job.get(item.id))
                for item in jobs
            ],
            "usage": [usage_summary(item) for item in usage],
            "outputs": [output_summary(item) for item in outputs],
            "errors": [error_summary(item) for item in errors],
            "availableActions": _available_actions(execution, outputs),
        }
    )
    return result


def snapshot_summary(snapshot: AIExecutionSnapshot) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "snapshotHash": snapshot.snapshot_hash,
        "accountRevision": int(snapshot.account_revision),
        "aiConfigRevision": int(snapshot.ai_config_revision),
        "positioning": {
            "profileId": snapshot.positioning_profile_id,
            "version": snapshot.positioning_version,
            "contentHash": snapshot.positioning_content_hash,
        },
        "knowledge": {
            "snapshotId": snapshot.knowledge_snapshot_id,
            "version": int(snapshot.knowledge_snapshot_version),
            "contentHash": snapshot.knowledge_content_hash,
            "contextManifestHash": snapshot.context_manifest_hash,
        },
        "recipe": {
            "id": snapshot.account_recipe_id,
            "version": int(snapshot.recipe_version),
            "revision": int(snapshot.recipe_revision),
            "contentHash": snapshot.recipe_content_hash,
        },
        "route": {
            "id": snapshot.capability_route_id,
            "revisionId": snapshot.route_revision_id,
            "contentHash": snapshot.route_content_hash,
        },
        "prompt": {
            "profileId": snapshot.prompt_profile_id,
            "version": int(snapshot.prompt_version),
            "revision": int(snapshot.prompt_revision),
            "contentHash": snapshot.prompt_content_hash,
            "renderedHash": snapshot.rendered_prompt_hash,
        },
        "dependencySnapshotId": snapshot.dependency_snapshot_id,
        "inputSchemaHash": snapshot.input_schema_hash,
        "outputSchemaHash": snapshot.output_schema_hash,
        "policy": load_object(snapshot.policy_json, label="AI 执行策略快照"),
        "createdAt": snapshot.created_at,
    }


def candidate_summary(row: AIExecutionCandidate) -> dict[str, object]:
    return {
        "ordinal": int(row.ordinal),
        "providerProfileId": row.provider_profile_id,
        "providerRevisionId": row.provider_revision_id,
        "modelProfileId": row.model_profile_id,
        "modelRevisionId": row.model_revision_id,
        "validationRunId": row.validation_run_id,
        "timeoutMs": int(row.timeout_ms),
        "maxRetries": int(row.max_retries),
    }


def job_summary(
    row: AIExecutionJob,
    *,
    error: AIErrorEvidence | None,
) -> dict[str, object]:
    return {
        "id": row.id,
        "candidateSnapshotId": row.candidate_snapshot_id,
        "attempt": int(row.attempt),
        "fallbackIndex": int(row.fallback_index),
        "retryIndex": int(row.retry_index),
        "status": row.status,
        "completionKind": row.completion_kind,
        "failureKind": row.failure_kind,
        "durationMs": row.duration_ms,
        "errorCode": error.error_code if error is not None else None,
        "logId": error.log_id if error is not None else None,
        "createdAt": row.created_at,
        "startedAt": row.started_at,
        "completedAt": row.completed_at,
    }


def usage_summary(row: AIUsageRecord) -> dict[str, object]:
    return {
        "inputUnits": row.input_units,
        "outputUnits": row.output_units,
        "cachedUnits": row.cached_units,
        "totalUnits": row.total_units,
        "costMicros": row.cost_micros,
        "currency": row.currency,
        "costSource": row.cost_source,
        "pricingRevision": row.pricing_revision,
    }


def output_summary(row: AIExecutionOutput) -> dict[str, object]:
    return {
        "id": row.id,
        "kind": row.kind,
        "mimeType": row.mime_type,
        "contentHash": row.content_hash,
        "byteSize": int(row.byte_size),
        "schemaStatus": row.schema_status,
        "safeSummary": load_object(
            row.safe_summary_json,
            label="AI 执行输出摘要",
        ),
        "quarantined": bool(row.quarantined),
        "createdAt": row.created_at,
    }


def error_summary(row: AIErrorEvidence) -> dict[str, object]:
    return {
        "errorCode": row.error_code,
        "stage": row.stage,
        "retryable": bool(row.retryable),
        "safeSummary": row.safe_summary,
        "logId": row.log_id,
    }


def _available_actions(
    execution: AIExecution,
    outputs: Sequence[AIExecutionOutput],
) -> list[str]:
    actions: list[str] = []
    if execution.status in {"queued", "running", "cancelling"}:
        actions.append("cancel")
    if execution.status in {"failed", "completed"}:
        actions.append("retry_same_snapshot")
    if any(not item.quarantined for item in outputs):
        actions.append("view_output")
    return actions


__all__ = [
    "candidate_summary",
    "error_summary",
    "execution_detail",
    "execution_summary",
    "job_summary",
    "output_summary",
    "snapshot_summary",
    "usage_summary",
]
