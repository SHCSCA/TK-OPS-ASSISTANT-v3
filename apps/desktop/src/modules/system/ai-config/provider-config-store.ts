import { defineStore } from "pinia";

import {
  listModelProfiles,
  listProviderProfiles,
  patchProviderProfile,
  startProviderCheck,
  startProviderModelDiscovery
} from "@/app/runtime-client/ai-system";
import { isRuntimeRequestAborted } from "@/app/runtime-client/core";
import { cancelSystemTask, getSystemTask } from "@/app/runtime-client/tasks";
import type {
  ModelProfileDto,
  ProviderDto,
  ProviderHealthStatus,
  ProviderPatchInput
} from "@/types/runtime/ai-system";
import type { RuntimeTaskDto, TaskAcceptedDto } from "@/types/runtime/tasks";

import {
  createAIOperationKey,
  logAIConfigError,
  pageStateFromError,
  toAIConfigUiError
} from "./ai-config-helpers";
import type { AIConfigUiError, AIPageState } from "./ai-config-types";

type ProviderTask = TaskAcceptedDto | RuntimeTaskDto;

type ProviderConfigState = {
  providers: ProviderDto[];
  models: ModelProfileDto[];
  totalKnown: number | null;
  search: string;
  healthFilter: ProviderHealthStatus | "";
  selectedProviderId: string | null;
  state: AIPageState;
  error: AIConfigUiError | null;
  feedback: string | null;
  task: ProviderTask | null;
  taskOwnerId: string | null;
  busyKey: string | null;
};

let loadController: AbortController | null = null;
let loadSequence = 0;

export const useProviderConfigStore = defineStore("p0-ai-provider-config", {
  state: (): ProviderConfigState => ({
    providers: [],
    models: [],
    totalKnown: null,
    search: "",
    healthFilter: "",
    selectedProviderId: null,
    state: "idle",
    error: null,
    feedback: null,
    task: null,
    taskOwnerId: null,
    busyKey: null
  }),
  getters: {
    selectedProvider(state): ProviderDto | null {
      return state.providers.find(
        (provider) => provider.id === state.selectedProviderId
      ) ?? null;
    },
    filteredProviders(state): ProviderDto[] {
      const search = state.search.trim().toLocaleLowerCase();
      return state.providers.filter((provider) => {
        const matchesSearch = !search
          || provider.name.toLocaleLowerCase().includes(search)
          || provider.baseUrl.toLocaleLowerCase().includes(search);
        const matchesHealth = !state.healthFilter
          || provider.healthStatus === state.healthFilter;
        return matchesSearch && matchesHealth;
      });
    },
    hasFilters(state): boolean {
      return Boolean(state.search.trim() || state.healthFilter);
    }
  },
  actions: {
    async load(): Promise<void> {
      const sequence = ++loadSequence;
      loadController?.abort();
      loadController = new AbortController();
      if (!this.providers.length) this.state = "loading";
      this.error = null;
      try {
        const options = { signal: loadController.signal };
        const [providers, models] = await Promise.all([
          listProviderProfiles({ limit: 200 }, options),
          listModelProfiles({ limit: 200 }, options)
        ]);
        if (sequence !== loadSequence) return;
        this.providers = providers.data.items;
        this.models = models.data.items;
        this.totalKnown = providers.data.totalKnown;
        if (
          this.selectedProviderId
          && !this.providers.some((item) => item.id === this.selectedProviderId)
        ) {
          this.selectedProviderId = null;
        }
        this.recomputeState();
      } catch (error) {
        if (isRuntimeRequestAborted(error) || sequence !== loadSequence) return;
        this.fail(error, "Provider 列表加载失败，请稍后重试。");
      } finally {
        if (sequence === loadSequence) loadController = null;
      }
    },

    recomputeState(): void {
      if (this.error) {
        this.state = pageStateFromError(this.error);
      } else if (
        this.task
        && ["queued", "running", "cancelling"].includes(this.task.status)
      ) {
        this.state = "waiting_external";
      } else if (!this.providers.length) {
        this.state = "first_use";
      } else if (!this.filteredProviders.length && this.hasFilters) {
        this.state = "filtered_empty";
      } else {
        this.state = "ready";
      }
    },

    modelsForProvider(providerId: string): ModelProfileDto[] {
      return this.models.filter(
        (model) => model.providerProfileId === providerId
      );
    },

    selectProvider(providerId: string | null): void {
      this.selectedProviderId = providerId;
    },

    clearFilters(): void {
      this.search = "";
      this.healthFilter = "";
      this.recomputeState();
    },

    async updateProvider(
      provider: ProviderDto,
      input: ProviderPatchInput
    ): Promise<boolean> {
      return this.runMutation(`provider-update:${provider.id}`, async () => {
        await patchProviderProfile(provider.id, input, {
          expectedRevision: provider.revision
        });
        this.feedback = "Provider 配置已更新，相关路由将重新校验。";
        await this.load();
      });
    },

    async runCheck(provider: ProviderDto): Promise<boolean> {
      return this.runMutation(`provider-check:${provider.id}`, async () => {
        const result = await startProviderCheck(
          provider.id,
          { force: true },
          { idempotencyKey: createAIOperationKey("provider-check", provider.id) }
        );
        this.task = result.data;
        this.taskOwnerId = provider.id;
        this.feedback = "Provider 连接检查已提交。";
        this.recomputeState();
      });
    },

    async discoverModels(provider: ProviderDto): Promise<boolean> {
      return this.runMutation(`model-discovery:${provider.id}`, async () => {
        const result = await startProviderModelDiscovery(
          provider.id,
          { replaceMissing: false },
          { idempotencyKey: createAIOperationKey("model-discovery", provider.id) }
        );
        this.task = result.data;
        this.taskOwnerId = provider.id;
        this.feedback = "模型发现任务已提交，现有模型不会被静默删除。";
        this.recomputeState();
      });
    },

    async refreshTask(): Promise<void> {
      const taskId = this.task?.taskId;
      if (!taskId) return;
      try {
        const result = await getSystemTask(taskId);
        this.task = result.data;
        if (["completed", "failed"].includes(result.data.status)) {
          await this.load();
        }
        this.recomputeState();
      } catch (error) {
        this.fail(error, "Provider 任务状态读取失败。");
      }
    },

    async cancelTask(): Promise<void> {
      const task = this.task;
      if (!task?.cancellable) return;
      try {
        const result = await cancelSystemTask(task.taskId, {
          idempotencyKey: createAIOperationKey("provider-task-cancel", task.taskId)
        });
        this.task = result.data;
        this.feedback = "取消请求已提交，等待 Runtime 确认终态。";
        this.recomputeState();
      } catch (error) {
        this.fail(error, "Provider 任务取消失败。");
      }
    },

    clearFeedback(): void {
      this.feedback = null;
      this.error = null;
      this.recomputeState();
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
        this.fail(error, "Provider 操作失败，请根据提示重试。");
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
