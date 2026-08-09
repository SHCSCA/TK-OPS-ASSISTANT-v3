import { RuntimeError } from "@/app/runtime-client/core";

export type BootstrapUiError = {
  code: string;
  message: string;
  logId: string | null;
  requestId: string | null;
  retryable: boolean;
};

export function createOperationId(prefix: string): string {
  return `${prefix}-${globalThis.crypto.randomUUID()}`;
}

export function toBootstrapUiError(
  error: unknown,
  fallbackMessage: string
): BootstrapUiError {
  if (error instanceof RuntimeError) {
    return {
      code: error.errorCode,
      message: error.message || fallbackMessage,
      logId: error.logId,
      requestId: error.requestId,
      retryable: !error.aborted && error.status !== 403
    };
  }
  return {
    code: "INTERNAL_ERROR",
    message: fallbackMessage,
    logId: null,
    requestId: null,
    retryable: true
  };
}

export function waitForPoll(
  milliseconds: number,
  signal: AbortSignal
): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(signal.reason);
      return;
    }
    const timer = window.setTimeout(resolve, milliseconds);
    signal.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(signal.reason);
      },
      { once: true }
    );
  });
}
