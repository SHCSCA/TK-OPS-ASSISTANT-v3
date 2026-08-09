import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi
} from "vitest";

const invoke = vi.hoisted(() => vi.fn());

vi.mock("@tauri-apps/api/core", () => ({ invoke }));

import {
  exportDesktopRuntimeSupervisorDiagnostics,
  getDesktopRuntimeSupervisorDiagnostics,
  getDesktopRuntimeSupervisorStatus,
  installDesktopRuntimeConnectionProvider,
  invalidateDesktopRuntimeConnection,
  restartDesktopRuntime
} from "@/app/runtime-client/connection";
import { getRuntimeConnectionInfo } from "@/app/runtime-client/core";

describe("P0 Desktop Runtime Supervisor 客户端", () => {
  beforeEach(() => {
    invalidateDesktopRuntimeConnection();
  });

  afterEach(() => {
    invoke.mockReset();
    vi.useRealTimers();
    vi.unstubAllEnvs();
    invalidateDesktopRuntimeConnection();
    Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
  });

  it("Tauri 环境始终通过命令获取连接并忽略开发令牌", async () => {
    vi.stubEnv("VITE_RUNTIME_SESSION_TOKEN", "browser-dev-token");
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {}
    });
    invoke.mockResolvedValue({
      baseUrl: "http://127.0.0.1:18120",
      generation: 1,
      sessionToken: "tauri-session-token"
    });
    installDesktopRuntimeConnectionProvider();

    const connection = await getRuntimeConnectionInfo();

    expect(invoke).toHaveBeenCalledWith("get_runtime_connection");
    expect(connection.sessionToken).toBe("tauri-session-token");
    expect(connection.generation).toBe(1);
  });

  it("Runtime 冷启动期间保持加载并在就绪后自动取得连接", async () => {
    vi.useFakeTimers();
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {}
    });
    invoke
      .mockRejectedValueOnce({
        message: "Runtime 尚未就绪，请稍后重试。",
        errorCode: "RUNTIME_NOT_READY",
        logId: null
      })
      .mockResolvedValueOnce({
        baseUrl: "http://127.0.0.1:18120",
        generation: 1,
        sessionToken: "tauri-session-token"
      });
    installDesktopRuntimeConnectionProvider();

    const pending = getRuntimeConnectionInfo();
    await vi.advanceTimersByTimeAsync(250);

    await expect(pending).resolves.toEqual({
      baseUrl: "http://127.0.0.1:18120",
      generation: 1,
      sessionToken: "tauri-session-token"
    });
    expect(invoke).toHaveBeenNthCalledWith(1, "get_runtime_connection");
    expect(invoke).toHaveBeenNthCalledWith(2, "get_runtime_connection");
  });

  it("Runtime 永久启动错误不进入冷启动轮询", async () => {
    vi.useFakeTimers();
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {}
    });
    invoke.mockRejectedValue({
      message: "Runtime 制品缺失，请重新安装应用。",
      errorCode: "RUNTIME_SIDECAR_RESOURCE_MISSING",
      logId: "log-artifact"
    });
    installDesktopRuntimeConnectionProvider();

    await expect(getRuntimeConnectionInfo()).rejects.toMatchObject({
      errorCode: "RUNTIME_SIDECAR_RESOURCE_MISSING",
      logId: "log-artifact",
      status: 503
    });
    expect(invoke).toHaveBeenCalledTimes(1);
  });

  it("生产浏览器环境拒绝使用注入的开发令牌", async () => {
    vi.stubEnv("DEV", false);
    vi.stubEnv("VITE_RUNTIME_SESSION_TOKEN", "forbidden-token");
    installDesktopRuntimeConnectionProvider();

    await expect(getRuntimeConnectionInfo()).rejects.toMatchObject({
      errorCode: "RUNTIME_SESSION_REQUIRED",
      status: 401
    });
    expect(invoke).not.toHaveBeenCalled();
  });

  it("通过无令牌状态命令读取 Supervisor 证据", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {}
    });
    invoke.mockResolvedValue(supervisorStatus("ready"));

    const status = await getDesktopRuntimeSupervisorStatus();

    expect(invoke).toHaveBeenCalledWith(
      "get_runtime_supervisor_status"
    );
    expect(status.status).toBe("ready");
    expect(status).not.toHaveProperty("sessionToken");
  });

  it("Runtime 不可用前仍可通过 Tauri 命令读取和导出脱机诊断", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {}
    });
    invoke
      .mockResolvedValueOnce({
        artifactBuildId: "build-1",
        artifactSha256: "A".repeat(64),
        desktopVersion: "0.4.7",
        generatedAtEpochMs: 42,
        generation: 2,
        lastExitCode: 1,
        maxRestartAttempts: 3,
        phase: "failed",
        recentLogs: [],
        restartAttempt: 3,
        status: "failed"
      })
      .mockResolvedValueOnce({
        fileName: "tk-ops-diagnostics-42.json",
        path: "C:\\safe\\tk-ops-diagnostics-42.json"
      });

    const diagnostics = await getDesktopRuntimeSupervisorDiagnostics();
    const exported = await exportDesktopRuntimeSupervisorDiagnostics();

    expect(diagnostics).not.toHaveProperty("sessionToken");
    expect(exported.fileName).toBe("tk-ops-diagnostics-42.json");
    expect(invoke).toHaveBeenNthCalledWith(
      1,
      "get_runtime_supervisor_diagnostics"
    );
    expect(invoke).toHaveBeenNthCalledWith(
      2,
      "export_runtime_supervisor_diagnostics"
    );
  });

  it("重启动作只调用受控 Tauri 命令", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {}
    });
    invoke.mockResolvedValue(supervisorStatus("starting"));

    const status = await restartDesktopRuntime();

    expect(invoke).toHaveBeenCalledWith("restart_runtime");
    expect(status.status).toBe("starting");
  });

  it("保留 SupervisorCommandError 的消息、错误码与日志编号", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {}
    });
    invoke.mockRejectedValue({
      message: "Runtime 正在启动，请稍后重试。",
      errorCode: "RUNTIME_RESTART_IN_PROGRESS",
      logId: "log-supervisor-42"
    });

    await expect(restartDesktopRuntime()).rejects.toMatchObject({
      message: "Runtime 正在启动，请稍后重试。",
      errorCode: "RUNTIME_RESTART_IN_PROGRESS",
      logId: "log-supervisor-42",
      status: 503
    });
  });

  it("无法识别的 Tauri 异常使用受控后备错误", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {}
    });
    invoke.mockRejectedValue(new Error("raw bridge failure"));

    await expect(getDesktopRuntimeSupervisorStatus()).rejects.toMatchObject({
      message: "无法读取本机 Runtime 状态，请重新启动桌面应用。",
      errorCode: "RUNTIME_SUPERVISOR_COMMAND_FAILED",
      logId: null,
      status: 503
    });
  });
});

function supervisorStatus(
  status: "starting" | "ready"
) {
  return {
    status,
    phase: status === "ready" ? "ready" : "spawning",
    baseUrl: status === "ready" ? "http://127.0.0.1:18120" : null,
    errorCode: null,
    generation: 1,
    logId: null,
    restartAttempt: 0,
    maxRestartAttempts: 2,
    canRestart: status !== "starting",
    updatedAtEpochMs: Date.now()
  };
}
