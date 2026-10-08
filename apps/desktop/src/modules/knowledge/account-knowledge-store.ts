import { defineStore } from "pinia";

import {
  getAccountBrandKit,
  getAccountKnowledge,
  getAccountPositioning,
  getAccountPositioningVersion,
  listAccountKnowledgeSources
} from "@/app/runtime-client/account-knowledge";
import { isRuntimeRequestAborted } from "@/app/runtime-client/core";
import { getAccountTask } from "@/app/runtime-client/tasks";
import type {
  KnowledgeSourceInput,
  KnowledgeSourceDto,
  PositioningVersionDto
} from "@/types/runtime/account-knowledge";
import type { AccountControlledFile } from "@/app/controlled-files/types";

import {
  logKnowledgeError,
  toKnowledgeUiError
} from "./account-knowledge-helpers";
import {
  applyIndexTaskState,
  createAccountKnowledgeCache,
  knowledgeSourceCount,
  sameRules,
  setRulesBaseline,
  toRulesDraft
} from "./account-knowledge-cache";
import {
  activatePositioningOperation,
  addSourceOperation,
  createPositioningOperation,
  removeSourceOperation,
  saveRulesOperation,
  sourceInputFromCache,
  startIndexOperation
} from "./account-knowledge-operations";
import {
  emptyPositioningDraft,
  emptyKnowledgeSourceDraft,
  type AccountKnowledgeCache,
  type KnowledgeRulesDraft,
  type KnowledgeSourceDraft,
  type KnowledgeSourceFilters,
  type PositioningDraft
} from "./account-knowledge-types";
import { toPositioningDraft } from "./positioning-view-helpers";

type AccountKnowledgeState = {
  cacheByAccount: Record<string, AccountKnowledgeCache>;
};

const loadControllers = new Map<string, AbortController>();
const loadSequences = new Map<string, number>();
const positioningDetailControllers = new Map<string, AbortController>();
const positioningDetailSequences = new Map<string, number>();

export const useAccountKnowledgeStore = defineStore("p0-account-knowledge", {
  state: (): AccountKnowledgeState => ({
    cacheByAccount: Object.create(null) as Record<string, AccountKnowledgeCache>
  }),
  actions: {
    cache(accountId: string): AccountKnowledgeCache {
      if (!this.cacheByAccount[accountId]) {
        this.cacheByAccount[accountId] = createAccountKnowledgeCache(accountId);
      }
      return this.cacheByAccount[accountId];
    },
    async load(accountId: string, filters?: KnowledgeSourceFilters): Promise<void> {
      const cache = this.cache(accountId);
      const sequence = (loadSequences.get(accountId) ?? 0) + 1;
      loadSequences.set(accountId, sequence);
      loadControllers.get(accountId)?.abort();
      const controller = new AbortController();
      loadControllers.set(accountId, controller);
      if (filters) cache.sourceFilters = { ...filters };
      if (!cache.positioning || !cache.knowledge || !cache.brandKit) {
        cache.pageState = "loading";
      }
      cache.sourceState = "loading";
      cache.error = null;

      try {
        const options = { signal: controller.signal };
        const query = {
          kind: cache.sourceFilters.kind || undefined,
          status: cache.sourceFilters.status || undefined,
          limit: 200
        };
        const [positioning, knowledge, sources, brandKit] = await Promise.all([
          getAccountPositioning(accountId, options),
          getAccountKnowledge(accountId, options),
          listAccountKnowledgeSources(accountId, query, options),
          getAccountBrandKit(accountId, options)
        ]);
        if (loadSequences.get(accountId) !== sequence) return;
        cache.positioning = positioning.data;
        if (
          cache.positioningDetailVersion !== null
          && !positioning.data.versions.some(
            (item) => item.version === cache.positioningDetailVersion
          )
        ) {
          this.closePositioningDetail(accountId);
          cache.feedback = "所选定位版本已不可用，版本列表已刷新。";
        }
        cache.knowledge = knowledge.data;
        cache.sources = sources.data.items;
        cache.sourceTotalKnown = sources.data.totalKnown;
        cache.brandKit = brandKit.data;
        if (!cache.rulesDirty) {
          setRulesBaseline(cache, toRulesDraft(knowledge.data.rules));
        }
        await this.refreshIndexTask(accountId, controller.signal);
        this.recomputeState(accountId);
        const activeVersion = positioning.data.activeVersion;
        if (
          activeVersion
          && !cache.positioningDetailOpen
          && cache.positioningDetail?.version !== activeVersion
        ) {
          void this.preloadPositioningDetail(accountId, activeVersion);
        }
      } catch (error) {
        if (
          isRuntimeRequestAborted(error)
          || loadSequences.get(accountId) !== sequence
        ) return;
        this.setError(accountId, error, "定位与知识加载失败，请稍后重试。");
        cache.pageState = "error";
        cache.sourceState = "error";
      } finally {
        if (loadControllers.get(accountId) === controller) {
          loadControllers.delete(accountId);
        }
      }
    },
    async refreshIndexTask(accountId: string, signal?: AbortSignal): Promise<void> {
      const cache = this.cache(accountId);
      if (!cache.indexTaskId) return;
      try {
        const result = await getAccountTask(accountId, cache.indexTaskId, { signal });
        applyIndexTaskState(cache, result.data, result.requestId);
      } catch (error) {
        if (isRuntimeRequestAborted(error)) return;
        this.setError(accountId, error, "索引任务状态读取失败，内容数据仍可继续使用。");
      }
    },
    openPositioningEditor(accountId: string): void {
      const cache = this.cache(accountId);
      cache.positioningEditorOpen = true;
      cache.positioningEditorMode = { kind: "create" };
      cache.positioningDraft = emptyPositioningDraft();
      cache.positioningDirty = false;
    },
    closePositioningEditor(accountId: string): void {
      const cache = this.cache(accountId);
      cache.positioningEditorOpen = false;
      cache.positioningEditorMode = { kind: "create" };
      cache.positioningDraft = emptyPositioningDraft();
      cache.positioningDirty = false;
    },

    async openPositioningDetail(
      accountId: string,
      version: number,
      force = false
    ): Promise<boolean> {
      return this.loadPositioningDetail(accountId, version, force, true);
    },

    async preloadPositioningDetail(
      accountId: string,
      version: number
    ): Promise<boolean> {
      return this.loadPositioningDetail(accountId, version, false, false);
    },

    async loadPositioningDetail(
      accountId: string,
      version: number,
      force: boolean,
      openPanel: boolean
    ): Promise<boolean> {
      const cache = this.cache(accountId);
      if (openPanel) cache.positioningDetailOpen = true;
      cache.positioningDetailVersion = version;
      if (
        !force
        && cache.positioningDetail?.version === version
        && cache.positioningDetailState === "ready"
      ) {
        return true;
      }
      const sequence = (positioningDetailSequences.get(accountId) ?? 0) + 1;
      positioningDetailSequences.set(accountId, sequence);
      positioningDetailControllers.get(accountId)?.abort();
      const controller = new AbortController();
      positioningDetailControllers.set(accountId, controller);
      cache.positioningDetailState = "loading";
      cache.positioningDetailError = null;

      try {
        const result = await getAccountPositioningVersion(
          accountId,
          version,
          { signal: controller.signal }
        );
        if (
          positioningDetailSequences.get(accountId) !== sequence
          || cache.positioningDetailVersion !== version
        ) {
          return false;
        }
        cache.positioningDetail = result.data;
        cache.positioningDetailState = "ready";
        return true;
      } catch (error) {
        if (
          isRuntimeRequestAborted(error)
          || positioningDetailSequences.get(accountId) !== sequence
        ) {
          return false;
        }
        logKnowledgeError("定位版本详情读取失败。", error);
        cache.positioningDetail = null;
        cache.positioningDetailState = "error";
        cache.positioningDetailError = toKnowledgeUiError(
          error,
          "定位版本详情读取失败，请稍后重试。"
        );
        return false;
      } finally {
        if (positioningDetailControllers.get(accountId) === controller) {
          positioningDetailControllers.delete(accountId);
        }
      }
    },

    closePositioningDetail(accountId: string): void {
      positioningDetailControllers.get(accountId)?.abort();
      positioningDetailControllers.delete(accountId);
      const cache = this.cache(accountId);
      cache.positioningDetailOpen = false;
      cache.positioningDetailError = null;
      if (cache.positioningDetailState === "loading") {
        cache.positioningDetailState = cache.positioningDetail
          ? "ready"
          : "idle";
      }
    },

    async editFromPositioningVersion(
      accountId: string,
      version: number
    ): Promise<boolean> {
      const cache = this.cache(accountId);
      if (
        cache.positioningDetail?.version !== version
        || cache.positioningDetailState !== "ready"
      ) {
        const loaded = await this.openPositioningDetail(accountId, version);
        if (!loaded) return false;
      }
      const detail = cache.positioningDetail;
      if (!detail || detail.version !== version) return false;
      cache.positioningDraft = toPositioningDraft(detail);
      cache.positioningEditorMode = {
        kind: "fork",
        sourceVersion: version
      };
      cache.positioningEditorOpen = true;
      cache.positioningDirty = false;
      this.closePositioningDetail(accountId);
      return true;
    },

    updatePositioningDraft(
      accountId: string,
      field: keyof PositioningDraft,
      value: string
    ): void {
      const cache = this.cache(accountId);
      cache.positioningDraft[field] = value;
      cache.positioningDirty = true;
    },
    updateRulesDraft(
      accountId: string,
      field: keyof KnowledgeRulesDraft,
      value: string
    ): void {
      const cache = this.cache(accountId);
      cache.rulesDraft[field] = value;
      cache.rulesDirty = !sameRules(cache.rulesDraft, cache.rulesBaseline);
    },
    openSourceEditor(accountId: string): void {
      const cache = this.cache(accountId);
      cache.sourceEditorOpen = true;
      cache.sourceDirty = false;
    },

    updateSourceDraft<K extends keyof KnowledgeSourceDraft>(
      accountId: string,
      field: K,
      value: KnowledgeSourceDraft[K]
    ): void {
      const cache = this.cache(accountId);
      cache.sourceDraft[field] = value;
      cache.sourceDirty = true;
    },

    closeSourceEditor(accountId: string): void {
      const cache = this.cache(accountId);
      cache.sourceEditorOpen = false;
      cache.sourceDraft = emptyKnowledgeSourceDraft();
      cache.sourceDirty = false;
    },

    applyControlledFileSelection(
      accountId: string,
      file: AccountControlledFile
    ): void {
      const cache = this.cache(accountId);
      cache.sourceEditorOpen = true;
      cache.sourceDraft.mode = "file";
      cache.sourceDraft.controlledFileRef = file.fileRef;
      cache.sourceDraft.controlledFileName = file.displayName;
      cache.sourceDraft.controlledFileKind = file.kind;
      cache.sourceDraft.controlledFileSize = file.size;
      if (!cache.sourceDraft.title.trim()) {
        cache.sourceDraft.title = file.displayName;
      }
      cache.sourceDirty = true;
      cache.error = null;
    },

    prepareControlledFileRecovery(
      accountId: string,
      source: KnowledgeSourceDto
    ): void {
      const cache = this.cache(accountId);
      cache.sourceEditorOpen = true;
      cache.sourceDraft = {
        ...emptyKnowledgeSourceDraft(),
        mode: "file",
        title: source.title
      };
      cache.sourceDirty = true;
      cache.feedback = "请重新选择授权文件；旧来源和历史快照会保留。";
    },
    async createPositioning(accountId: string): Promise<boolean> {
      const cache = this.cache(accountId);
      const created: { value: PositioningVersionDto | null } = {
        value: null
      };
      const succeeded = await this.runMutation(
        accountId,
        "positioning-create",
        async () => {
          created.value = await createPositioningOperation(accountId, cache);
          cache.positioningDirty = false;
          cache.positioningEditorOpen = false;
          cache.positioningEditorMode = { kind: "create" };
          cache.positioningDraft = emptyPositioningDraft();
          cache.feedback = "定位草稿版本已创建。";
          await this.load(accountId);
        }
      );
      if (succeeded && created.value) {
        cache.positioningDetail = created.value;
        cache.positioningDetailVersion = created.value.version;
        cache.positioningDetailState = "ready";
        cache.positioningDetailError = null;
        cache.positioningDetailOpen = true;
      }
      return succeeded;
    },

    async activatePositioning(accountId: string, version: number): Promise<boolean> {
      const cache = this.cache(accountId);
      return this.runMutation(accountId, `positioning-activate:${version}`, async () => {
        await activatePositioningOperation(accountId, cache, version);
        cache.feedback = `定位版本 v${version} 已激活。`;
        await this.load(accountId);
        if (cache.positioningDetailOpen) {
          await this.openPositioningDetail(
            accountId,
            cache.positioningDetailVersion ?? version,
            true
          );
        }
      });
    },

    async saveRules(accountId: string): Promise<boolean> {
      const cache = this.cache(accountId);
      return this.runMutation(accountId, "rules-save", async () => {
        const knowledge = await saveRulesOperation(accountId, cache);
        cache.knowledge = knowledge;
        setRulesBaseline(cache, toRulesDraft(knowledge.rules));
        cache.feedback = "知识规则已保存。";
        this.recomputeState(accountId);
      });
    },

    async addSource(accountId: string, input: KnowledgeSourceInput): Promise<boolean> {
      const cache = this.cache(accountId);
      return this.runMutation(accountId, "source-add", async () => {
        await addSourceOperation(accountId, input);
        this.closeSourceEditor(accountId);
        cache.feedback = "知识来源已添加，提交索引后才会进入可用状态。";
        await this.load(accountId);
      });
    },

    async removeSource(accountId: string, sourceId: string): Promise<boolean> {
      const cache = this.cache(accountId);
      return this.runMutation(accountId, `source-remove:${sourceId}`, async () => {
        await removeSourceOperation(accountId, cache, sourceId);
        cache.feedback = "知识来源已移除，原始证据与快照不会被覆盖。";
        await this.load(accountId);
      });
    },

    async startIndex(accountId: string, sourceIds?: string[]): Promise<boolean> {
      const cache = this.cache(accountId);
      return this.runMutation(accountId, "knowledge-index", async () => {
        const task = await startIndexOperation(accountId, sourceIds);
        cache.indexTaskId = task.taskId;
        cache.indexTask = null;
        cache.feedback = "索引任务已提交，可刷新查看最新状态。";
        cache.pageState = "waiting";
        cache.sourceState = "waiting";
      });
    },

    async applyFilters(
      accountId: string,
      filters: KnowledgeSourceFilters
    ): Promise<void> {
      await this.load(accountId, filters);
    },

    hasUnsaved(accountId: string): boolean {
      const cache = this.cache(accountId);
      return cache.positioningDirty || cache.rulesDirty || cache.sourceDirty;
    },

    async saveUnsaved(accountId: string): Promise<void> {
      const cache = this.cache(accountId);
      if (cache.positioningDirty && !await this.createPositioning(accountId)) {
        throw new Error(cache.error?.message ?? "定位草稿保存失败。");
      }
      if (cache.rulesDirty && !await this.saveRules(accountId)) {
        throw new Error(cache.error?.message ?? "知识规则保存失败。");
      }
      if (cache.sourceDirty && !await this.addSourceFromDraft(accountId)) {
        throw new Error(cache.error?.message ?? "知识来源保存失败。");
      }
    },

    async addSourceFromDraft(accountId: string): Promise<boolean> {
      let input: KnowledgeSourceInput;
      try {
        input = sourceInputFromCache(this.cache(accountId));
      } catch (error) {
        this.setError(accountId, error, "知识来源不完整。");
        return false;
      }
      return this.addSource(accountId, input);
    },

    discardUnsaved(accountId: string): void {
      const cache = this.cache(accountId);
      this.closePositioningEditor(accountId);
      this.closeSourceEditor(accountId);
      setRulesBaseline(cache, cache.rulesBaseline);
      cache.feedback = "未保存修改已放弃。";
    },

    recomputeState(accountId: string): void {
      const cache = this.cache(accountId);
      const hasFilters = Boolean(cache.sourceFilters.kind || cache.sourceFilters.status);
      const taskWaiting = cache.indexTaskId && (
        !cache.indexTask
        || ["queued", "running", "cancelling"].includes(cache.indexTask.status)
      );
      const sourcesWaiting = cache.sources.some((source) =>
        source.status === "pending" || source.status === "indexing"
      ) || Boolean(
        cache.knowledge?.sourceCounts.pending
        || cache.knowledge?.sourceCounts.indexing
      );
      cache.sourceState = taskWaiting || sourcesWaiting
        ? "waiting"
        : cache.sources.length
          ? "ready"
          : hasFilters
            ? "filtered_empty"
            : "empty";
      const rulesEmpty = cache.knowledge
        ? Object.values(cache.knowledge.rules).every((value) =>
            Object.keys(value).length === 0
          )
        : true;
      const firstUse = !cache.positioning?.versions.length
        && knowledgeSourceCount(cache) === 0
        && !cache.brandKit?.active
        && rulesEmpty;
      cache.pageState = taskWaiting || sourcesWaiting
        ? "waiting"
        : firstUse
          ? "first_use"
          : knowledgeSourceCount(cache) === 0 && rulesEmpty
            ? "empty"
            : "ready";
    },

    async runMutation(
      accountId: string,
      busyKey: string,
      operation: () => Promise<void>
    ): Promise<boolean> {
      const cache = this.cache(accountId);
      cache.busyKey = busyKey;
      cache.error = null;
      try {
        await operation();
        return true;
      } catch (error) {
        this.setError(accountId, error, "定位与知识操作失败，请根据提示重试。");
        return false;
      } finally {
        if (cache.busyKey === busyKey) cache.busyKey = null;
      }
    },

    setError(accountId: string, error: unknown, fallback: string): void {
      logKnowledgeError(fallback, error);
      this.cache(accountId).error = toKnowledgeUiError(error, fallback);
    },

    clearFeedback(accountId: string): void {
      const cache = this.cache(accountId);
      cache.feedback = null;
      cache.error = null;
    }
  }
});
