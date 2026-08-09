import { defineStore } from "pinia";

import {
  createModelProfile,
  listCapabilityRoutes,
  listModelCapabilities,
  listModelProfiles,
  listPromptProfiles,
  listProviderProfiles,
  startModelCapabilityCheck,
  updateCapabilityRoute,
  validateCapabilityRoute
} from "@/app/runtime-client/ai-system";
import { isRuntimeRequestAborted } from "@/app/runtime-client/core";
import { cancelSystemTask, getSystemTask } from "@/app/runtime-client/tasks";
import type {
  AICapabilityKey,
  CapabilityRouteDto,
  CapabilityRouteInput,
  ModelCreateInput,
  ModelCapabilityListItemDto,
  ModelProfileDto,
  PromptProfileDto,
  ProviderDto
} from "@/types/runtime/ai-system";
import type { RuntimeTaskDto, TaskAcceptedDto } from "@/types/runtime/tasks";

import {
  capabilityLabel,
  createAIOperationKey,
  logAIConfigError,
  pageStateFromError,
  toAIConfigUiError
} from "./ai-config-helpers";
import type { AIConfigUiError, AIPageState } from "./ai-config-types";

type ModelRouteState = {
  providers: ProviderDto[];
  models: ModelProfileDto[];
  capabilities: ModelCapabilityListItemDto[];
  routes: CapabilityRouteDto[];
  prompts: PromptProfileDto[];
  mode: "models" | "routes";
  search: string;
  selectedModelId: string | null;
  selectedCapabilityKey: AICapabilityKey | null;
  state: AIPageState;
  error: AIConfigUiError | null;
  feedback: string | null;
  task: TaskAcceptedDto | RuntimeTaskDto | null;
  busyKey: string | null;
};

let loadController: AbortController | null = null;
let loadSequence = 0;

export const useModelRouteConfigStore = defineStore("p0-ai-model-route", {
  state: (): ModelRouteState => ({
    providers: [],
    models: [],
    capabilities: [],
    routes: [],
    prompts: [],
    mode: "models",
    search: "",
    selectedModelId: null,
    selectedCapabilityKey: null,
    state: "idle",
    error: null,
    feedback: null,
    task: null,
    busyKey: null
  }),
  getters: {
    selectedModel(state): ModelProfileDto | null {
      return state.models.find(
        (model) => model.id === state.selectedModelId
      ) ?? null;
    },
    selectedRoute(state): CapabilityRouteDto | null {
      return state.routes.find(
        (route) => route.capabilityKey === state.selectedCapabilityKey
      ) ?? null;
    },
    filteredModels(state): ModelProfileDto[] {
      const search = state.search.trim().toLocaleLowerCase();
      if (!search) return state.models;
      return state.models.filter((model) =>
        model.modelId.toLocaleLowerCase().includes(search)
        || model.displayName.toLocaleLowerCase().includes(search)
        || capabilityListText(model).includes(search)
      );
    },
    filteredRoutes(state): CapabilityRouteDto[] {
      const search = state.search.trim().toLocaleLowerCase();
      if (!search) return state.routes;
      return state.routes.filter((route) =>
        route.capabilityKey.toLocaleLowerCase().includes(search)
        || capabilityLabel(route.capabilityKey).includes(search)
      );
    },
    hasFilters(state): boolean {
      return Boolean(state.search.trim());
    }
  },
  actions: {
    async load(): Promise<void> {
      const sequence = ++loadSequence;
      loadController?.abort();
      loadController = new AbortController();
      if (!this.models.length && !this.routes.length) this.state = "loading";
      this.error = null;
      try {
        const options = { signal: loadController.signal };
        const [providers, models, capabilities, routes, prompts] = await Promise.all([
          listProviderProfiles({ limit: 200 }, options),
          listModelProfiles({ limit: 200 }, options),
          listModelCapabilities({ limit: 200 }, options),
          listCapabilityRoutes({ limit: 200 }, options),
          listPromptProfiles({ limit: 200 }, options)
        ]);
        if (sequence !== loadSequence) return;
        this.providers = providers.data.items;
        this.models = models.data.items;
        this.capabilities = capabilities.data.items;
        this.routes = routes.data.items;
        this.prompts = prompts.data.items;
        this.ensureSelections();
        this.recomputeState();
      } catch (error) {
        if (isRuntimeRequestAborted(error) || sequence !== loadSequence) return;
        this.fail(error, "模型、能力与 Route 加载失败。");
      } finally {
        if (sequence === loadSequence) loadController = null;
      }
    },

    setMode(mode: "models" | "routes"): void {
      this.mode = mode;
      this.search = "";
      this.recomputeState();
    },

    selectModel(modelId: string | null): void {
      this.selectedModelId = modelId;
    },

    selectRoute(capabilityKey: AICapabilityKey | null): void {
      this.selectedCapabilityKey = capabilityKey;
    },

    clearFilters(): void {
      this.search = "";
      this.recomputeState();
    },

    clearFeedback(): void {
      this.feedback = null;
      this.error = null;
      this.recomputeState();
    },

    providerFor(model: ModelProfileDto): ProviderDto | null {
      return this.providers.find(
        (provider) => provider.id === model.providerProfileId
      ) ?? null;
    },

    capabilitiesFor(modelId: string): ModelCapabilityListItemDto[] {
      return this.capabilities.filter(
        (capability) => capability.modelProfileId === modelId
      );
    },

    eligibleModels(capabilityKey: AICapabilityKey): ModelProfileDto[] {
      const eligibleIds = new Set(
        this.capabilities
          .filter(
            (item) =>
              item.capabilityKey === capabilityKey
              && item.availability === "available"
              && item.contractVerified
          )
          .map((item) => item.modelProfileId)
      );
      const eligibleProviderIds = new Set(
        this.providers
          .filter(
            (provider) =>
              provider.enabled
              && provider.healthStatus === "ready"
          )
          .map((provider) => provider.id)
      );
      return this.models.filter(
        (model) =>
          model.enabled
          && eligibleProviderIds.has(model.providerProfileId)
          && eligibleIds.has(model.id)
      );
    },

    promptsFor(capabilityKey: AICapabilityKey): PromptProfileDto[] {
      return this.prompts.filter(
        (prompt) =>
          prompt.capabilityKey === capabilityKey
          && prompt.activeVersionId !== null
      );
    },

    async checkCapabilities(
      model: ModelProfileDto,
      capabilityKeys?: AICapabilityKey[]
    ): Promise<boolean> {
      return this.runMutation(`capability-check:${model.id}`, async () => {
        const result = await startModelCapabilityCheck(
          model.id,
          { capabilityKeys, force: true },
          {
            idempotencyKey: createAIOperationKey(
              "capability-check",
              model.id
            )
          }
        );
        this.task = result.data;
        this.feedback = "能力契约验证任务已提交。";
        this.recomputeState();
      });
    },

    async createManualModel(input: ModelCreateInput): Promise<boolean> {
      return this.runMutation("model-create", async () => {
        const result = await createModelProfile(input, {
          idempotencyKey: createAIOperationKey(
            "model-create",
            input.providerProfileId
          )
        });
        this.selectedModelId = result.data.id;
        this.feedback = "真实模型已登记，请继续运行能力契约验证。";
        await this.load();
      });
    },

    async saveRoute(
      route: CapabilityRouteDto,
      input: CapabilityRouteInput
    ): Promise<boolean> {
      return this.runMutation(`route-save:${route.capabilityKey}`, async () => {
        await updateCapabilityRoute(route.capabilityKey, input, {
          expectedRevision: route.revision,
          idempotencyKey: createAIOperationKey(
            "route-save",
            route.capabilityKey
          )
        });
        this.feedback = "主模型、回退模型与 Prompt 已原子保存。";
        await this.load();
      });
    },

    async createRoute(
      capabilityKey: AICapabilityKey,
      input: CapabilityRouteInput
    ): Promise<boolean> {
      return this.runMutation(`route-create:${capabilityKey}`, async () => {
        await updateCapabilityRoute(capabilityKey, input, {
          expectedRevision: 0,
          idempotencyKey: createAIOperationKey(
            "route-create",
            capabilityKey
          )
        });
        this.mode = "routes";
        this.selectedCapabilityKey = capabilityKey;
        this.feedback = "首条能力 Route 已按修订 0 原子创建。";
        await this.load();
      });
    },

    async validateRoute(route: CapabilityRouteDto): Promise<boolean> {
      return this.runMutation(
        `route-validate:${route.capabilityKey}`,
        async () => {
          await validateCapabilityRoute(route.capabilityKey, {
            idempotencyKey: createAIOperationKey(
              "route-validate",
              route.capabilityKey
            )
          });
          this.feedback = "Route 验证已完成。";
          await this.load();
        }
      );
    },

    async refreshTask(): Promise<void> {
      if (!this.task) return;
      try {
        this.task = (await getSystemTask(this.task.taskId)).data;
        if (["completed", "failed"].includes(this.task.status)) await this.load();
        this.recomputeState();
      } catch (error) {
        this.fail(error, "能力验证任务状态读取失败。");
      }
    },

    async cancelTask(): Promise<void> {
      if (!this.task?.cancellable) return;
      try {
        this.task = (
          await cancelSystemTask(this.task.taskId, {
            idempotencyKey: createAIOperationKey(
              "capability-check-cancel",
              this.task.taskId
            )
          })
        ).data;
        this.feedback = "取消请求已提交。";
        this.recomputeState();
      } catch (error) {
        this.fail(error, "能力验证任务取消失败。");
      }
    },

    recomputeState(): void {
      if (this.error) {
        this.state = pageStateFromError(this.error);
        return;
      }
      if (
        this.task
        && ["queued", "running", "cancelling"].includes(this.task.status)
      ) {
        this.state = "waiting_external";
        return;
      }
      const visible = this.mode === "models"
        ? this.filteredModels
        : this.filteredRoutes;
      if (!this.providers.length) this.state = "first_use";
      else if (this.mode === "models" && !this.models.length) {
        this.state = "dependency_blocked";
      } else if (!visible.length && this.hasFilters) {
        this.state = "filtered_empty";
      } else if (!visible.length) {
        this.state = "empty";
      } else {
        this.state = "ready";
      }
    },

    ensureSelections(): void {
      if (
        this.selectedModelId
        && !this.models.some((model) => model.id === this.selectedModelId)
      ) {
        this.selectedModelId = null;
      }
      if (
        this.selectedCapabilityKey
        && !this.routes.some(
          (route) => route.capabilityKey === this.selectedCapabilityKey
        )
      ) {
        this.selectedCapabilityKey = null;
      }
    },

    async runMutation(
      busyKey: string,
      operation: () => Promise<void>
    ): Promise<boolean> {
      this.busyKey = busyKey;
      this.error = null;
      try {
        await operation();
        return true;
      } catch (error) {
        this.fail(error, "AI 模型或 Route 操作失败。");
        return false;
      } finally {
        if (this.busyKey === busyKey) this.busyKey = null;
      }
    },

    fail(error: unknown, fallback: string): void {
      logAIConfigError(fallback, error);
      this.error = toAIConfigUiError(error, fallback);
      this.state = pageStateFromError(this.error);
    }
  }
});

function capabilityListText(model: ModelProfileDto): string {
  return model.capabilities
    .map((capability) => capabilityLabel(capability.capabilityKey))
    .join(" ")
    .toLocaleLowerCase();
}
