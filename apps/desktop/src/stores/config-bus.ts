import { defineStore } from "pinia";

import {
  fetchBootstrapReadiness,
  fetchProviderHealth,
  fetchRuntimeConfig,
  fetchRuntimeDiagnostics,
  fetchRuntimeHealth,
  initializeDirectories,
  runtimeSelfCheck,
  updateRuntimeConfig
} from "@/app/runtime-client";
import { useBootstrapStore } from "@/stores/bootstrap";
import { useTaskBusStore } from "@/stores/task-bus";
import type {
  AppSettings,
  AppSettingsUpdateInput,
  BootstrapDirectoryReport,
  BootstrapReadinessReport,
  RuntimeDiagnostics,
  RuntimeHealthSnapshot,
  RuntimeRequestErrorShape,
  RuntimeSelfCheckReport,
  AIProviderHealth
} from "@/types/runtime";
import type { TaskEvent } from "@/types/task-events";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";

export type ConfigBusStatus = "idle" | "loading" | "ready" | "saving" | "error";
export type RuntimeConnectionStatus = "idle" | "loading" | "online" | "offline";

type ConfigBusState = {
  bootstrapDirectoryReport: BootstrapDirectoryReport | null;
  bootstrapReadiness: BootstrapReadinessReport | null;
  diagnostics: RuntimeDiagnostics | null;
  error: RuntimeRequestErrorShape | null;
  health: RuntimeHealthSnapshot | null;
  lastSyncedAt: string;
  settings: AppSettings | null;
  status: ConfigBusStatus;
  runtimeStatus: RuntimeConnectionStatus;
  runtimeSelfCheckReport: RuntimeSelfCheckReport | null;
  providerReadiness: Record<string, AIProviderHealth>;
  _bootstrapInitializationPromise: Promise<void> | null;
  _unsubscriber: (() => void) | null;
};

export const useConfigBusStore = defineStore("config-bus", {
  state: (): ConfigBusState => ({
    bootstrapDirectoryReport: null,
    bootstrapReadiness: null,
    diagnostics: null,
    error: null,
    health: null,
    lastSyncedAt: "",
    settings: null,
    status: "idle",
    runtimeStatus: "idle",
    runtimeSelfCheckReport: null,
    providerReadiness: {},
    _bootstrapInitializationPromise: null,
    _unsubscriber: null
  }),
  getters: {
    viewState: (state): "loading" | "ready" | "error" =>
      state.status === "error"
        ? "error"
        : state.status === "loading" || state.status === "saving"
          ? "loading"
          : "ready"
  },
  actions: {
    async load(): Promise<void> {
      await this.hydrate("loading");
    },
    async refresh(): Promise<void> {
      await this.hydrate("loading");
    },
    async fetchProviderReadinessSilently(): Promise<void> {
      try {
        const data = await fetchProviderHealth();
        this.providerReadiness = data || {};
      } catch (err) {
        console.warn("静默获取 Provider 健康状态失败", err);
      }
    },
    initializeEventSubscription(): void {
      if (this._unsubscriber) return;

      const taskBus = useTaskBusStore();
      this._unsubscriber = taskBus.subscribeToType("config.changed", (event: TaskEvent) => {
        void this.handleConfigChanged(event);
      });
    },
    async handleConfigChanged(event: TaskEvent): Promise<void> {
      const incomingRevision = event.revision ?? 0;
      const currentRevision = this.settings?.revision ?? 0;

      if (incomingRevision > currentRevision) {
        try {
          const [settings, diagnostics, readiness] = await Promise.all([
            fetchRuntimeConfig(),
            fetchRuntimeDiagnostics(),
            fetchBootstrapReadiness()
          ]);
          this.settings = settings;
          this.diagnostics = diagnostics;
          this.bootstrapReadiness = readiness;
          this.lastSyncedAt = new Date().toISOString();
          await syncBootstrapPhase();
        } catch (e) {
          console.error("[config-bus] 配置变更后重新同步失败", e);
          this.bootstrapReadiness = null;
          this.applyRuntimeError(e);
          await syncBootstrapPhase();
        }
      }
    },
    async save(input: AppSettingsUpdateInput): Promise<void> {
      this.status = "saving";
      this.error = null;

      try {
        await updateRuntimeConfig(input);
        const [health, settings, diagnostics, readiness] = await Promise.all([
          fetchRuntimeHealth(),
          fetchRuntimeConfig(),
          fetchRuntimeDiagnostics(),
          fetchBootstrapReadiness()
        ]);

        this.health = health;
        this.settings = settings;
        this.diagnostics = diagnostics;
        this.bootstrapReadiness = readiness;
        this.runtimeStatus = "online";
        this.status = "ready";
        this.lastSyncedAt = new Date().toISOString();
        this.fetchProviderReadinessSilently();
      } catch (error) {
        console.error("[config-bus] 保存 Runtime 配置失败", error);
        this.applyRuntimeError(error);
      }
    },
    applyRuntimeError(error: unknown): void {
      this.runtimeStatus = "offline";
      this.status = "error";
      this.bootstrapReadiness = null;
      this.error = toRuntimeErrorShape(error, "Runtime 配置请求失败，请稍后重试。");
    },
    async initializeBootstrap(): Promise<void> {
      if (this._bootstrapInitializationPromise) {
        return this._bootstrapInitializationPromise;
      }

      const operation = this.runBootstrapInitialization();
      this._bootstrapInitializationPromise = operation;
      try {
        await operation;
      } finally {
        if (this._bootstrapInitializationPromise === operation) {
          this._bootstrapInitializationPromise = null;
        }
      }
    },
    async runBootstrapInitialization(): Promise<void> {
      this.status = "loading";
      this.runtimeStatus = "loading";
      this.error = null;

      try {
        const directoryReport = await initializeDirectories();
        const selfCheckReport = await runtimeSelfCheck();
        const readiness = await fetchBootstrapReadiness();

        this.bootstrapDirectoryReport = directoryReport;
        this.runtimeSelfCheckReport = selfCheckReport;
        this.bootstrapReadiness = readiness;
        this.runtimeStatus = "online";
        this.status = "ready";
        this.lastSyncedAt = new Date().toISOString();
      } catch (error) {
        console.error("[config-bus] Runtime 首启初始化失败", error);
        this.applyRuntimeError(error);
      }
    },
    async hydrate(nextStatus: ConfigBusStatus): Promise<void> {
      this.status = nextStatus;
      this.runtimeStatus = "loading";
      this.error = null;

      try {
        const [health, settings, diagnostics, readiness] = await Promise.all([
          fetchRuntimeHealth(),
          fetchRuntimeConfig(),
          fetchRuntimeDiagnostics(),
          fetchBootstrapReadiness()
        ]);

        this.health = health;
        this.settings = settings;
        this.diagnostics = diagnostics;
        this.bootstrapReadiness = readiness;
        this.runtimeStatus = "online";
        this.status = "ready";
        this.lastSyncedAt = new Date().toISOString();
        
        this.fetchProviderReadinessSilently();
        this.initializeEventSubscription();
      } catch (error) {
        console.error("[config-bus] Runtime 配置加载失败", error);
        this.applyRuntimeError(error);
      }
    }
  }
});

function syncBootstrapPhase(): void {
  useBootstrapStore().syncPhase();
}
