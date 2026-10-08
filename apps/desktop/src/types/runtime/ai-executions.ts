export type AIExecutionStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "failed"
  | "completed";

export type AIExecutionCompletionKind = "succeeded" | "cancelled" | null;
export type AIExecutionFailureKind =
  | "error"
  | "timed_out"
  | "restart_interrupted"
  | "result_unknown"
  | null;

export type AIExecutionPolicyInput = {
  timeoutMs?: number;
  allowFallback?: boolean;
  maxRetries?: number;
  maxCostMicros?: number;
  currency?: string;
};

export type AIExecutionDependencyIssueDto = {
  code: string;
  severity: "info" | "warning" | "error";
  nodeType: string;
  nodeId: string | null;
  path: string;
  message: string;
  blocking: boolean;
  evidenceRef: string | null;
};

export type AIExecutionRepairActionDto = {
  kind: "navigate" | "edit";
  label: string;
  targetPage: string;
  targetSection: string;
  targetResourceId: string | null;
  requiredAccountId: string | null;
};

export type AIExecutionPreflightInput = {
  capabilityKey: string;
  knowledgeSnapshotId: string;
  recipeVersionId: string;
  inputSummary: { estimatedInputUnits: number };
  executionPolicy: AIExecutionPolicyInput;
};

export type AIExecutionCreateInput = {
  capabilityKey: string;
  knowledgeSnapshotId: string;
  recipeVersionId: string;
  input: Record<string, unknown>;
  executionPolicy: AIExecutionPolicyInput;
};

export type AIExecutionPreflightDto = {
  accountId: string;
  capabilityKey: string;
  ready: boolean;
  candidateCount: number;
  blockingIssues: AIExecutionDependencyIssueDto[];
  repairActions: AIExecutionRepairActionDto[];
  costEstimate: {
    currency: string;
    minimumMicros: number | null;
    maximumMicros: number | null;
    budgetLimitMicros: number;
  };
  snapshotPreviewHash: string;
};

export type AIExecutionAcceptedDto = {
  executionId: string;
  taskId: string;
  accountId: string;
  capabilityKey: string;
  status: AIExecutionStatus;
  snapshotHash: string;
  revision: number;
  createdAt: string;
};

export type AIExecutionSummaryDto = {
  id: string;
  accountId: string;
  capabilityKey: string;
  status: AIExecutionStatus;
  completionKind: AIExecutionCompletionKind;
  failureKind: AIExecutionFailureKind;
  taskId: string;
  snapshotHash: string;
  costMicros: number | null;
  costStatus: "reported" | "estimated" | "unavailable";
  outputCount: number;
  errorCode: string | null;
  logId: string | null;
  revision: number;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  updatedAt: string;
};

export type AIExecutionCandidateDto = {
  ordinal: number;
  providerProfileId: string;
  providerRevisionId: string;
  modelProfileId: string;
  modelRevisionId: string;
  validationRunId: string;
  timeoutMs: number;
  maxRetries: number;
};

export type AIExecutionJobDto = {
  id: string;
  candidateSnapshotId: string;
  attempt: number;
  fallbackIndex: number;
  retryIndex: number;
  status: AIExecutionStatus;
  completionKind: AIExecutionCompletionKind;
  failureKind: AIExecutionFailureKind;
  durationMs: number | null;
  errorCode: string | null;
  logId: string | null;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
};

export type AIExecutionUsageDto = {
  inputUnits: number | null;
  outputUnits: number | null;
  cachedUnits: number | null;
  totalUnits: number | null;
  costMicros: number | null;
  currency: string;
  costSource: "reported" | "estimated" | "unavailable";
  pricingRevision: number | null;
};

export type AIExecutionOutputSummaryDto = {
  id: string;
  kind: string;
  mimeType: string;
  contentHash: string;
  byteSize: number;
  schemaStatus: string;
  safeSummary: Record<string, unknown>;
  quarantined: boolean;
  createdAt: string;
};

export type AIExecutionErrorDto = {
  errorCode: string;
  stage: string;
  retryable: boolean;
  safeSummary: string;
  logId: string;
};

export type AIExecutionDetailDto = AIExecutionSummaryDto & {
  retryOfExecutionId: string | null;
  progress: number;
  cancellable: boolean;
  snapshot: Record<string, unknown>;
  candidates: AIExecutionCandidateDto[];
  jobs: AIExecutionJobDto[];
  usage: AIExecutionUsageDto[];
  outputs: AIExecutionOutputSummaryDto[];
  errors: AIExecutionErrorDto[];
  availableActions: Array<
    "cancel" | "retry_same_snapshot" | "view_output"
  >;
};

export type AIExecutionPageDto = {
  items: AIExecutionSummaryDto[];
  totalKnown: number | null;
};

export type AIExecutionOutputDto = AIExecutionOutputSummaryDto & {
  executionId: string;
  content: string;
};

export type AIExecutionEvidenceDto = {
  executionId: string;
  accountId: string;
  capabilityKey: string;
  finalStatus:
    | "queued"
    | "running"
    | "cancelling"
    | "failed"
    | "succeeded"
    | "cancelled";
  snapshotHash: string;
  provider: {
    adapterType: "openai_compatible";
    providerRefHash: string;
    modelIdHash: string;
    validationRunHash: string;
    validationStage: "real_small_call";
    validationStatus: "verified";
  } | null;
  responseIdHash: string | null;
  durationMs: number | null;
  usageReported: boolean;
  jobs: AIExecutionJobDto[];
  usage: AIExecutionUsageDto[];
  outputs: AIExecutionOutputSummaryDto[];
  errors: AIExecutionErrorDto[];
};

export type AIExecutionListQuery = {
  status?: AIExecutionStatus[];
  capabilityKey?: string;
  cursor?: string;
  limit?: number;
};
