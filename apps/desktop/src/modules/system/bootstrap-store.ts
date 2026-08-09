import { defineStore } from "pinia";

import {
  activateBootstrapLicense,
  fetchBootstrapStatus,
  initializeBootstrapDirectories,
  startBootstrapSelfChecks
} from "@/app/runtime-client/bootstrap";
import {
  isRuntimeRequestAborted,
  RuntimeError
} from "@/app/runtime-client/core";
import {
  getDesktopRuntimeSupervisorStatus,
  isDesktopRuntimeSupervisorAvailable,
  restartDesktopRuntime,
  type RuntimeSupervisorStatus
} from "@/app/runtime-client/connection";
import {
  cancelSystemTask,
  getSystemTask
} from "@/app/runtime-client/tasks";
import type {
  BootstrapStatusDto,
  SelfCheckKey
} from "@/types/runtime/bootstrap";
import type { RuntimeTaskDto } from "@/types/runtime/tasks";

import {
  createOperationId,
  toBootstrapUiError,
  waitForPoll,
  type BootstrapUiError
} from "./bootstrap-helpers";

export type P0BootstrapPhase =
  | "idle"
  | "loading"
  | "setup_required"
  | "ready"
  | "error";

export type BootstrapOperation =
  | "idle"
  | "activating_license"
  | "initializing_directories"
  | "running_self_checks"
  | "cancelling_self_checks"
  | "restarting_runtime"
  | "refreshing";

type P0BootstrapState = {
  phase: P0BootstrapPhase;
  operation: BootstrapOperation;
  snapshot: BootstrapStatusDto | null;
  activeTask: RuntimeTaskDto | null;
  error: BootstrapUiError | null;
  supervisorStatus: RuntimeSupervisorStatus | null;
  monitorController: AbortController | null;
};

const SELF_CHECKS: SelfCheckKey[] = [
  "database",
  "directories",
  "media_tools",
  "runtime"
];
const TASK_POLL_INTERVAL_MS = 700;
const TASK_MONITOR_TIMEOUT_MS = 120_000;
const SUPERVISOR_POLL_INTERVAL_MS = 500;
const SUPERVISOR_RESTART_TIMEOUT_MS = 45_000;

export const useP0BootstrapStore = defineStore("p0-bootstrap", {
  state: (): P0BootstrapState => ({
    phase: "idle",
    operation: "idle",
    snapshot: null,
    activeTask: null,
    error: null,
    supervisorStatus: null,
    monitorController: null
  }),
  getters: {
    licenseActive: (state): boolean =>
      state.snapshot?.license.status === "active",
    canContinue: (state): boolean =>
      state.snapshot?.canContinue === true,
    isBusy: (state): boolean =>
      state.operation !== "idle",
    canRestartRuntime: (state): boolean =>
      state.supervisorStatus?.canRestart === true
  },
  actions: {
    async load(): Promise<void> {
      if (this.phase === "loading") {
        return;
      }
      this.phase = "loading";
      this.operation = "refreshing";
      this.error = null;
      try {
        const result = await fetchBootstrapStatus();
        this.applySnapshot(result.data);
      } catch (error) {
        this.applyError(error, "无法连接本机 Runtime，请重新启动后重试。");
        await this.syncSupervisorStatus();
      } finally {
        this.operation = "idle";
      }
    },

    async refresh(): Promise<void> {
      this.operation = "refreshing";
      this.error = null;
      try {
        const result = await fetchBootstrapStatus();
        this.applySnapshot(result.data);
      } catch (error) {
        this.applyError(error, "刷新首启状态失败，请稍后重试。");
      } finally {
        this.operation = "idle";
      }
    },

    async activateLicense(licenseKey: string): Promise<boolean> {
      this.operation = "activating_license";
      this.error = null;
      const operationId = createOperationId("bootstrap-license");
      try {
        await activateBootstrapLicense(
          {
            licenseKey: licenseKey.trim()
          },
          {
            idempotencyKey: operationId,
            operationId
          }
        );
        await this.refresh();
        return this.licenseActive;
      } catch (error) {
        this.applyError(error, "许可证激活失败，请检查输入后重试。");
        return false;
      } finally {
        if (this.operation === "activating_license") {
          this.operation = "idle";
        }
      }
    },

    async initializeDirectories(
      workspaceRootRef: string | null = null
    ): Promise<boolean> {
      this.operation = "initializing_directories";
      this.error = null;
      const operationId = createOperationId("bootstrap-directories");
      try {
        await initializeBootstrapDirectories(
          { workspaceRootRef },
          {
            idempotencyKey: operationId,
            operationId
          }
        );
        await this.refresh();
        return this.snapshot?.directories.status !== "failed";
      } catch (error) {
        this.applyError(error, "目录初始化失败，请检查日志后重试。");
        return false;
      } finally {
        if (this.operation === "initializing_directories") {
          this.operation = "idle";
        }
      }
    },

    async runSelfChecks(): Promise<boolean> {
      this.stopMonitoring();
      this.operation = "running_self_checks";
      this.error = null;
      this.activeTask = null;
      const operationId = createOperationId("bootstrap-self-check");
      const controller = new AbortController();
      this.monitorController = controller;
      try {
        const accepted = await startBootstrapSelfChecks(
          { checks: SELF_CHECKS },
          {
            idempotencyKey: operationId,
            operationId,
            signal: controller.signal
          }
        );
        const completed = await this.monitorSystemTask(
          accepted.data.taskId,
          controller
        );
        await this.refresh();
        return (
          completed.status === "completed"
          && completed.completionKind === "succeeded"
        );
      } catch (error) {
        if (
          !controller.signal.aborted
          && !isRuntimeRequestAborted(error)
        ) {
          this.applyError(error, "Runtime 自检失败，请查看日志后重试。");
        }
        return false;
      } finally {
        if (this.monitorController === controller) {
          this.monitorController = null;
        }
        if (this.operation === "running_self_checks") {
          this.operation = "idle";
        }
      }
    },

    async cancelSelfChecks(): Promise<void> {
      const task = this.activeTask;
      this.stopMonitoring();
      if (!task || !task.cancellable) {
        return;
      }
      this.operation = "cancelling_self_checks";
      const operationId = createOperationId("bootstrap-cancel");
      try {
        const result = await cancelSystemTask(task.taskId, {
          idempotencyKey: operationId,
          operationId
        });
        this.activeTask = result.data;
      } catch (error) {
        this.applyError(error, "取消自检失败，任务可能仍在运行。");
      } finally {
        this.operation = "idle";
      }
    },

    async restartRuntime(): Promise<boolean> {
      this.stopMonitoring();
      this.operation = "restarting_runtime";
      this.error = null;
      const controller = new AbortController();
      this.monitorController = controller;
      try {
        this.supervisorStatus = await restartDesktopRuntime();
        await this.waitForSupervisorReady(controller);
        await this.load();
        return this.phase !== "error";
      } catch (error) {
        if (!controller.signal.aborted) {
          this.applyError(
            error,
            "重新启动本机 Runtime 失败，请查看日志后重试。"
          );
        }
        return false;
      } finally {
        if (this.monitorController === controller) {
          this.monitorController = null;
        }
        if (this.operation === "restarting_runtime") {
          this.operation = "idle";
        }
      }
    },

    applySnapshot(snapshot: BootstrapStatusDto): void {
      this.snapshot = snapshot;
      this.error = null;
      this.phase = snapshot.canContinue ? "ready" : "setup_required";
    },

    applyError(error: unknown, fallbackMessage: string): void {
      this.error = toBootstrapUiError(error, fallbackMessage);
      this.phase = "error";
    },

    stopMonitoring(): void {
      this.monitorController?.abort(
        new DOMException("任务监控已取消", "AbortError")
      );
      this.monitorController = null;
    },

    async syncSupervisorStatus(): Promise<void> {
      if (!isDesktopRuntimeSupervisorAvailable()) {
        this.supervisorStatus = null;
        return;
      }
      try {
        this.supervisorStatus =
          await getDesktopRuntimeSupervisorStatus();
      } catch {
        this.supervisorStatus = null;
      }
    },

    async waitForSupervisorReady(
      controller: AbortController
    ): Promise<void> {
      const deadline = Date.now() + SUPERVISOR_RESTART_TIMEOUT_MS;
      while (Date.now() < deadline) {
        const status = await getDesktopRuntimeSupervisorStatus();
        this.supervisorStatus = status;
        if (status.status === "ready") {
          return;
        }
        if (
          status.status === "failed"
          || (
            status.status === "offline"
            && !status.canRestart
          )
        ) {
          throw toSupervisorFailure(status);
        }
        await waitForPoll(
          SUPERVISOR_POLL_INTERVAL_MS,
          controller.signal
        );
      }
      throw new RuntimeError(
        "本机 Runtime 重新启动超时，请查看日志后重试。",
        {
          errorCode: "RUNTIME_RESTART_TIMEOUT",
          logId: this.supervisorStatus?.logId,
          status: 504
        }
      );
    },

    async monitorSystemTask(
      taskId: string,
      controller: AbortController
    ): Promise<RuntimeTaskDto> {
      const deadline = Date.now() + TASK_MONITOR_TIMEOUT_MS;
      while (Date.now() < deadline) {
        const result = await getSystemTask(taskId, {
          signal: controller.signal
        });
        this.activeTask = result.data;
        if (
          result.data.status === "completed"
          || result.data.status === "failed"
        ) {
          if (result.data.status === "failed") {
            throw toTaskFailure(result.data);
          }
          return result.data;
        }
        await waitForPoll(TASK_POLL_INTERVAL_MS, controller.signal);
      }
      throw new Error("Runtime 自检超过两分钟，请取消后重试。");
    }
  }
});

function toTaskFailure(task: RuntimeTaskDto): RuntimeError {
  return new RuntimeError(
    task.errorCode
      ? `Runtime 自检失败（${task.errorCode}）。`
      : "Runtime 自检失败。",
    {
      errorCode: task.errorCode ?? "TASK_FAILED",
      logId: task.logId,
      status: 409
    }
  );
}

function toSupervisorFailure(
  status: RuntimeSupervisorStatus
): RuntimeError {
  return new RuntimeError(
    "本机 Runtime 未能恢复，请查看日志后重试。",
    {
      errorCode: status.errorCode ?? "RUNTIME_RESTART_FAILED",
      logId: status.logId,
      status: 503
    }
  );
}
