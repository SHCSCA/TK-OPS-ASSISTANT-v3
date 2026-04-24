import { defineStore } from "pinia";

import {
  fetchAICapabilitySettings,
  fetchAICapabilitySupportMatrix,
  fetchAIModelCatalog,
  fetchAIProviderCatalog,
  refreshAIProviderModels,
  saveAICapabilitySettings,
  saveAIProviderSecret,
  upsertAIProviderModel,
  checkAIProviderHealth
} from "@/app/runtime-client";
import { useTaskBusStore } from "@/stores/task-bus";
import type {
  AICapabilityConfig,
  AICapabilitySettings,
  AICapabilitySupportMatrix,
  AIModelCatalogItem,
  AIModelCatalogRefreshResult,
  AIProviderCatalogItem,
  AIProviderSecretInput,
  AIProviderModelUpsertInput,
  RuntimeRequestErrorShape,
  AIProviderHealthInput,
  AIProviderHealth
} from "@/types/runtime";
import type { TaskEvent } from "@/types/task-events";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";

export type AIStoreStatus = "idle" | "loading" | "ready" | "saving" | "error";

type AIStoreState = {
  settings: AICapabilitySettings | null;
  supportMatrix: AICapabilitySupportMatrix | null;
  providerCatalog: AIProviderCatalogItem[];
  modelCatalogByProvider: Record<string, AIModelCatalogItem[]>;
  refreshResultByProvider: Record<string, AIModelCatalogRefreshResult>;
  providerHealth: Record<string, AIProviderHealth>;
  status: AIStoreStatus;
  error: RuntimeRequestErrorShape | null;
  _unsubscriber: (() => void) | null;
};

export const useAIStore = defineStore("ai-capability", {
  state: (): AIStoreState => ({
    settings: null,
    supportMatrix: null,
    providerCatalog: [],
    modelCatalogByProvider: {},
    refreshResultByProvider: {},
    providerHealth: {},
    status: "idle",
    error: null,
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
      this.status = "loading";
      this.error = null;
      try {
        const [settings, matrix, providers] = await Promise.all([
          fetchAICapabilitySettings(),
          fetchAICapabilitySupportMatrix(),
          fetchAIProviderCatalog()
        ]);
        this.settings = settings;
        this.supportMatrix = matrix;
        this.providerCatalog = providers;
        this.status = "ready";
        
        this.initializeEventSubscription();
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    // Compatibility actions
    async loadProviderCatalog(): Promise<void> {
      return this.reloadProviderCatalog();
    },
    async loadSupportMatrix(): Promise<void> {
      return this.reloadSupportMatrix();
    },
    async loadProviderModels(providerId: string): Promise<void> {
      return this.loadModelsForProvider(providerId);
    },
    async checkProvider(providerId: string, input?: AIProviderHealthInput): Promise<AIProviderHealth> {
      const health = await this.checkAIProviderHealth(providerId, input);
      this.providerHealth[providerId] = health;
      if (health.message.includes("已从可选模型中屏蔽")) {
        await Promise.all([this.loadModelsForProvider(providerId), this.reloadSupportMatrix()]);
      }
      return health;
    },

    initializeEventSubscription(): void {
      if (this._unsubscriber) return;

      const taskBus = useTaskBusStore();
      this._unsubscriber = taskBus.subscribeToType("ai-capability.changed", (event: TaskEvent) => {
        void this.handleAICapabilityChanged(event);
      });
    },

    async handleAICapabilityChanged(event: TaskEvent): Promise<void> {
      const incomingVersion = event.configVersion ?? 0;
      const currentVersion = this.settings?.configVersion ?? 0;

      if (incomingVersion > currentVersion) {
        try {
          const providerIds = event.providerIds ?? [];
          
          switch (event.reason) {
            case "capability_config_updated":
              await Promise.all([this.reloadSettings(), this.reloadSupportMatrix()]);
              break;
            case "provider_secret_updated":
              await Promise.all([this.reloadSettings(), this.reloadProviderCatalog()]);
              break;
            case "provider_model_upserted":
              for (const pId of providerIds) {
                await Promise.all([this.loadModelsForProvider(pId), this.reloadSupportMatrix()]);
              }
              break;
            case "provider_models_refreshed":
            case "provider_model_disabled":
              for (const pId of providerIds) {
                await Promise.all([
                  this.loadModelsForProvider(pId),
                  this.reloadProviderCatalog(),
                  this.reloadSupportMatrix()
                ]);
              }
              break;
            case "provider_health_refreshed":
              await this.reloadSettings();
              break;
            default:
              await this.load();
          }
        } catch (e) {
          console.error("[ai-capability] Failed to refresh after change event", e);
        }
      }
    },

    async reloadSettings(): Promise<void> {
      this.settings = await fetchAICapabilitySettings();
    },

    async reloadSupportMatrix(): Promise<void> {
      this.supportMatrix = await fetchAICapabilitySupportMatrix();
    },

    async reloadProviderCatalog(): Promise<void> {
      this.providerCatalog = await fetchAIProviderCatalog();
    },

    async saveCapabilities(input: Partial<AICapabilitySettings> | AICapabilityConfig[]): Promise<void> {
      this.status = "saving";
      try {
        const payload = Array.isArray(input) ? { capabilities: input } : input;
        // Ensure payload structure matches expected AICapabilitySettings format
        await saveAICapabilitySettings(payload.capabilities as any);
        await this.reloadSettings();
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    async saveProviderSecret(providerId: string, input: AIProviderSecretInput): Promise<void> {
      this.status = "saving";
      try {
        await saveAIProviderSecret(providerId, input);
        await Promise.all([this.reloadSettings(), this.reloadProviderCatalog()]);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    async saveProviderModel(providerId: string, modelId: string, input: AIProviderModelUpsertInput): Promise<void> {
      this.status = "saving";
      try {
        await upsertAIProviderModel(providerId, modelId, input);
        await this.loadModelsForProvider(providerId);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    async loadModelsForProvider(providerId: string): Promise<void> {
      try {
        const models = await fetchAIModelCatalog(providerId);
        this.modelCatalogByProvider = {
          ...this.modelCatalogByProvider,
          [providerId]: models
        };
      } catch (error) {
        console.error(`Failed to load models for ${providerId}`, error);
      }
    },

    async refreshProviderModels(providerId: string): Promise<void> {
      try {
        const result = await refreshAIProviderModels(providerId);
        this.refreshResultByProvider = {
          ...this.refreshResultByProvider,
          [providerId]: result
        };
        await this.loadModelsForProvider(providerId);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    async checkAIProviderHealth(providerId: string, input: AIProviderHealthInput = {}): Promise<AIProviderHealth> {
      return checkAIProviderHealth(providerId, input);
    },

    applyRuntimeError(error: unknown): void {
      this.status = "error";
      this.error = toRuntimeErrorShape(error, "AI 能力数据同步失败");
    }
  }
});

export const useAICapabilityStore = useAIStore;
