import type { RuntimeClientResult } from "@/types/runtime/common";
import type {
  ExecutionEnvironmentAcceptedDto,
  ExecutionEnvironmentCreateInput,
  ExecutionEnvironmentDto,
  ExecutionEnvironmentListDto,
  ExecutionEnvironmentRetryAcceptedDto
} from "@/types/runtime/execution-environments";

import {
  accountRequestScopeKey,
  assertRuntimeAccountScope,
  assertStableResourceId,
  requestRuntimeV1,
  type RuntimeCallOptions,
  type RuntimeIdempotentOptions
} from "./core";

export function listExecutionEnvironments(
  accountId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ExecutionEnvironmentListDto>> {
  return requestRuntimeV1<ExecutionEnvironmentListDto>(environmentPath(accountId), {
    ...options,
    scopeKey: accountRequestScopeKey(accountId),
    validateData: (data) => {
      for (const environment of data.items) {
        validateEnvironment(accountId, environment);
      }
    }
  });
}

export function createExecutionEnvironment(
  accountId: string,
  input: ExecutionEnvironmentCreateInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<ExecutionEnvironmentAcceptedDto>> {
  if (!/^wr_[0-9a-f]{32}$/.test(input.rootRef)) {
    throw new Error("工作目录引用格式无效，请重新选择目录。");
  }
  return requestRuntimeV1<ExecutionEnvironmentAcceptedDto>(environmentPath(accountId), {
    ...options,
    body: input,
    method: "POST",
    scopeKey: accountRequestScopeKey(accountId),
    validateData: (data) => {
      assertStableResourceId(data.environmentId, "environmentId");
      assertStableResourceId(data.taskId, "taskId");
    }
  });
}

export function getExecutionEnvironment(
  accountId: string,
  environmentId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ExecutionEnvironmentDto>> {
  assertStableResourceId(environmentId, "environment_id");
  return requestRuntimeV1<ExecutionEnvironmentDto>(
    `${environmentPath(accountId)}/${encodeURIComponent(environmentId)}`,
    {
      ...options,
      scopeKey: accountRequestScopeKey(accountId),
      validateData: (data) => validateEnvironment(accountId, data)
    }
  );
}

export function retryExecutionEnvironment(
  accountId: string,
  environmentId: string,
  revision: number,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<ExecutionEnvironmentRetryAcceptedDto>> {
  assertStableResourceId(environmentId, "environment_id");
  return requestRuntimeV1<ExecutionEnvironmentRetryAcceptedDto>(
    `${environmentPath(accountId)}/${encodeURIComponent(environmentId)}/retry`,
    {
      ...options,
      method: "POST",
      expectedRevision: revision,
      scopeKey: accountRequestScopeKey(accountId),
      validateData: (data) => {
        assertStableResourceId(data.environmentId, "environmentId");
        assertStableResourceId(data.taskId, "taskId");
        assertStableResourceId(data.retryOfTaskId, "retryOfTaskId");
      }
    }
  );
}

function environmentPath(accountId: string): string {
  assertStableResourceId(accountId, "account_id");
  return `/api/v1/accounts/${encodeURIComponent(accountId)}/execution-environments`;
}

function validateEnvironment(
  accountId: string,
  environment: ExecutionEnvironmentDto
): void {
  assertStableResourceId(environment.id, "environment.id");
  assertRuntimeAccountScope(accountId, environment.accountId, "environment.accountId");
  assertStableResourceId(environment.workspace.id, "environment.workspace.id");
  assertStableResourceId(environment.browser.id, "environment.browser.id");
  if (
    !Number.isInteger(environment.revision)
    || environment.revision < 1
    || !Number.isInteger(environment.eligibility.evidenceRevision)
    || environment.eligibility.evidenceRevision < 1
  ) {
    throw new Error("Runtime 返回的执行环境修订号无效。");
  }
}
