import { defineStore } from "pinia";

import {
  fetchProviderHealth,
  fetchRuntimeConfig,
  fetchRuntimeDiagnostics,
  fetchRuntimeHealth,
  updateRuntimeConfig
} from "@/app/runtime-client";
import { useTaskBusStore } from "@/stores/task-bus";
import type {
  AppSettings,
  AppSettingsUpdateInput,
  RuntimeDiagnostics,
  RuntimeHealthSnapshot,
  RuntimeRequestErrorShape,
  AIProviderHealth
} from "@/types/runtime";
import type { TaskEvent } from "@/types/task-events";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";

export type ConfigBusStatus = "idle" | "loading" | "ready" | "saving" | "error";
export type RuntimeConnectionStatus = "idle" | "loading" | "online" | "offline";

type ConfigBusState = {
  diagnostics: RuntimeDiagnostics | null;
  error: RuntimeRequestErrorShape | null;
  health: RuntimeHealthSnapshot | null;
  lastSyncedAt: string;
  settings: AppSettings | null;
  status: ConfigBusStatus;
  runtimeStatus: RuntimeConnectionStatus;
  providerReadiness: Record<string, AIProviderHealth>;
  _unsubscriber: (() => void) | null;
};

export const useConfigBusStore = defineStore("config-bus", {
  state: (): ConfigBusState => ({
    diagnostics: null,
    error: null,
    health: null,
    lastSyncedAt: "",
    settings: null,
    status: "idle",
    runtimeStatus: "idle",
    providerReadiness: {},
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
        console.warn("Failed to fetch provider health silently", err);
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
          const [settings, diagnostics] = await Promise.all([
            fetchRuntimeConfig(),
            fetchRuntimeDiagnostics()
          ]);
          this.settings = settings;
          this.diagnostics = diagnostics;
          this.lastSyncedAt = new Date().toISOString();
        } catch (e) {
          console.error("[config-bus] Failed to re-sync after change event", e);
        }
      }
    },
    async save(input: AppSettingsUpdateInput): Promise<void> {
      this.status = "saving";
      this.error = null;

      try {
        this.settings = await updateRuntimeConfig(input);
        const [health, diagnostics] = await Promise.all([
          fetchRuntimeHealth(),
          fetchRuntimeDiagnostics()
        ]);

        this.health = health;
        this.diagnostics = diagnostics;
        this.runtimeStatus = "online";
        this.status = "ready";
        this.lastSyncedAt = new Date().toISOString();
        this.fetchProviderReadinessSilently();
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    applyRuntimeError(error: unknown): void {
      this.runtimeStatus = "offline";
      this.status = "error";
      this.error = toRuntimeErrorShape(error, "Runtime 配置请求失败，请稍后重试。");
    },
    async hydrate(nextStatus: ConfigBusStatus): Promise<void> {
      this.status = nextStatus;
      this.runtimeStatus = "loading";
      this.error = null;

      try {
        const [health, settings, diagnostics] = await Promise.all([
          fetchRuntimeHealth(),
          fetchRuntimeConfig(),
          fetchRuntimeDiagnostics()
        ]);

        this.health = health;
        this.settings = settings;
        this.diagnostics = diagnostics;
        this.runtimeStatus = "online";
        this.status = "ready";
        this.lastSyncedAt = new Date().toISOString();
        
        this.fetchProviderReadinessSilently();
        this.initializeEventSubscription();
      } catch (error) {
        this.applyRuntimeError(error);
      }
    }
  }
});
