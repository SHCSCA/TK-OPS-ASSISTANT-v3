import { resolveRuntimeBaseUrl } from "@/app/runtime-endpoint";
import type {
  RuntimeClientResult,
  RuntimeEnvelope,
  RuntimeErrorEnvelope,
  RuntimeErrorShape
} from "@/types/runtime/common";
import { emitRuntimeLog } from "./runtime-logger";
import { RuntimeError } from "./runtime-error";

export { RuntimeError } from "./runtime-error";
export { configureRuntimeClientLogger } from "./runtime-logger";
export type {
  RuntimeClientLogEvent,
  RuntimeClientLogger,
  RuntimeClientLogLevel
} from "./runtime-logger";

const API_V1_PREFIX = "/api/v1/";
const HEADER_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const STABLE_RESOURCE_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1"]);

export type RuntimeConnectionInfo = {
  baseUrl: string;
  generation?: number;
  sessionToken: string;
};

export type RuntimeConnectionProvider = (
) => RuntimeConnectionInfo | Promise<RuntimeConnectionInfo>;

export type RuntimeCallOptions = {
  signal?: AbortSignal;
  scopeKey?: string;
  operationId?: string;
};

export type RuntimeIdempotentOptions = RuntimeCallOptions & {
  idempotencyKey: string;
};

export type RuntimeRevisionOptions = RuntimeCallOptions & {
  expectedRevision: number;
};

export type RuntimeRevisionIdempotentOptions = RuntimeIdempotentOptions & {
  expectedRevision: number;
};

export type RuntimeRequestOptions<T> = RuntimeCallOptions & {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  idempotencyKey?: string;
  expectedRevision?: number;
  validateData?: (data: T) => void;
};

let connectionProvider: RuntimeConnectionProvider | null = null;
const requestScopes = new Map<string, Set<AbortController>>();
const activeRequestControllers = new Set<AbortController>();
let runtimeMutationsPaused = false;

export function configureRuntimeConnectionProvider(
  provider: RuntimeConnectionProvider
): () => void {
  const previousProvider = connectionProvider;
  connectionProvider = provider;
  return () => {
    if (connectionProvider === provider) {
      connectionProvider = previousProvider;
    }
  };
}

export function configureStaticRuntimeConnection(
  connection: RuntimeConnectionInfo
): () => void {
  const snapshot = { ...connection };
  return configureRuntimeConnectionProvider(() => snapshot);
}

export function getRuntimeConnectionInfo(): Promise<RuntimeConnectionInfo> {
  return resolveRuntimeConnection();
}

export function accountRequestScopeKey(accountId: string): string {
  assertStableResourceId(accountId, "account_id");
  return `account:${accountId}`;
}

export function cancelAccountRuntimeRequests(accountId: string): number {
  return cancelRuntimeRequestScope(accountRequestScopeKey(accountId));
}

export function cancelRuntimeRequestScope(scopeKey: string): number {
  const controllers = requestScopes.get(scopeKey);
  if (!controllers) {
    return 0;
  }

  requestScopes.delete(scopeKey);
  const reason = new DOMException("账号工作区请求已取消", "AbortError");
  for (const controller of controllers) {
    controller.abort(reason);
  }
  return controllers.size;
}

export function setRuntimeMutationsPaused(paused: boolean): void {
  runtimeMutationsPaused = paused;
}

export function cancelRuntimeRequestsForConnectionChange(): number {
  const controllers = [...activeRequestControllers];
  const reason = new RuntimeError(
    "Runtime 连接已更新，当前操作已停止，请在恢复后重试。",
    {
      errorCode: "RUNTIME_CONNECTION_CHANGED",
      status: 503
    }
  );
  for (const controller of controllers) {
    controller.abort(reason);
  }
  return controllers.length;
}

export function isRuntimeRequestAborted(error: unknown): boolean {
  return error instanceof RuntimeError && error.aborted;
}

export function assertStableResourceId(value: string, field = "resource_id"): void {
  if (STABLE_RESOURCE_ID_PATTERN.test(value)) {
    return;
  }
  throw new RuntimeError("资源标识格式无效，请刷新后重试。", {
    errorCode: "REQUEST_VALIDATION_FAILED",
    fieldErrors: [
      {
        field,
        code: "invalid_stable_id",
        message: "必须为 1 至 128 位稳定标识"
      }
    ],
    status: 422
  });
}

export function assertRuntimeAccountScope(
  expectedAccountId: string,
  observedAccountId: string,
  resource: string
): void {
  assertStableResourceId(expectedAccountId, "account_id");
  if (observedAccountId === expectedAccountId) {
    return;
  }
  throw new RuntimeError("Runtime 返回了其他账号的数据，已阻止写入当前工作区。", {
    errorCode: "ACCOUNT_SCOPE_MISMATCH",
    fieldErrors: [
      {
        field: resource,
        code: "account_scope_mismatch",
        message: "响应账号与请求账号不一致"
      }
    ],
    status: 403
  });
}

export async function requestRuntimeV1<T>(
  path: string,
  options: RuntimeRequestOptions<T> = {}
): Promise<RuntimeClientResult<T>> {
  const method = options.method ?? "GET";
  const safePath = normalizeV1Path(path);
  validateRequestHeaders(options);
  const requestHandle = createRequestHandle(options.scopeKey, options.signal);

  try {
    if (method !== "GET" && runtimeMutationsPaused) {
      throw new RuntimeError(
        "Runtime 正在恢复连接，已暂停写入；你的草稿不会丢失。",
        {
          errorCode: "RUNTIME_CONNECTION_CHANGED",
          status: 503
        }
      );
    }
    const connection = await resolveRuntimeConnection();
    const url = buildRuntimeUrl(connection.baseUrl, path);
    const headers = buildRuntimeHeaders(connection.sessionToken, options);
    const response = await globalThis.fetch(url, {
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      headers,
      method,
      signal: requestHandle.controller.signal
    });
    const requestId = response.headers.get("X-Request-ID");
    const operationId = response.headers.get("X-Operation-ID") ?? options.operationId ?? null;
    const envelope = await readRuntimeEnvelope<T>(response);

    if (!envelope) {
      throw new RuntimeError("Runtime 返回了无法识别的响应，请稍后重试。", {
        errorCode: "INTERNAL_ERROR",
        operationId,
        path: safePath,
        requestId,
        status: response.status
      });
    }
    if (!response.ok || !envelope.ok) {
      throw toRuntimeError(envelope, {
        operationId,
        path: safePath,
        requestId,
        status: response.status
      });
    }

    options.validateData?.(envelope.data);
    return {
      data: envelope.data,
      meta: envelope.meta ?? null,
      operationId,
      requestId,
      status: response.status
    };
  } catch (error) {
    const runtimeError = normalizeRequestError(
      error,
      safePath,
      options.operationId ?? null,
      requestHandle.controller.signal
    );
    emitRuntimeLog({
      errorCode: runtimeError.errorCode,
      event: runtimeError.aborted ? "runtime.request.aborted" : "runtime.request.failed",
      level: runtimeError.aborted ? "debug" : "error",
      logId: runtimeError.logId,
      operationId: runtimeError.operationId,
      path: safePath,
      requestId: runtimeError.requestId,
      scopeKey: options.scopeKey ?? null,
      status: runtimeError.status
    });
    throw runtimeError;
  } finally {
    requestHandle.dispose();
  }
}

function resolveRuntimeConnection(): Promise<RuntimeConnectionInfo> {
  if (!connectionProvider) {
    return Promise.reject(
      new RuntimeError("本机 Runtime 连接信息尚未就绪，请重新启动 Runtime。", {
        errorCode: "RUNTIME_SESSION_REQUIRED",
        status: 401
      })
    );
  }

  return Promise.resolve(connectionProvider()).then((connection) => {
    validateRuntimeConnection(connection);
    return connection;
  });
}

function validateRuntimeConnection(connection: RuntimeConnectionInfo): void {
  buildRuntimeBaseUrl(connection.baseUrl);
  if (
    !connection.sessionToken
    || connection.sessionToken !== connection.sessionToken.trim()
    || /\s/.test(connection.sessionToken)
  ) {
    throw new RuntimeError("本机 Runtime 会话凭据无效，请重新获取连接信息。", {
      errorCode: "RUNTIME_SESSION_INVALID",
      status: 401
    });
  }
}

function buildRuntimeHeaders<T>(
  sessionToken: string,
  options: RuntimeRequestOptions<T>
): Headers {
  const headers = new Headers({
    Accept: "application/json",
    Authorization: `Bearer ${sessionToken}`
  });
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json; charset=utf-8");
  }
  if (options.operationId) {
    headers.set("X-Operation-ID", options.operationId);
  }
  if (options.idempotencyKey) {
    headers.set("Idempotency-Key", options.idempotencyKey);
  }
  if (options.expectedRevision !== undefined) {
    headers.set("If-Match", `"${options.expectedRevision}"`);
  }
  return headers;
}

function validateRequestHeaders<T>(options: RuntimeRequestOptions<T>): void {
  if (options.operationId) {
    assertHeaderId(options.operationId, "X-Operation-ID");
  }
  if (options.idempotencyKey) {
    assertHeaderId(options.idempotencyKey, "Idempotency-Key");
  }
  if (
    options.expectedRevision !== undefined
    && (!Number.isInteger(options.expectedRevision) || options.expectedRevision < 0)
  ) {
    throw new RuntimeError("资源修订号无效，请重新加载后再试。", {
      errorCode: "REQUEST_VALIDATION_FAILED",
      fieldErrors: [
        {
          field: "If-Match",
          code: "invalid_revision",
          message: "必须为非负整数修订号"
        }
      ],
      status: 422
    });
  }
}

function assertHeaderId(value: string, field: string): void {
  if (HEADER_ID_PATTERN.test(value)) {
    return;
  }
  throw new RuntimeError("请求关联标识格式无效，请重试。", {
    errorCode: "REQUEST_VALIDATION_FAILED",
    fieldErrors: [
      {
        field,
        code: "invalid_header_id",
        message: "必须为 1 至 128 位受控标识"
      }
    ],
    status: 422
  });
}

function normalizeV1Path(path: string): string {
  if (!path.startsWith(API_V1_PREFIX)) {
    throw new RuntimeError("Runtime 客户端拒绝了未版本化接口。", {
      errorCode: "RUNTIME_HOST_INVALID",
      status: 400
    });
  }
  const queryIndex = path.indexOf("?");
  return queryIndex >= 0 ? path.slice(0, queryIndex) : path;
}

function buildRuntimeUrl(baseUrl: string, path: string): string {
  const base = buildRuntimeBaseUrl(baseUrl);
  const url = new URL(path, `${base.origin}/`);
  if (url.origin !== base.origin || !url.pathname.startsWith(API_V1_PREFIX)) {
    throw new RuntimeError("Runtime 请求目标不受信任，请重新启动 Runtime。", {
      errorCode: "RUNTIME_HOST_INVALID",
      status: 400
    });
  }
  return url.toString();
}

function buildRuntimeBaseUrl(value: string): URL {
  let url: URL;
  try {
    url = new URL(value || resolveRuntimeBaseUrl());
  } catch (error) {
    throw new RuntimeError("Runtime 地址无效，请重新启动 Runtime。", {
      cause: error,
      errorCode: "RUNTIME_HOST_INVALID",
      status: 400
    });
  }
  if (
    !["http:", "https:"].includes(url.protocol)
    || !LOOPBACK_HOSTS.has(url.hostname)
    || Boolean(url.username)
    || Boolean(url.password)
  ) {
    throw new RuntimeError("Runtime 地址不是受控本机地址，请重新启动 Runtime。", {
      errorCode: "RUNTIME_HOST_INVALID",
      status: 400
    });
  }
  return url;
}

async function readRuntimeEnvelope<T>(response: Response): Promise<RuntimeEnvelope<T> | null> {
  let raw: unknown;
  try {
    raw = JSON.parse(await response.text());
  } catch {
    return null;
  }
  if (!isRecord(raw)) {
    return null;
  }
  if (raw.ok === true && Object.prototype.hasOwnProperty.call(raw, "data")) {
    return raw as RuntimeEnvelope<T>;
  }
  if (
    raw.ok === false
    && typeof raw.error === "string"
    && typeof raw.error_code === "string"
  ) {
    return raw as RuntimeEnvelope<T>;
  }
  return null;
}

function toRuntimeError<T>(
  envelope: RuntimeEnvelope<T>,
  context: Pick<RuntimeErrorShape, "operationId" | "path" | "requestId" | "status">
): RuntimeError {
  if (envelope.ok) {
    return new RuntimeError("Runtime 请求失败，请稍后重试。", {
      ...context,
      errorCode: "INTERNAL_ERROR"
    });
  }
  const errorEnvelope: RuntimeErrorEnvelope = envelope;
  return new RuntimeError(errorEnvelope.error, {
    ...context,
    errorCode: errorEnvelope.error_code,
    fieldErrors: errorEnvelope.fieldErrors,
    logId: errorEnvelope.log_id ?? null,
    meta: errorEnvelope.meta ?? null
  });
}

function normalizeRequestError(
  error: unknown,
  path: string,
  operationId: string | null,
  signal: AbortSignal
): RuntimeError {
  if (error instanceof RuntimeError) {
    return error;
  }
  if (signal.reason instanceof RuntimeError) {
    return signal.reason;
  }
  if (signal.aborted || isAbortLikeError(error)) {
    return new RuntimeError("请求已取消。", {
      aborted: true,
      cause: error,
      errorCode: "REQUEST_ABORTED",
      operationId,
      path,
      status: 0
    });
  }
  return new RuntimeError("无法连接本机 Runtime，请确认服务已启动后重试。", {
    cause: error,
    errorCode: "RUNTIME_UNAVAILABLE",
    operationId,
    path,
    status: 0
  });
}

function isAbortLikeError(error: unknown): boolean {
  return (
    error instanceof DOMException
    && error.name === "AbortError"
  );
}

function createRequestHandle(
  scopeKey: string | undefined,
  externalSignal: AbortSignal | undefined
): {
  controller: AbortController;
  dispose: () => void;
} {
  const controller = new AbortController();
  const abortFromExternal = () => controller.abort(externalSignal?.reason);

  if (externalSignal?.aborted) {
    abortFromExternal();
  } else {
    externalSignal?.addEventListener("abort", abortFromExternal, { once: true });
  }

  if (scopeKey) {
    const controllers = requestScopes.get(scopeKey) ?? new Set<AbortController>();
    controllers.add(controller);
    requestScopes.set(scopeKey, controllers);
  }
  activeRequestControllers.add(controller);

  return {
    controller,
    dispose: () => {
      externalSignal?.removeEventListener("abort", abortFromExternal);
      activeRequestControllers.delete(controller);
      if (!scopeKey) {
        return;
      }
      const controllers = requestScopes.get(scopeKey);
      controllers?.delete(controller);
      if (controllers?.size === 0) {
        requestScopes.delete(scopeKey);
      }
    }
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
