import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  fetchAICapabilitySettings,
  updateAICapabilitySettings
} from "@/app/runtime-client";
import type {
  AICapabilityConfig,
  AICapabilitySettings,
  RuntimeRequestErrorShape
} from "@/types/runtime";

export type AICapabilityStoreStatus = "idle" | "loading" | "ready" | "saving" | "error";

type AICapabilityStoreState = {
  error: RuntimeRequestErrorShape | null;
  settings: AICapabilitySettings | null;
  status: AICapabilityStoreStatus;
};

export const useAICapabilityStore = defineStore("ai-capability", {
  state: (): AICapabilityStoreState => ({
    error: null,
    settings: null,
    status: "idle"
  }),
  actions: {
    async load(): Promise<void> {
      this.status = "loading";
      this.error = null;

      try {
        this.settings = await fetchAICapabilitySettings();
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async refresh(): Promise<void> {
      await this.load();
    },
    async saveCapabilities(capabilities: AICapabilityConfig[]): Promise<void> {
      this.status = "saving";
      this.error = null;

      try {
        this.settings = await updateAICapabilitySettings(capabilities);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    applyRuntimeError(error: unknown): void {
      const runtimeError =
        error instanceof RuntimeRequestError
          ? error
          : new RuntimeRequestError("AI capability request failed.");

      this.status = "error";
      this.error = {
        details: runtimeError.details,
        message: runtimeError.message,
        requestId: runtimeError.requestId,
        status: runtimeError.status
      };
    }
  }
});
