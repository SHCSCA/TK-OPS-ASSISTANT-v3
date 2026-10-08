from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from schemas.v1.ai_common import (
    AIConfigurationDto,
    AIConfigurationInput,
    BoundedKey,
    ContentHash,
    JsonObject,
    PositiveRevision,
    StableId,
)

ExecutionStatus = Literal["queued", "running", "cancelling", "failed", "completed"]


class AIExecutionPolicyInput(AIConfigurationInput):
    timeoutMs: Annotated[int, Field(ge=1_000, le=86_400_000)] | None = None
    allowFallback: bool | None = None
    maxRetries: Annotated[int, Field(ge=0, le=3)] | None = None
    maxCostMicros: Annotated[int, Field(ge=0, le=10**12)] | None = None
    currency: Annotated[str, Field(min_length=1, max_length=16)] | None = None


class AIExecutionInputSummary(AIConfigurationInput):
    estimatedInputUnits: Annotated[int, Field(ge=0, le=10_000_000)]


class AIExecutionPreflightInput(AIConfigurationInput):
    capabilityKey: BoundedKey
    knowledgeSnapshotId: StableId
    recipeVersionId: StableId
    inputSummary: AIExecutionInputSummary
    executionPolicy: AIExecutionPolicyInput


class AIExecutionCreateInput(AIConfigurationInput):
    capabilityKey: BoundedKey
    knowledgeSnapshotId: StableId
    recipeVersionId: StableId
    input: JsonObject
    executionPolicy: AIExecutionPolicyInput


class AIExecutionRetryInput(AIConfigurationInput):
    mode: Literal["same_snapshot"]


class AIExecutionCostEstimateDto(AIConfigurationDto):
    currency: str
    minimumMicros: int | None
    maximumMicros: int | None
    budgetLimitMicros: int


class AIExecutionPreflightDto(AIConfigurationDto):
    accountId: StableId
    capabilityKey: BoundedKey
    ready: bool
    candidateCount: Annotated[int, Field(ge=0)]
    blockingIssues: list[JsonObject]
    repairActions: list[JsonObject]
    costEstimate: AIExecutionCostEstimateDto
    snapshotPreviewHash: ContentHash


class AIExecutionAcceptedDto(AIConfigurationDto):
    executionId: StableId
    taskId: StableId
    accountId: StableId
    capabilityKey: BoundedKey
    status: ExecutionStatus
    snapshotHash: ContentHash
    revision: PositiveRevision
    createdAt: str


class AIExecutionCandidateDto(AIConfigurationDto):
    ordinal: Annotated[int, Field(ge=0)]
    providerProfileId: StableId
    providerRevisionId: StableId
    modelProfileId: StableId
    modelRevisionId: StableId
    validationRunId: StableId
    timeoutMs: Annotated[int, Field(ge=1)]
    maxRetries: Annotated[int, Field(ge=0)]


class AIExecutionJobDto(AIConfigurationDto):
    id: StableId
    candidateSnapshotId: StableId
    attempt: Annotated[int, Field(ge=1)]
    fallbackIndex: Annotated[int, Field(ge=0)]
    retryIndex: Annotated[int, Field(ge=0)]
    status: ExecutionStatus
    completionKind: Literal["succeeded", "cancelled"] | None
    failureKind: Literal[
        "error",
        "timed_out",
        "restart_interrupted",
        "result_unknown",
    ] | None
    durationMs: Annotated[int, Field(ge=0)] | None
    errorCode: str | None
    logId: str | None
    createdAt: str
    startedAt: str | None
    completedAt: str | None


class AIExecutionUsageDto(AIConfigurationDto):
    inputUnits: int | None
    outputUnits: int | None
    cachedUnits: int | None
    totalUnits: int | None
    costMicros: int | None
    currency: str
    costSource: Literal["reported", "estimated", "unavailable"]
    pricingRevision: int | None


class AIExecutionOutputSummaryDto(AIConfigurationDto):
    id: StableId
    kind: str
    mimeType: str
    contentHash: ContentHash
    byteSize: Annotated[int, Field(ge=0)]
    schemaStatus: str
    safeSummary: JsonObject
    quarantined: bool
    createdAt: str


class AIExecutionErrorDto(AIConfigurationDto):
    errorCode: str
    stage: str
    retryable: bool
    safeSummary: str
    logId: StableId


class AIExecutionSummaryDto(AIConfigurationDto):
    id: StableId
    accountId: StableId
    capabilityKey: BoundedKey
    status: ExecutionStatus
    completionKind: Literal["succeeded", "cancelled"] | None
    failureKind: Literal[
        "error",
        "timed_out",
        "restart_interrupted",
        "result_unknown",
    ] | None
    taskId: StableId
    snapshotHash: ContentHash
    costMicros: int | None
    costStatus: Literal["reported", "estimated", "unavailable"]
    outputCount: Annotated[int, Field(ge=0)]
    errorCode: str | None
    logId: str | None
    revision: PositiveRevision
    createdAt: str
    startedAt: str | None
    completedAt: str | None
    updatedAt: str


class AIExecutionPageDto(AIConfigurationDto):
    items: list[AIExecutionSummaryDto]
    totalKnown: int | None


class AIExecutionDetailDto(AIExecutionSummaryDto):
    retryOfExecutionId: StableId | None
    progress: Annotated[float, Field(ge=0, le=1)]
    cancellable: bool
    snapshot: JsonObject
    candidates: list[AIExecutionCandidateDto]
    jobs: list[AIExecutionJobDto]
    usage: list[AIExecutionUsageDto]
    outputs: list[AIExecutionOutputSummaryDto]
    errors: list[AIExecutionErrorDto]
    availableActions: list[Literal["cancel", "retry_same_snapshot", "view_output"]]


class AIExecutionOutputDto(AIExecutionOutputSummaryDto):
    executionId: StableId
    content: str


class AIExecutionEvidenceProviderDto(AIConfigurationDto):
    adapterType: Literal["openai_compatible"]
    providerRefHash: ContentHash
    modelIdHash: ContentHash
    validationRunHash: ContentHash
    validationStage: Literal["real_small_call"]
    validationStatus: Literal["verified"]


class AIExecutionEvidenceDto(AIConfigurationDto):
    executionId: StableId
    accountId: StableId
    capabilityKey: BoundedKey
    finalStatus: Literal[
        "queued",
        "running",
        "cancelling",
        "failed",
        "succeeded",
        "cancelled",
    ]
    snapshotHash: ContentHash
    provider: AIExecutionEvidenceProviderDto | None
    responseIdHash: ContentHash | None
    durationMs: Annotated[int, Field(ge=0)] | None
    usageReported: bool
    jobs: list[AIExecutionJobDto]
    usage: list[AIExecutionUsageDto]
    outputs: list[AIExecutionOutputSummaryDto]
    errors: list[AIExecutionErrorDto]


__all__ = [
    "AIExecutionAcceptedDto",
    "AIExecutionCreateInput",
    "AIExecutionDetailDto",
    "AIExecutionEvidenceDto",
    "AIExecutionEvidenceProviderDto",
    "AIExecutionOutputDto",
    "AIExecutionPageDto",
    "AIExecutionPreflightDto",
    "AIExecutionPreflightInput",
    "AIExecutionRetryInput",
]
