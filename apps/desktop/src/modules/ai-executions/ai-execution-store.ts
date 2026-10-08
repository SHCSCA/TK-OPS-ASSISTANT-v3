import { defineStore } from "pinia";

import {
  getAIExecution,
  getAIExecutionOutput,
  listAIExecutions
} from "@/app/runtime-client/ai-executions";
import { listAccountKnowledgeSnapshots } from "@/app/runtime-client/account-knowledge";
import { isRuntimeRequestAborted } from "@/app/runtime-client/core";
import type { KnowledgeSnapshotDto } from "@/types/runtime/account-knowledge";
import type {
  AIExecutionDetailDto,
  AIExecutionPolicyInput,
  AIExecutionPreflightDto,
  AIExecutionSummaryDto
} from "@/types/runtime/ai-executions";
import type { AIConfigUiError } from "@/modules/system/ai-config/ai-config-types";

import { executionError } from "./ai-execution-helpers";
import {
  cancelExecutionOperation,
  createExecutionOperation,
  preflightExecutionOperation,
  retryExecutionOperation
} from "./ai-execution-operations";

export type AIExecutionViewState =
  | "idle"
  | "loading"
  | "first_use"
  | "ready"
  | "error"
  | "restricted";

type AIExecutionPolicyDraft = AIExecutionPolicyInput & {
  currency: string;
  maxCostMicros: number;
};

export type AIExecutionCache = {
  accountId: string;
  state: AIExecutionViewState;
  executions: AIExecutionSummaryDto[];
  knowledgeSnapshots: KnowledgeSnapshotDto[];
  selectedKnowledgeSnapshotId: string;
  selectedExecutionId: string | null;
  detail: AIExecutionDetailDto | null;
  preflight: AIExecutionPreflightDto | null;
  outputContent: string | null;
  topic: string;
  language: string;
  targetDurationSeconds: number;
  policy: AIExecutionPolicyDraft;
  busyKey: string | null;
  error: AIConfigUiError | null;
  feedback: string | null;
};

type AIExecutionState = {
  cacheByAccount: Record<string, AIExecutionCache>;
  visibleAccountId: string | null;
  visibleGeneration: number;
};

const loadControllers = new Map<string, AbortController>();
const detailControllers = new Map<string, AbortController>();
const operationControllers = new Map<string, AbortController>();
const loadSequences = new Map<string, number>();
const detailSequences = new Map<string, number>();
const pollTimers = new Map<string, ReturnType<typeof setTimeout>>();

export const useAIExecutionStore = defineStore("p0-h-ai-executions", {
  state: (): AIExecutionState => ({
    cacheByAccount: Object.create(null) as Record<string, AIExecutionCache>,
    visibleAccountId: null,
    visibleGeneration: 0
  }),
  actions: {
    cache(accountId: string): AIExecutionCache {
      const key = executionCacheKey(accountId);
      if (!this.cacheByAccount[key]) {
        this.cacheByAccount[key] = createCache(accountId);
      }
      return this.cacheByAccount[key];
    },

    activateAccount(accountId: string): AIExecutionCache {
      if (this.visibleAccountId !== accountId) {
        const previous = this.visibleAccountId;
        if (previous) this.stopAccount(previous, true);
        this.visibleAccountId = accountId;
        this.visibleGeneration += 1;
        const next = this.cache(accountId);
        next.detail = null;
        next.outputContent = null;
      }
      return this.cache(accountId);
    },

    async load(accountId: string): Promise<void> {
      const cache = this.activateAccount(accountId);
      const generation = this.visibleGeneration;
      const sequence = (loadSequences.get(accountId) ?? 0) + 1;
      loadSequences.set(accountId, sequence);
      loadControllers.get(accountId)?.abort();
      const controller = new AbortController();
      loadControllers.set(accountId, controller);
      if (!cache.executions.length) cache.state = "loading";
      cache.error = null;
      try {
        const [executions, snapshots] = await Promise.all([
          listAIExecutions(accountId, { limit: 50 }, { signal: controller.signal }),
          listAccountKnowledgeSnapshots(
            accountId,
            { limit: 200 },
            { signal: controller.signal }
          )
        ]);
        if (!this.isCurrent(accountId, generation, sequence)) return;
        cache.executions = executions.data.items;
        cache.knowledgeSnapshots = snapshots.data.items;
        if (
          !cache.selectedKnowledgeSnapshotId
          || !cache.knowledgeSnapshots.some(
            (item) => item.id === cache.selectedKnowledgeSnapshotId
          )
        ) {
          cache.selectedKnowledgeSnapshotId = cache.knowledgeSnapshots[0]?.id ?? "";
        }
        cache.state = cache.executions.length ? "ready" : "first_use";
        const selected = cache.selectedExecutionId
          && cache.executions.some((item) => item.id === cache.selectedExecutionId)
          ? cache.selectedExecutionId
          : cache.executions[0]?.id ?? null;
        cache.selectedExecutionId = selected;
        if (selected) await this.loadDetail(accountId, selected);
      } catch (error) {
        if (isRuntimeRequestAborted(error) || !this.isVisible(accountId, generation)) return;
        cache.error = executionError(error, "AI 执行记录加载失败。");
        cache.state = cache.error.errorCode?.startsWith("LICENSE_")
          ? "restricted"
          : "error";
      } finally {
        if (loadControllers.get(accountId) === controller) {
          loadControllers.delete(accountId);
        }
      }
    },

    async loadDetail(accountId: string, executionId: string): Promise<void> {
      const cache = this.cache(accountId);
      const generation = this.visibleGeneration;
      const sequence = (detailSequences.get(accountId) ?? 0) + 1;
      detailSequences.set(accountId, sequence);
      detailControllers.get(accountId)?.abort();
      const controller = new AbortController();
      detailControllers.set(accountId, controller);
      cache.selectedExecutionId = executionId;
      cache.outputContent = null;
      try {
        const result = await getAIExecution(accountId, executionId, {
          signal: controller.signal
        });
        if (
          !this.isVisible(accountId, generation)
          || detailSequences.get(accountId) !== sequence
          || cache.selectedExecutionId !== executionId
        ) return;
        cache.detail = result.data;
        this.mergeSummary(accountId, result.data);
        if (["queued", "running", "cancelling"].includes(result.data.status)) {
          this.schedulePoll(accountId, executionId);
        } else {
          this.clearPoll(accountId);
        }
      } catch (error) {
        if (isRuntimeRequestAborted(error) || !this.isVisible(accountId, generation)) return;
        cache.error = executionError(error, "AI 执行详情加载失败。");
      } finally {
        if (detailControllers.get(accountId) === controller) {
          detailControllers.delete(accountId);
        }
      }
    },

    async runPreflight(
      accountId: string,
      accountRevision: number,
      recipeVersionId: string
    ): Promise<boolean> {
      const cache = this.cache(accountId);
      if (!this.requireInputs(cache)) return false;
      return this.runOperation(accountId, "preflight", async (signal) => {
        const result = await preflightExecutionOperation(
          accountId,
          accountRevision,
          {
            capabilityKey: "script_generation",
            knowledgeSnapshotId: cache.selectedKnowledgeSnapshotId,
            recipeVersionId,
            inputSummary: { estimatedInputUnits: estimateInputUnits(cache) },
            executionPolicy: cache.policy
          },
          signal
        );
        cache.preflight = result.data;
        cache.feedback = result.data.ready
          ? "预检通过，已冻结候选、知识与成本摘要。"
          : "预检发现阻断项，请完成修复后重新预检。";
      });
    },

    async create(
      accountId: string,
      accountRevision: number,
      recipeVersionId: string
    ): Promise<boolean> {
      const cache = this.cache(accountId);
      if (!this.requireInputs(cache)) return false;
      return this.runOperation(accountId, "create", async (signal) => {
        const result = await createExecutionOperation(
          accountId,
          accountRevision,
          {
            capabilityKey: "script_generation",
            knowledgeSnapshotId: cache.selectedKnowledgeSnapshotId,
            recipeVersionId,
            input: {
              topic: cache.topic.trim(),
              language: cache.language,
              targetDurationSeconds: cache.targetDurationSeconds
            },
            executionPolicy: cache.policy
          },
          signal
        );
        cache.preflight = null;
        cache.feedback = "真实 AI 执行已进入 Runtime 队列。";
        cache.selectedExecutionId = result.data.executionId;
        await this.load(accountId);
      });
    },

    async cancel(accountId: string, executionId: string): Promise<boolean> {
      const cache = this.cache(accountId);
      return this.runOperation(accountId, "cancel", async (signal) => {
        const result = await cancelExecutionOperation(accountId, executionId, signal);
        cache.detail = result.data;
        cache.feedback = result.data.status === "completed"
          ? result.data.completionKind === "cancelled"
            ? "执行已取消；已发送调用的费用仍以详情证据为准。"
            : "执行已进入终态，取消请求未改写既有结果。"
          : "取消请求已送达 Runtime。";
        this.mergeSummary(accountId, result.data);
        if (result.data.status === "cancelling") {
          this.schedulePoll(accountId, executionId);
        }
      });
    },

    async retry(accountId: string, executionId: string): Promise<boolean> {
      const cache = this.cache(accountId);
      return this.runOperation(accountId, "retry", async (signal) => {
        const result = await retryExecutionOperation(accountId, executionId, signal);
        cache.feedback = "已按原输入、配置和知识快照创建新执行。";
        cache.selectedExecutionId = result.data.executionId;
        await this.load(accountId);
      });
    },

    async loadOutput(
      accountId: string,
      executionId: string,
      outputId: string
    ): Promise<void> {
      const cache = this.cache(accountId);
      const generation = this.visibleGeneration;
      try {
        const result = await getAIExecutionOutput(accountId, executionId, outputId);
        if (!this.isVisible(accountId, generation)) return;
        cache.outputContent = result.data.content;
      } catch (error) {
        cache.error = executionError(error, "AI 输出读取失败。");
      }
    },

    selectKnowledgeSnapshot(accountId: string, snapshotId: string): void {
      const cache = this.cache(accountId);
      cache.selectedKnowledgeSnapshotId = snapshotId;
      cache.preflight = null;
    },

    selectExecution(accountId: string, executionId: string): void {
      void this.loadDetail(accountId, executionId);
    },

    clearFeedback(accountId: string): void {
      this.cache(accountId).feedback = null;
    },

    stopAccount(accountId: string, clearDetail = false): void {
      loadControllers.get(accountId)?.abort();
      detailControllers.get(accountId)?.abort();
      operationControllers.get(accountId)?.abort();
      this.clearPoll(accountId);
      if (clearDetail) {
        const cache = this.cache(accountId);
        cache.detail = null;
        cache.outputContent = null;
      }
    },

    clearPoll(accountId: string): void {
      const timer = pollTimers.get(accountId);
      if (timer) clearTimeout(timer);
      pollTimers.delete(accountId);
    },

    schedulePoll(accountId: string, executionId: string): void {
      this.clearPoll(accountId);
      pollTimers.set(accountId, setTimeout(() => {
        if (this.visibleAccountId === accountId) {
          void this.loadDetail(accountId, executionId);
        }
      }, 1500));
    },

    async runOperation(
      accountId: string,
      key: string,
      operation: (signal: AbortSignal) => Promise<void>
    ): Promise<boolean> {
      const cache = this.cache(accountId);
      operationControllers.get(accountId)?.abort();
      const controller = new AbortController();
      operationControllers.set(accountId, controller);
      cache.busyKey = key;
      cache.error = null;
      try {
        await operation(controller.signal);
        return true;
      } catch (error) {
        if (isRuntimeRequestAborted(error)) return false;
        cache.error = executionError(error, "AI 执行操作失败。");
        return false;
      } finally {
        if (operationControllers.get(accountId) === controller) {
          operationControllers.delete(accountId);
          cache.busyKey = null;
        }
      }
    },

    requireInputs(cache: AIExecutionCache): boolean {
      if (!cache.selectedKnowledgeSnapshotId) {
        cache.error = executionError(
          new Error("当前账号还没有知识快照。"),
          "请先创建知识快照。"
        );
        return false;
      }
      if (!cache.topic.trim()) {
        cache.error = executionError(new Error("请输入验证主题。"), "请输入验证主题。");
        return false;
      }
      return true;
    },

    mergeSummary(accountId: string, detail: AIExecutionDetailDto): void {
      const cache = this.cache(accountId);
      const index = cache.executions.findIndex((item) => item.id === detail.id);
      if (index >= 0) cache.executions.splice(index, 1, detail);
      else cache.executions.unshift(detail);
    },

    isVisible(accountId: string, generation: number): boolean {
      return this.visibleAccountId === accountId && this.visibleGeneration === generation;
    },

    isCurrent(accountId: string, generation: number, sequence: number): boolean {
      return this.isVisible(accountId, generation)
        && loadSequences.get(accountId) === sequence;
    }
  }
});

function createCache(accountId: string): AIExecutionCache {
  return {
    accountId,
    state: "idle",
    executions: [],
    knowledgeSnapshots: [],
    selectedKnowledgeSnapshotId: "",
    selectedExecutionId: null,
    detail: null,
    preflight: null,
    outputContent: null,
    topic: "",
    language: "zh-CN",
    targetDurationSeconds: 45,
    policy: {
      maxCostMicros: 50_000,
      currency: "USD"
    },
    busyKey: null,
    error: null,
    feedback: null
  };
}

function estimateInputUnits(cache: AIExecutionCache): number {
  const payload = JSON.stringify({
    topic: cache.topic,
    language: cache.language,
    targetDurationSeconds: cache.targetDurationSeconds
  });
  return Math.max(1, Math.ceil(new TextEncoder().encode(payload).length / 4));
}

function executionCacheKey(accountId: string): string {
  return `account:${accountId}:ai-executions`;
}
