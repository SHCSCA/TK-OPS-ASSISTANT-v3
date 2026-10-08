import { RuntimeError } from "@/app/runtime-client/core";
import { ControlledFileBridgeError } from "@/app/controlled-files/types";
import type { KnowledgeUiError } from "./account-knowledge-types";

export function toKnowledgeUiError(
  error: unknown,
  fallback: string
): KnowledgeUiError {
  if (error instanceof ControlledFileBridgeError) {
    return {
      message: error.message || fallback,
      errorCode: error.errorCode,
      logId: error.logId,
      requestId: null,
      retryable: true
    };
  }
  if (error instanceof RuntimeError) {
    return {
      message: error.message || fallback,
      errorCode: error.errorCode,
      logId: error.logId,
      requestId: error.requestId,
      retryable:
        error.status === 0
        || error.status >= 500
        || error.errorCode === "REVISION_CONFLICT"
    };
  }
  if (error instanceof Error) {
    return {
      message: error.message || fallback,
      errorCode: error.name || null,
      logId: null,
      requestId: null,
      retryable: false
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

export function createKnowledgeOperationKey(
  operation: string,
  accountId: string
): string {
  const suffix =
    globalThis.crypto?.randomUUID?.()
    ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  return `${operation}:${accountId}:${suffix}`.slice(0, 128);
}

export function stableJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

export function parseRulesJson(
  value: string,
  label: string
): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value || "{}");
  } catch (error) {
    throw new Error(`${label}必须是有效 JSON 对象。`, { cause: error });
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label}必须是 JSON 对象。`);
  }
  return parsed as Record<string, unknown>;
}

export function logKnowledgeError(message: string, error: unknown): void {
  console.error(`[定位与知识] ${message}`, error);
}
