import { resolveRuntimeBaseUrl } from "@/app/runtime-endpoint";

import {
  cancelRuntimeRequestsForConnectionChange,
  configureRuntimeConnectionProvider,
  RuntimeError,
  setRuntimeMutationsPaused,
  type RuntimeConnectionInfo
} from "./core";

type RuntimeConnectionCommandResult = {
  baseUrl: string;
  generation: number;
  sessionToken: string;
};

type SupervisorCommandErrorShape = {
  errorCode: string;
  logId?: string | null;
  message: string;
};

export type RuntimeSupervisorStatus = {
  status: "starting" | "ready" | "offline" | "failed" | "stopping";
  phase: string;
  baseUrl: string | null;
  errorCode: string | null;
  generation: number;
  logId: string | null;
  restartAttempt: number;
  maxRestartAttempts: number;
  canRestart: boolean;
  updatedAtEpochMs: number;
};

export type RuntimeSupervisorDiagnostics = {
  artifactBuildId: string | null;
  artifactSha256: string | null;
  desktopVersion: string;
  generatedAtEpochMs: number;
  generation: number;
  lastExitCode: number | null;
  maxRestartAttempts: number;
  phase: string;
  recentLogs: Array<{
    errorCode: string | null;
    level: string;
    logId: string;
    operation: string;
    timestampEpochMs: number;
  }>;
  restartAttempt: number;
  status: string;
};

export type RuntimeSupervisorDiagnosticExport = {
  fileName: string;
  path: string;
};

type ConnectionLifecycleListener = () => void | Promise<void>;

let connectionPromise: Promise<RuntimeConnectionInfo> | null = null;
let cachedConnection: RuntimeConnectionInfo | null = null;
let monitorPromise: Promise<void> | null = null;
let stopStatusListener: (() => void) | null = null;
let observedGeneration: number | null = null;
let readyGeneration: number | null = null;
const connectionChangedListeners = new Set<ConnectionLifecycleListener>();
const connectionRecoveredListeners = new Set<ConnectionLifecycleListener>();
const CONNECTION_POLL_INTERVAL_MS = 250;
const CONNECTION_STARTUP_TIMEOUT_MS = 90_000;

export function installDesktopRuntimeConnectionProvider(): void {
  configureRuntimeConnectionProvider(resolveDesktopRuntimeConnection);
}

export function invalidateDesktopRuntimeConnection(): void {
  connectionPromise = null;
  cachedConnection = null;
}

export function onDesktopRuntimeConnectionChanged(
  listener: ConnectionLifecycleListener
): () => void {
  connectionChangedListeners.add(listener);
  return () => connectionChangedListeners.delete(listener);
}

export function onDesktopRuntimeConnectionRecovered(
  listener: ConnectionLifecycleListener
): () => void {
  connectionRecoveredListeners.add(listener);
  return () => connectionRecoveredListeners.delete(listener);
}

export function startDesktopRuntimeSupervisorMonitoring(): Promise<void> {
  if (!isTauriRuntime()) return Promise.resolve();
  if (!monitorPromise) {
    monitorPromise = installSupervisorStatusListener().catch((error) => {
      monitorPromise = null;
      throw error;
    });
  }
  return monitorPromise;
}

export function stopDesktopRuntimeSupervisorMonitoring(): void {
  stopStatusListener?.();
  stopStatusListener = null;
  monitorPromise = null;
  observedGeneration = null;
  readyGeneration = null;
  setRuntimeMutationsPaused(false);
}

export function isDesktopRuntimeSupervisorAvailable(): boolean {
  return isTauriRuntime();
}

export async function getDesktopRuntimeSupervisorStatus(
): Promise<RuntimeSupervisorStatus> {
  return invokeSupervisorCommand<RuntimeSupervisorStatus>(
    "get_runtime_supervisor_status",
    "无法读取本机 Runtime 状态，请重新启动桌面应用。"
  );
}

export async function getDesktopRuntimeSupervisorDiagnostics(
): Promise<RuntimeSupervisorDiagnostics> {
  return invokeSupervisorCommand<RuntimeSupervisorDiagnostics>(
    "get_runtime_supervisor_diagnostics",
    "无法读取 Runtime 脱机诊断，请重新启动桌面应用。"
  );
}

export async function exportDesktopRuntimeSupervisorDiagnostics(
): Promise<RuntimeSupervisorDiagnosticExport> {
  return invokeSupervisorCommand<RuntimeSupervisorDiagnosticExport>(
    "export_runtime_supervisor_diagnostics",
    "无法导出 Runtime 诊断，请检查目录权限后重试。"
  );
}

export async function restartDesktopRuntime(
): Promise<RuntimeSupervisorStatus> {
  signalRuntimeConnectionChanged();
  return invokeSupervisorCommand<RuntimeSupervisorStatus>(
    "restart_runtime",
    "重新启动本机 Runtime 失败，请查看日志后重试。"
  );
}

function resolveDesktopRuntimeConnection(): Promise<RuntimeConnectionInfo> {
  if (!connectionPromise) {
    connectionPromise = loadDesktopRuntimeConnection()
      .then((connection) => {
        if (
          cachedConnection
          && (
            cachedConnection.generation !== connection.generation
            || cachedConnection.sessionToken !== connection.sessionToken
          )
        ) {
          signalRuntimeConnectionChanged();
        }
        cachedConnection = connection;
        return connection;
      })
      .catch((error) => {
        connectionPromise = null;
        throw error;
      });
  }
  return connectionPromise;
}

async function loadDesktopRuntimeConnection(): Promise<RuntimeConnectionInfo> {
  if (isTauriRuntime()) {
    return waitForDesktopRuntimeConnection();
  }

  if (!import.meta.env.DEV) {
    throw new RuntimeError(
      "生产环境不允许使用浏览器开发会话，请启动桌面应用。",
      {
        errorCode: "RUNTIME_SESSION_REQUIRED",
        status: 401
      }
    );
  }

  const developmentToken =
    import.meta.env.VITE_RUNTIME_SESSION_TOKEN?.trim();
  if (developmentToken) {
    return {
      baseUrl: resolveRuntimeBaseUrl(),
      sessionToken: developmentToken
    };
  }

  throw new RuntimeError(
    "本地开发会话尚未启动，请使用受控桌面开发入口重新启动。",
    {
      errorCode: "RUNTIME_SESSION_REQUIRED",
      status: 401
    }
  );
}

async function waitForDesktopRuntimeConnection(
): Promise<RuntimeConnectionInfo> {
  const { invoke } = await import("@tauri-apps/api/core");
  const deadline = Date.now() + CONNECTION_STARTUP_TIMEOUT_MS;
  let lastError: RuntimeError | null = null;
  while (Date.now() < deadline) {
    try {
      const connection = await invoke<RuntimeConnectionCommandResult>(
        "get_runtime_connection"
      );
      return {
        baseUrl: connection.baseUrl,
        generation: connection.generation,
        sessionToken: connection.sessionToken
      };
    } catch (error) {
      lastError = toSupervisorRuntimeError(
        error,
        "无法获取本机 Runtime 会话，请重新启动桌面应用。",
        "RUNTIME_NOT_READY"
      );
      if (lastError.errorCode !== "RUNTIME_NOT_READY") {
        throw lastError;
      }
      await waitForConnectionPoll();
    }
  }
  throw new RuntimeError(
    "本机 Runtime 启动超时，请查看日志后重试。",
    {
      errorCode: "RUNTIME_STARTUP_TIMEOUT",
      logId: lastError?.logId,
      status: 504
    }
  );
}

async function installSupervisorStatusListener(): Promise<void> {
  const { listen } = await import("@tauri-apps/api/event");
  stopStatusListener = await listen<RuntimeSupervisorStatus>(
    "runtime-supervisor://status",
    (event) => {
      void applySupervisorStatus(event.payload).catch((error) => {
        console.error("[runtime-supervisor] 恢复连接失败", error);
      });
    }
  );
  await applySupervisorStatus(await getDesktopRuntimeSupervisorStatus());
}

async function applySupervisorStatus(
  status: RuntimeSupervisorStatus
): Promise<void> {
  if (!Number.isSafeInteger(status.generation) || status.generation < 0) {
    throw new RuntimeError("Runtime Supervisor 世代信息无效。", {
      errorCode: "RUNTIME_SUPERVISOR_STATUS_INVALID",
      status: 503
    });
  }
  const generationChanged =
    observedGeneration !== null
    && observedGeneration !== status.generation;
  observedGeneration = status.generation;

  if (status.status !== "ready") {
    setRuntimeMutationsPaused(true);
    if (generationChanged || readyGeneration !== null) {
      signalRuntimeConnectionChanged();
    }
    return;
  }

  if (readyGeneration === status.generation && cachedConnection) {
    setRuntimeMutationsPaused(false);
    return;
  }

  const recovering = readyGeneration !== null;
  if (generationChanged || recovering) {
    signalRuntimeConnectionChanged();
  }
  const connection = await resolveDesktopRuntimeConnection();
  if (connection.generation !== status.generation) {
    signalRuntimeConnectionChanged();
    throw new RuntimeError("Runtime 连接世代已变化，正在重新握手。", {
      errorCode: "RUNTIME_CONNECTION_CHANGED",
      status: 503
    });
  }
  readyGeneration = status.generation;
  setRuntimeMutationsPaused(false);
  if (recovering) {
    await notifyLifecycleListeners(connectionRecoveredListeners);
  }
}

function signalRuntimeConnectionChanged(): void {
  invalidateDesktopRuntimeConnection();
  setRuntimeMutationsPaused(true);
  cancelRuntimeRequestsForConnectionChange();
  void notifyLifecycleListeners(connectionChangedListeners);
}

async function notifyLifecycleListeners(
  listeners: Set<ConnectionLifecycleListener>
): Promise<void> {
  const results = await Promise.allSettled(
    [...listeners].map((listener) => listener())
  );
  for (const result of results) {
    if (result.status === "rejected") {
      console.error("[runtime-supervisor] 连接生命周期处理失败", result.reason);
    }
  }
}

function waitForConnectionPoll(): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, CONNECTION_POLL_INTERVAL_MS);
  });
}

async function invokeSupervisorCommand<T>(
  command: string,
  fallbackMessage: string
): Promise<T> {
  if (!isTauriRuntime()) {
    throw new RuntimeError(
      "当前为浏览器开发模式，请重新启动本地 Runtime 进程。",
      {
        errorCode: "RUNTIME_SUPERVISOR_UNAVAILABLE",
        status: 409
      }
    );
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<T>(command);
  } catch (error) {
    throw toSupervisorRuntimeError(
      error,
      fallbackMessage,
      "RUNTIME_SUPERVISOR_COMMAND_FAILED"
    );
  }
}

function toSupervisorRuntimeError(
  error: unknown,
  fallbackMessage: string,
  fallbackErrorCode: string
): RuntimeError {
  const supervisorError = readSupervisorCommandError(error);
  if (supervisorError) {
    return new RuntimeError(supervisorError.message, {
      cause: error,
      errorCode: supervisorError.errorCode,
      logId: supervisorError.logId ?? null,
      status: 503
    });
  }
  return new RuntimeError(fallbackMessage, {
    cause: error,
    errorCode: fallbackErrorCode,
    status: 503
  });
}

function readSupervisorCommandError(
  value: unknown
): SupervisorCommandErrorShape | null {
  if (
    typeof value !== "object"
    || value === null
    || Array.isArray(value)
  ) {
    return null;
  }
  const candidate = value as Record<string, unknown>;
  if (
    typeof candidate.message !== "string"
    || candidate.message.trim().length === 0
    || typeof candidate.errorCode !== "string"
    || candidate.errorCode.trim().length === 0
    || (
      candidate.logId !== undefined
      && candidate.logId !== null
      && typeof candidate.logId !== "string"
    )
  ) {
    return null;
  }
  return {
    errorCode: candidate.errorCode,
    logId: candidate.logId as string | null | undefined,
    message: candidate.message
  };
}

function isTauriRuntime(): boolean {
  return (
    typeof window !== "undefined"
    && "__TAURI_INTERNALS__" in window
  );
}
