import type {
  AIExecutionAcceptedDto,
  AIExecutionCreateInput,
  AIExecutionDetailDto,
  AIExecutionEvidenceDto,
  AIExecutionListQuery,
  AIExecutionOutputDto,
  AIExecutionPageDto,
  AIExecutionPreflightDto,
  AIExecutionPreflightInput
} from "@/types/runtime/ai-executions";
import type { RuntimeClientResult } from "@/types/runtime/common";

import {
  accountRequestScopeKey,
  assertRuntimeAccountScope,
  assertStableResourceId,
  requestRuntimeV1,
  RuntimeError,
  type RuntimeCallOptions,
  type RuntimeIdempotentOptions,
  type RuntimeRevisionIdempotentOptions,
  type RuntimeRevisionOptions
} from "./core";

type AccountOptions = RuntimeCallOptions
  & Partial<RuntimeIdempotentOptions>
  & Partial<RuntimeRevisionOptions>;

export function preflightAIExecution(
  accountId: string,
  input: AIExecutionPreflightInput,
  options: RuntimeRevisionOptions
): Promise<RuntimeClientResult<AIExecutionPreflightDto>> {
  return requestRuntimeV1(
    `${accountPath(accountId)}/preflight`,
    scopedOptions(accountId, options, validatePreflight(accountId), {
      body: input,
      method: "POST"
    })
  );
}

export function createAIExecution(
  accountId: string,
  input: AIExecutionCreateInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<AIExecutionAcceptedDto>> {
  return requestRuntimeV1(
    accountPath(accountId),
    scopedOptions(accountId, options, validateAccepted(accountId), {
      body: input,
      method: "POST"
    })
  );
}

export function listAIExecutions(
  accountId: string,
  query: AIExecutionListQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<AIExecutionPageDto>> {
  const params = new URLSearchParams();
  query.status?.forEach((value) => params.append("status", value));
  if (query.capabilityKey) params.set("capabilityKey", query.capabilityKey);
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  const suffix = params.size ? `?${params.toString()}` : "";
  return requestRuntimeV1(
    `${accountPath(accountId)}${suffix}`,
    scopedOptions(accountId, options, (data: AIExecutionPageDto) => {
      data.items.forEach(validateSummary(accountId));
    })
  );
}

export function getAIExecution(
  accountId: string,
  executionId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<AIExecutionDetailDto>> {
  assertStableResourceId(executionId, "execution_id");
  return requestRuntimeV1(
    `${accountPath(accountId)}/${encodeURIComponent(executionId)}`,
    scopedOptions(accountId, options, validateDetail(accountId, executionId))
  );
}

export function cancelAIExecution(
  accountId: string,
  executionId: string,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<AIExecutionDetailDto>> {
  assertStableResourceId(executionId, "execution_id");
  return requestRuntimeV1(
    `${accountPath(accountId)}/${encodeURIComponent(executionId)}/cancel`,
    scopedOptions(accountId, options, validateDetail(accountId, executionId), {
      method: "POST"
    })
  );
}

export function retryAIExecution(
  accountId: string,
  executionId: string,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<AIExecutionAcceptedDto>> {
  assertStableResourceId(executionId, "execution_id");
  return requestRuntimeV1(
    `${accountPath(accountId)}/${encodeURIComponent(executionId)}/retry`,
    scopedOptions(accountId, options, validateAccepted(accountId), {
      body: { mode: "same_snapshot" },
      method: "POST"
    })
  );
}

export function getAIExecutionOutput(
  accountId: string,
  executionId: string,
  outputId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<AIExecutionOutputDto>> {
  assertStableResourceId(executionId, "execution_id");
  assertStableResourceId(outputId, "output_id");
  return requestRuntimeV1(
    `${accountPath(accountId)}/${encodeURIComponent(executionId)}/outputs/${encodeURIComponent(outputId)}`,
    scopedOptions(accountId, options, (data: AIExecutionOutputDto) => {
      if (data.executionId !== executionId) throw invalidResponse();
      assertStableResourceId(data.id, "output.id");
      assertHash(data.contentHash, "output.contentHash");
      if (typeof data.content !== "string") throw invalidResponse();
    })
  );
}

export function getAIExecutionEvidence(
  accountId: string,
  executionId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<AIExecutionEvidenceDto>> {
  assertStableResourceId(executionId, "execution_id");
  return requestRuntimeV1(
    `${accountPath(accountId)}/${encodeURIComponent(executionId)}/evidence`,
    scopedOptions(accountId, options, (data: AIExecutionEvidenceDto) => {
      assertRuntimeAccountScope(accountId, data.accountId, "evidence.accountId");
      if (data.executionId !== executionId) throw invalidResponse();
      assertHash(data.snapshotHash, "evidence.snapshotHash");
      if (data.provider) {
        assertHash(data.provider.providerRefHash, "evidence.provider.providerRefHash");
        assertHash(data.provider.modelIdHash, "evidence.provider.modelIdHash");
        assertHash(data.provider.validationRunHash, "evidence.provider.validationRunHash");
      }
      if (data.responseIdHash) {
        assertHash(data.responseIdHash, "evidence.responseIdHash");
      }
      if (typeof data.usageReported !== "boolean") throw invalidResponse();
    })
  );
}

function accountPath(accountId: string): string {
  assertStableResourceId(accountId, "account_id");
  return `/api/v1/accounts/${encodeURIComponent(accountId)}/ai-executions`;
}

function scopedOptions<T>(
  accountId: string,
  options: AccountOptions,
  validateData: (data: T) => void,
  request: { body?: unknown; method?: "GET" | "POST" } = {}
) {
  const scopeKey = accountRequestScopeKey(accountId);
  if (options.scopeKey && options.scopeKey !== scopeKey) {
    throw new RuntimeError("账号请求范围与目标账号不一致。", {
      errorCode: "ACCOUNT_SCOPE_MISMATCH",
      status: 403
    });
  }
  return { ...options, ...request, scopeKey, validateData };
}

function validatePreflight(accountId: string) {
  return (data: AIExecutionPreflightDto): void => {
    assertRuntimeAccountScope(accountId, data.accountId, "preflight.accountId");
    assertHash(data.snapshotPreviewHash, "preflight.snapshotPreviewHash");
    if (!Number.isInteger(data.candidateCount) || data.candidateCount < 0) {
      throw invalidResponse();
    }
  };
}

function validateAccepted(accountId: string) {
  return (data: AIExecutionAcceptedDto): void => {
    assertRuntimeAccountScope(accountId, data.accountId, "execution.accountId");
    assertStableResourceId(data.executionId, "execution.id");
    assertStableResourceId(data.taskId, "execution.taskId");
    assertHash(data.snapshotHash, "execution.snapshotHash");
  };
}

function validateSummary(accountId: string) {
  return (data: AIExecutionDetailDto | AIExecutionPageDto["items"][number]): void => {
    assertRuntimeAccountScope(accountId, data.accountId, "execution.accountId");
    assertStableResourceId(data.id, "execution.id");
    assertStableResourceId(data.taskId, "execution.taskId");
    assertHash(data.snapshotHash, "execution.snapshotHash");
  };
}

function validateDetail(accountId: string, executionId: string) {
  return (data: AIExecutionDetailDto): void => {
    validateSummary(accountId)(data);
    if (data.id !== executionId || data.progress < 0 || data.progress > 1) {
      throw invalidResponse();
    }
    data.outputs.forEach((output) => {
      assertStableResourceId(output.id, "output.id");
      assertHash(output.contentHash, "output.contentHash");
    });
  };
}

function assertHash(value: string, field: string): void {
  if (/^[0-9a-f]{64}$/.test(value)) return;
  throw new RuntimeError("Runtime 返回的 AI 执行摘要无效。", {
    errorCode: "INTERNAL_ERROR",
    fieldErrors: [{ field, code: "invalid_hash", message: "必须为 SHA-256 摘要" }],
    status: 500
  });
}

function invalidResponse(): RuntimeError {
  return new RuntimeError("Runtime 返回的 AI 执行数据无效。", {
    errorCode: "INTERNAL_ERROR",
    status: 500
  });
}
