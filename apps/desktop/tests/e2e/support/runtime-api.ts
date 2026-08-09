import type { APIRequestContext } from "@playwright/test";

import { readE2eRuntimeState } from "./runtime-state";

type RuntimeMeta = {
  invalidations?: string[];
  revision?: number;
};

export type RuntimeResult<T> = {
  data: T;
  meta: RuntimeMeta;
};

export type RuntimeTask = {
  taskId: string;
  status: "queued" | "running" | "cancelling" | "failed" | "completed";
  completionKind: "succeeded" | "cancelled" | null;
  errorCode: string | null;
  logId: string | null;
};

type RuntimeCallOptions = {
  data?: unknown;
  expectedRevision?: number;
  idempotencyKey?: string;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
};

export async function callRuntime<T>(
  request: APIRequestContext,
  path: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeResult<T>> {
  const state = readE2eRuntimeState();
  const headers: Record<string, string> = {
    Authorization: `Bearer ${state.sessionToken}`
  };
  if (options.expectedRevision !== undefined) {
    headers["If-Match"] = String(options.expectedRevision);
  }
  if (options.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }
  const response = await request.fetch(`${state.runtimeBaseUrl}${path}`, {
    data: options.data,
    headers,
    method: options.method ?? "GET"
  });
  const payload = await response.json() as {
    data?: T;
    error?: string;
    error_code?: string;
    meta?: RuntimeMeta;
    ok?: boolean;
  };
  if (!response.ok() || payload.ok !== true || payload.data === undefined) {
    const code = payload.error_code || `HTTP_${response.status()}`;
    const message = payload.error || "Runtime 未返回成功信封";
    throw new Error(`${path} 调用失败：${code} ${message}`);
  }
  return {
    data: payload.data,
    meta: payload.meta ?? {}
  };
}

export async function waitForRuntimeTask(
  request: APIRequestContext,
  taskId: string,
  accountId?: string
): Promise<RuntimeTask> {
  const scope = accountId
    ? `/api/v1/accounts/${encodeURIComponent(accountId)}`
    : "/api/v1/system";
  for (let attempt = 0; attempt < 240; attempt += 1) {
    const { data } = await callRuntime<RuntimeTask>(
      request,
      `${scope}/tasks/${encodeURIComponent(taskId)}`
    );
    if (data.status === "failed") {
      throw new Error(
        `Runtime 任务失败：${data.errorCode ?? "UNKNOWN"} `
        + `${data.logId ?? "NO_LOG_ID"}`
      );
    }
    if (data.status === "completed") {
      if (data.completionKind !== "succeeded") {
        throw new Error(`Runtime 任务未成功完成：${data.completionKind}`);
      }
      return data;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Runtime 任务等待超时：${taskId}`);
}
