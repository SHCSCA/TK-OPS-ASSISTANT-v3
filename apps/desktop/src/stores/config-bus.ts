import { defineStore } from "pinia";

import {
  fetchRuntimeConfig,
  fetchRuntimeDiagnostics,
  fetchRuntimeHealth,
  updateRuntimeConfig
} from "@/app/runtime-client";
import type {
  AppSettings,
  AppSettingsUpdateInput,
  RuntimeDiagnostics,
  RuntimeHealthSnapshot,
  RuntimeRequestErrorShape
} from "@/types/runtime";
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
};

export const useConfigBusStore = defineStore("config-bus", {
  state: (): ConfigBusState => ({
    diagnostics: null,
    error: null,
    health: null,
    lastSyncedAt: "",
    settings: null,
    status: "idle",
    runtimeStatus: "idle"
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
      } catch (error) {
        this.applyRuntimeError(error);
      }
    }
  }
});
