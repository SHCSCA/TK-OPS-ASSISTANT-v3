import {
  cancelAIExecution,
  createAIExecution,
  preflightAIExecution,
  retryAIExecution
} from "@/app/runtime-client/ai-executions";
import type {
  AIExecutionCreateInput,
  AIExecutionPreflightInput
} from "@/types/runtime/ai-executions";
import { createAIOperationKey } from "@/modules/system/ai-config/ai-config-helpers";

export function preflightExecutionOperation(
  accountId: string,
  accountRevision: number,
  input: AIExecutionPreflightInput,
  signal?: AbortSignal
) {
  return preflightAIExecution(accountId, input, {
    expectedRevision: accountRevision,
    signal
  });
}

export function createExecutionOperation(
  accountId: string,
  accountRevision: number,
  input: AIExecutionCreateInput,
  signal?: AbortSignal
) {
  return createAIExecution(accountId, input, {
    expectedRevision: accountRevision,
    idempotencyKey: createAIOperationKey("ai-execution-create", accountId),
    signal
  });
}

export function cancelExecutionOperation(
  accountId: string,
  executionId: string,
  signal?: AbortSignal
) {
  return cancelAIExecution(accountId, executionId, {
    idempotencyKey: createAIOperationKey("ai-execution-cancel", executionId),
    signal
  });
}

export function retryExecutionOperation(
  accountId: string,
  executionId: string,
  signal?: AbortSignal
) {
  return retryAIExecution(accountId, executionId, {
    idempotencyKey: createAIOperationKey("ai-execution-retry", executionId),
    signal
  });
}
