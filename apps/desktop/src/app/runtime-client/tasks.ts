import type { RuntimeClientResult } from "@/types/runtime/common";
import type {
  RuntimeTaskDto,
  RuntimeTaskListDto
} from "@/types/runtime/tasks";

import {
  accountRequestScopeKey,
  assertRuntimeAccountScope,
  assertStableResourceId,
  requestRuntimeV1,
  RuntimeError,
  type RuntimeCallOptions,
  type RuntimeIdempotentOptions
} from "./core";

export function getSystemTask(
  taskId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<RuntimeTaskDto>> {
  return requestRuntimeV1<RuntimeTaskDto>(
    `/api/v1/system/tasks/${encodeTaskId(taskId)}`,
    {
      ...options,
      validateData: validateSystemTask
    }
  );
}

export function listSystemTasks(
  limit = 50,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<RuntimeTaskListDto>> {
  return requestRuntimeV1<RuntimeTaskListDto>(
    `/api/v1/system/tasks?limit=${validateTaskLimit(limit)}`,
    {
      ...options,
      validateData: (data) => data.items.forEach(validateSystemTask)
    }
  );
}

export function cancelSystemTask(
  taskId: string,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<RuntimeTaskDto>> {
  return requestRuntimeV1<RuntimeTaskDto>(
    `/api/v1/system/tasks/${encodeTaskId(taskId)}/cancel`,
    {
      ...options,
      method: "POST",
      validateData: validateSystemTask
    }
  );
}

export function getAccountTask(
  accountId: string,
  taskId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<RuntimeTaskDto>> {
  return requestRuntimeV1<RuntimeTaskDto>(
    accountTaskPath(accountId, taskId),
    {
      ...options,
      scopeKey: accountRequestScopeKey(accountId),
      validateData: (data) => validateAccountTask(accountId, data)
    }
  );
}

export function listAccountTasks(
  accountId: string,
  limit = 50,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<RuntimeTaskListDto>> {
  assertStableResourceId(accountId, "account_id");
  return requestRuntimeV1<RuntimeTaskListDto>(
    `/api/v1/accounts/${encodeURIComponent(accountId)}/tasks?limit=${validateTaskLimit(limit)}`,
    {
      ...options,
      scopeKey: accountRequestScopeKey(accountId),
      validateData: (data) => {
        for (const task of data.items) validateAccountTask(accountId, task);
      }
    }
  );
}

export function cancelAccountTask(
  accountId: string,
  taskId: string,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<RuntimeTaskDto>> {
  return requestRuntimeV1<RuntimeTaskDto>(
    `${accountTaskPath(accountId, taskId)}/cancel`,
    {
      ...options,
      method: "POST",
      scopeKey: accountRequestScopeKey(accountId),
      validateData: (data) => validateAccountTask(accountId, data)
    }
  );
}

function accountTaskPath(accountId: string, taskId: string): string {
  assertStableResourceId(accountId, "account_id");
  return `/api/v1/accounts/${encodeURIComponent(accountId)}/tasks/${encodeTaskId(taskId)}`;
}

function encodeTaskId(taskId: string): string {
  assertStableResourceId(taskId, "task_id");
  return encodeURIComponent(taskId);
}

function validateSystemTask(task: RuntimeTaskDto): void {
  validateTask(task);
  if (task.scope !== "system" || task.accountId !== null) {
    throw invalidTaskResponse();
  }
}

function validateAccountTask(
  accountId: string,
  task: RuntimeTaskDto
): void {
  validateTask(task);
  if (task.scope !== "account") {
    throw invalidTaskResponse();
  }
  assertRuntimeAccountScope(
    accountId,
    task.accountId ?? "",
    "task.accountId"
  );
}

function validateTask(task: RuntimeTaskDto): void {
  assertStableResourceId(task.taskId, "task.taskId");
  if (
    !Number.isFinite(task.progress)
    || task.progress < 0
    || task.progress > 1
    || !Number.isInteger(task.revision)
    || task.revision < 1
  ) {
    throw invalidTaskResponse();
  }
}

function invalidTaskResponse(): RuntimeError {
  return new RuntimeError("Runtime 返回的任务状态无效。", {
    errorCode: "INTERNAL_ERROR",
    status: 500
  });
}

function validateTaskLimit(limit: number): number {
  if (!Number.isInteger(limit) || limit < 1 || limit > 200) {
    throw new RuntimeError("任务列表条数必须位于 1 到 200 之间。", {
      errorCode: "REQUEST_VALIDATION_FAILED",
      status: 422
    });
  }
  return limit;
}
