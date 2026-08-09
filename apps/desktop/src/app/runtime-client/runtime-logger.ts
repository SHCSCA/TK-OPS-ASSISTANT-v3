export type RuntimeClientLogLevel =
  | "debug"
  | "info"
  | "warning"
  | "error";

export type RuntimeClientLogEvent = {
  level: RuntimeClientLogLevel;
  event: string;
  errorCode: string | null;
  status: number | null;
  requestId: string | null;
  operationId: string | null;
  logId: string | null;
  path: string | null;
  scopeKey: string | null;
};

export type RuntimeClientLogger = (
  event: RuntimeClientLogEvent
) => void;

let runtimeLogger: RuntimeClientLogger = defaultRuntimeLogger;

export function configureRuntimeClientLogger(
  logger: RuntimeClientLogger
): () => void {
  const previousLogger = runtimeLogger;
  runtimeLogger = logger;
  return () => {
    if (runtimeLogger === logger) {
      runtimeLogger = previousLogger;
    }
  };
}

export function emitRuntimeLog(event: RuntimeClientLogEvent): void {
  try {
    runtimeLogger(event);
  } catch (error) {
    defaultRuntimeLogger({
      ...event,
      errorCode: event.errorCode ?? (
        error instanceof Error
          ? error.name
          : "RUNTIME_LOGGER_FAILED"
      )
    });
  }
}

function defaultRuntimeLogger(event: RuntimeClientLogEvent): void {
  if (event.level === "error") {
    console.error("Runtime 请求异常", event);
  } else if (event.level === "warning") {
    console.warn("Runtime 请求告警", event);
  }
}
