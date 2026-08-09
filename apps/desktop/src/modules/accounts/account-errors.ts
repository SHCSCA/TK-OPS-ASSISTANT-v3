import { RuntimeError } from "@/app/runtime-client/core";

import type { AccountUiError } from "./account-management-types";

export function toAccountUiError(
  error: unknown,
  fallback: string
): AccountUiError {
  if (error instanceof RuntimeError) {
    return {
      message: error.message || fallback,
      errorCode: error.errorCode,
      logId: error.logId,
      requestId: error.requestId,
      retryable:
        error.status >= 500 ||
        error.status === 0 ||
        error.errorCode === "REVISION_CONFLICT"
    };
  }
  return {
    message: fallback,
    errorCode: null,
    logId: null,
    requestId: null,
    retryable: true
  };
}

export function createOperationKey(operation: string, accountId?: string): string {
  const suffix =
    globalThis.crypto?.randomUUID?.() ??
    `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  return `${operation}:${accountId ?? "system"}:${suffix}`.slice(0, 128);
}
