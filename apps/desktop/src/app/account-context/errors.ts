import type {
  AccountContextError,
  AccountSwitchFailureStage
} from "./types";

export class AccountSwitchSupersededError extends Error {
  readonly code = "ACCOUNT_SWITCH_SUPERSEDED";

  constructor() {
    super("账号切换意图已被更新的操作替代。");
    this.name = "AccountSwitchSupersededError";
  }
}

export class AccountScopeMismatchError extends Error {
  readonly code = "ACCOUNT_SCOPE_MISMATCH";

  constructor(expectedAccountId: string, actualAccountId: string) {
    super(`账号响应范围不一致，期望 ${expectedAccountId}，实际 ${actualAccountId}。`);
    this.name = "AccountScopeMismatchError";
  }
}

export class AccountContextDisposedError extends Error {
  readonly code = "ACCOUNT_CONTEXT_DISPOSED";

  constructor() {
    super("账号上下文已释放。");
    this.name = "AccountContextDisposedError";
  }
}

export class InvalidAccountIdentifierError extends Error {
  readonly code = "REQUEST_VALIDATION_FAILED";

  constructor() {
    super("账号 ID 格式无效。");
    this.name = "InvalidAccountIdentifierError";
  }
}

export function isAccountSwitchSuperseded(error: unknown): boolean {
  return (
    error instanceof AccountSwitchSupersededError ||
    readString(error, "code") === "ACCOUNT_SWITCH_SUPERSEDED"
  );
}

export function isAbortLikeError(error: unknown): boolean {
  return (
    isAccountSwitchSuperseded(error) ||
    (error instanceof DOMException && error.name === "AbortError") ||
    readString(error, "name") === "AbortError" ||
    readString(error, "code") === "REQUEST_ABORTED"
  );
}

export function normalizeAccountContextError(
  error: unknown,
  stage: AccountSwitchFailureStage,
  fallbackMessage: string
): AccountContextError {
  const code =
    readString(error, "errorCode") ??
    readString(error, "error_code") ??
    readString(error, "code") ??
    "ACCOUNT_CONTEXT_FAILED";
  const status = readNumber(error, "status");

  return {
    code,
    message: readString(error, "message") ?? fallbackMessage,
    logId: readString(error, "logId") ?? readString(error, "log_id"),
    requestId: readString(error, "requestId") ?? readString(error, "request_id"),
    status,
    retryable: isRetryable(code, status),
    stage,
    details: readUnknown(error, "details")
  };
}

function isRetryable(code: string, status: number | null): boolean {
  if (
    code === "ACCOUNT_ARCHIVED" ||
    code === "ACCOUNT_NOT_FOUND" ||
    code === "ACCOUNT_SCOPE_MISMATCH" ||
    code === "REQUEST_VALIDATION_FAILED"
  ) {
    return false;
  }
  if (
    code === "RUNTIME_NOT_READY" ||
    code === "RUNTIME_UNAVAILABLE" ||
    code === "NETWORK_ERROR" ||
    code === "REQUEST_TIMEOUT" ||
    code === "INTERNAL_ERROR"
  ) {
    return true;
  }
  return (
    status === null ||
    status === 0 ||
    status >= 500 ||
    status === 408 ||
    status === 429
  );
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function readString(value: unknown, key: string): string | null {
  const candidate = asRecord(value)?.[key];
  return typeof candidate === "string" && candidate.length > 0 ? candidate : null;
}

function readNumber(value: unknown, key: string): number | null {
  const candidate = asRecord(value)?.[key];
  return typeof candidate === "number" && Number.isFinite(candidate)
    ? candidate
    : null;
}

function readUnknown(value: unknown, key: string): unknown {
  return asRecord(value)?.[key];
}
