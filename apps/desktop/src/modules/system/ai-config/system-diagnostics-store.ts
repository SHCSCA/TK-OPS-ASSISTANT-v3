import { defineStore } from "pinia";

import {
  getSafeLogExcerpt,
  getSystemDiagnostics
} from "@/app/runtime-client/ai-system";
import { isRuntimeRequestAborted } from "@/app/runtime-client/core";
import { fetchSystemConfig } from "@/app/runtime-client/system-config";
import type {
  DiagnosticsDto,
  SafeLogExcerptDto
} from "@/types/runtime/ai-system";
import type { SystemConfigDto } from "@/types/runtime/system-config";

import {
  logAIConfigError,
  pageStateFromError,
  toAIConfigUiError
} from "./ai-config-helpers";
import type { AIConfigUiError, AIPageState } from "./ai-config-types";

type SystemDiagnosticsState = {
  config: SystemConfigDto | null;
  diagnostics: DiagnosticsDto | null;
  logExcerpt: SafeLogExcerptDto | null;
  logIdInput: string;
  runtimeState: AIPageState;
  diagnosticsState: AIPageState;
  error: AIConfigUiError | null;
};

let runtimeController: AbortController | null = null;
let diagnosticsController: AbortController | null = null;
let logController: AbortController | null = null;
let runtimeSequence = 0;
let diagnosticsSequence = 0;
let logSequence = 0;

export const useSystemDiagnosticsStore = defineStore(
  "p0-ai-system-diagnostics",
  {
    state: (): SystemDiagnosticsState => ({
      config: null,
      diagnostics: null,
      logExcerpt: null,
      logIdInput: "",
      runtimeState: "idle",
      diagnosticsState: "idle",
      error: null
    }),
    actions: {
      async loadRuntime(): Promise<void> {
        const sequence = ++runtimeSequence;
        runtimeController?.abort();
        const controller = new AbortController();
        runtimeController = controller;
        this.runtimeState = "loading";
        this.error = null;
        try {
          const [config, diagnostics] = await Promise.all([
            fetchSystemConfig({ signal: controller.signal }),
            getSystemDiagnostics(
              ["runtime", "directories", "sidecar"],
              { signal: controller.signal }
            )
          ]);
          if (sequence !== runtimeSequence) return;
          this.config = config.data;
          this.diagnostics = diagnostics.data;
          this.runtimeState = "ready";
        } catch (error) {
          if (isRuntimeRequestAborted(error) || sequence !== runtimeSequence) {
            return;
          }
          this.fail(error, "Runtime 与工作区状态加载失败。", "runtime");
        } finally {
          if (runtimeController === controller) runtimeController = null;
        }
      },

      async loadDiagnostics(): Promise<void> {
        const sequence = ++diagnosticsSequence;
        diagnosticsController?.abort();
        const controller = new AbortController();
        diagnosticsController = controller;
        this.diagnosticsState = "loading";
        this.error = null;
        try {
          const result = await getSystemDiagnostics([], {
            signal: controller.signal
          });
          if (sequence !== diagnosticsSequence) return;
          this.diagnostics = result.data;
          this.diagnosticsState = "ready";
        } catch (error) {
          if (
            isRuntimeRequestAborted(error)
            || sequence !== diagnosticsSequence
          ) {
            return;
          }
          this.fail(error, "日志与诊断摘要加载失败。", "diagnostics");
        } finally {
          if (diagnosticsController === controller) {
            diagnosticsController = null;
          }
        }
      },

      async lookupLog(logId?: string): Promise<void> {
        const normalized = (logId ?? this.logIdInput).trim();
        if (!normalized) {
          this.error = {
            message: "请输入关联日志 ID。",
            errorCode: "REQUEST_VALIDATION_FAILED",
            logId: null,
            requestId: null,
            retryable: false
          };
          return;
        }
        const sequence = ++logSequence;
        logController?.abort();
        const controller = new AbortController();
        logController = controller;
        this.logIdInput = normalized;
        this.error = null;
        try {
          const result = await getSafeLogExcerpt(normalized, {
            signal: controller.signal
          });
          if (sequence !== logSequence || this.logIdInput !== normalized) {
            return;
          }
          this.logExcerpt = result.data;
          this.diagnosticsState = "ready";
        } catch (error) {
          if (isRuntimeRequestAborted(error) || sequence !== logSequence) {
            return;
          }
          this.logExcerpt = null;
          this.fail(error, "日志摘要读取失败。", "diagnostics");
        } finally {
          if (logController === controller) logController = null;
        }
      },

      clearLog(): void {
        logSequence += 1;
        logController?.abort();
        logController = null;
        this.logExcerpt = null;
        this.logIdInput = "";
        this.error = null;
      },

      fail(
        error: unknown,
        fallback: string,
        target: "runtime" | "diagnostics"
      ): void {
        logAIConfigError(fallback, error);
        this.error = toAIConfigUiError(error, fallback);
        const state = pageStateFromError(this.error);
        if (target === "runtime") this.runtimeState = state;
        else this.diagnosticsState = state;
      }
    }
  }
);
