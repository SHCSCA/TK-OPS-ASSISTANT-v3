import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  checkAIProviderHealth,
  fetchAICapabilitySupportMatrix,
  fetchAICapabilitySettings,
  fetchAIProviderCatalog,
  fetchAIProviderModels,
  updateAIProviderSecret,
  updateAICapabilitySettings
} from "@/app/runtime-client";
import type {
  AICapabilityConfig,
  AICapabilitySettings,
  AICapabilitySupportMatrix,
  AIModelCatalogItem,
  AIProviderCatalogItem,
  AIProviderHealth,
  AIProviderSecretInput,
  RuntimeRequestErrorShape
} from "@/types/runtime";

export type AICapabilityStoreStatus = "idle" | "loading" | "ready" | "saving" | "error";

type AICapabilityStoreState = {
  error: RuntimeRequestErrorShape | null;
  lastCheckedProviderId: string | null;
  modelCatalogByProvider: Record<string, AIModelCatalogItem[]>;
  providerCatalog: AIProviderCatalogItem[];
  providerHealth: Record<string, AIProviderHealth>;
  settings: AICapabilitySettings | null;
  status: AICapabilityStoreStatus;
  supportMatrix: AICapabilitySupportMatrix | null;
};

export const useAICapabilityStore = defineStore("ai-capability", {
  state: (): AICapabilityStoreState => ({
    error: null,
    lastCheckedProviderId: null,
    modelCatalogByProvider: {},
    providerCatalog: [],
    providerHealth: {},
    settings: null,
    status: "idle",
    supportMatrix: null
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
        const nextSettings = await updateAICapabilitySettings(capabilities);
        this.settings = {
          capabilities: nextSettings.capabilities,
          providers: nextSettings.providers ?? this.settings?.providers ?? []
        };
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async loadProviderCatalog(): Promise<void> {
      this.status = this.status === "idle" ? "loading" : this.status;
      this.error = null;

      try {
        this.providerCatalog = await fetchAIProviderCatalog();
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async loadProviderModels(providerId: string): Promise<void> {
      this.error = null;

      try {
        this.modelCatalogByProvider = {
          ...this.modelCatalogByProvider,
          [providerId]: await fetchAIProviderModels(providerId)
        };
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async loadSupportMatrix(): Promise<void> {
      this.error = null;

      try {
        this.supportMatrix = await fetchAICapabilitySupportMatrix();
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async saveProviderSecret(
      providerId: string,
      input: AIProviderSecretInput
    ): Promise<void> {
      this.status = "saving";
      this.error = null;

      try {
        const status = await updateAIProviderSecret(providerId, input);
        if (this.settings) {
          this.settings = {
            ...this.settings,
            providers: (this.settings.providers ?? []).map((item) =>
              item.provider === providerId ? status : item
            )
          };
        }
        this.providerCatalog = this.providerCatalog.map((item) =>
          item.provider === providerId
            ? {
                ...item,
                configured: status.configured,
                baseUrl: status.baseUrl,
                secretSource: status.secretSource,
                status: status.configured ? "ready" : item.status
              }
            : item
        );
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async checkProvider(providerId: string, model?: string): Promise<void> {
      this.error = null;

      try {
        const health = await checkAIProviderHealth(providerId, { model });
        this.providerHealth = {
          ...this.providerHealth,
          [providerId]: health
        };
        this.lastCheckedProviderId = providerId;
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
