import { defineStore } from "pinia";

import {
  activateAccountAIRecipeVersion,
  createAccountAIRecipeVersion,
  getAccountAIRecipe,
  listAccountAIRecipeVersions,
  validateAccountAIRecipeVersion
} from "@/app/runtime-client/account-ai-recipe";
import { isRuntimeRequestAborted } from "@/app/runtime-client/core";
import { listCompositionTemplates } from "@/app/runtime-client/ai-system";
import type { AccountAIRecipeVersionDto } from "@/types/runtime/account-ai-recipe";
import {
  createAIOperationKey,
  logAIConfigError,
  pageStateFromError,
  toAIConfigUiError
} from "@/modules/system/ai-config/ai-config-helpers";

import {
  createRecipeCache,
  emptyRecipeDraft,
  recipeDraftFromVersion,
  recipeInputFromDraft
} from "./account-ai-recipe-helpers";
import type {
  AccountAIRecipeCache,
  AccountAIRecipeDraft
} from "./account-ai-recipe-types";

type AccountAIRecipeState = {
  cacheByAccount: Record<string, AccountAIRecipeCache>;
  visibleAccountId: string | null;
  visibleGeneration: number;
};

const loadControllers = new Map<string, AbortController>();
const loadSequences = new Map<string, number>();

export const useAccountAIRecipeStore = defineStore("p0-account-ai-recipe", {
  state: (): AccountAIRecipeState => ({
    cacheByAccount: Object.create(null) as Record<string, AccountAIRecipeCache>,
    visibleAccountId: null,
    visibleGeneration: 0
  }),
  actions: {
    cache(accountId: string): AccountAIRecipeCache {
      if (!this.cacheByAccount[accountId]) {
        this.cacheByAccount[accountId] = createRecipeCache(accountId);
      }
      return this.cacheByAccount[accountId];
    },

    activateAccount(accountId: string): AccountAIRecipeCache {
      if (this.visibleAccountId !== accountId) {
        this.visibleAccountId = accountId;
        this.visibleGeneration += 1;
      }
      return this.cache(accountId);
    },

    async load(accountId: string): Promise<void> {
      const cache = this.activateAccount(accountId);
      const sequence = (loadSequences.get(accountId) ?? 0) + 1;
      loadSequences.set(accountId, sequence);
      loadControllers.get(accountId)?.abort();
      const controller = new AbortController();
      loadControllers.set(accountId, controller);
      if (!cache.recipe) cache.state = "loading";
      cache.error = null;
      try {
        const options = { signal: controller.signal };
        const [recipe, versions, templates] = await Promise.all([
          getAccountAIRecipe(accountId, options),
          listAccountAIRecipeVersions(accountId, { limit: 200 }, options),
          listCompositionTemplates({ status: "active", limit: 200 }, options)
        ]);
        if (
          loadSequences.get(accountId) !== sequence
        ) {
          return;
        }
        cache.recipe = recipe.data;
        cache.versions = versions.data.items;
        cache.templates = templates.data.items.filter(
          (template) => template.activeVersionId !== null
        );
        if (
          cache.selectedVersion !== null
          && !cache.versions.some(
            (version) => version.version === cache.selectedVersion
          )
        ) {
          cache.selectedVersion = null;
        }
        this.recomputeState(accountId);
      } catch (error) {
        if (
          isRuntimeRequestAborted(error)
          || loadSequences.get(accountId) !== sequence
        ) {
          return;
        }
        this.fail(accountId, error, "账号 AI Recipe 加载失败。");
      } finally {
        if (loadControllers.get(accountId) === controller) {
          loadControllers.delete(accountId);
        }
      }
    },

    recomputeState(accountId: string): void {
      const cache = this.cache(accountId);
      if (cache.error) {
        cache.state = pageStateFromError(cache.error);
      } else if (cache.busyKey) {
        cache.state = "waiting_external";
      } else if (!cache.versions.length) {
        cache.state = "first_use";
      } else if (
        cache.recipe?.activeVersion === null
        || cache.versions.some(
          (version) =>
            version.version === cache.recipe?.activeVersion
            && version.validationStatus !== "valid"
        )
      ) {
        cache.state = "dependency_blocked";
      } else {
        cache.state = "ready";
      }
    },

    beginCreateVersion(
      accountId: string,
      source?: AccountAIRecipeVersionDto | null
    ): void {
      const cache = this.cache(accountId);
      cache.draft = source
        ? recipeDraftFromVersion(source)
        : emptyRecipeDraft();
      cache.editorOpen = true;
      cache.dirty = false;
      cache.error = null;
    },

    selectVersion(accountId: string, version: number): void {
      this.cache(accountId).selectedVersion = version;
    },

    updateDraft<K extends keyof AccountAIRecipeDraft>(
      accountId: string,
      field: K,
      value: AccountAIRecipeDraft[K]
    ): void {
      const cache = this.cache(accountId);
      cache.draft[field] = value;
      cache.dirty = true;
    },

    async saveDraft(accountId: string): Promise<boolean> {
      const cache = this.cache(accountId);
      const revision = cache.recipe?.revision;
      if (!revision) {
        this.fail(
          accountId,
          new Error("Recipe 修订尚未加载。"),
          "请先刷新账号 AI Recipe。"
        );
        return false;
      }
      let input;
      try {
        input = recipeInputFromDraft(cache.draft);
      } catch (error) {
        this.fail(accountId, error, "Recipe 配置格式无效。");
        return false;
      }
      return this.runMutation(accountId, "recipe-save", async () => {
        const result = await createAccountAIRecipeVersion(accountId, input, {
          expectedRevision: revision,
          idempotencyKey: createAIOperationKey(
            "account-recipe-version-create",
            accountId
          )
        });
        this.applyAccountRevision(accountId, result.meta?.revision);
        cache.selectedVersion = result.data.version;
        cache.editorOpen = false;
        cache.dirty = false;
        cache.feedback = `AI Recipe v${result.data.version} 已创建，激活前必须验证。`;
        await this.load(accountId);
      });
    },

    async validateVersion(accountId: string, version: number): Promise<boolean> {
      const cache = this.cache(accountId);
      return this.runMutation(accountId, `recipe-validate:${version}`, async () => {
        const result = await validateAccountAIRecipeVersion(
          accountId,
          version,
          {
            idempotencyKey: createAIOperationKey(
              "account-recipe-validate",
              accountId
            )
          }
        );
        this.applyAccountRevision(accountId, result.meta?.revision);
        cache.validation = result.data;
        cache.selectedVersion = version;
        cache.feedback =
          cache.validation.validationStatus === "valid"
            ? `AI Recipe v${version} 验证通过。`
            : `AI Recipe v${version} 仍有依赖问题。`;
        await this.load(accountId);
      });
    },

    async activateVersion(accountId: string, version: number): Promise<boolean> {
      const cache = this.cache(accountId);
      const revision = cache.recipe?.revision;
      if (!revision) return false;
      return this.runMutation(accountId, `recipe-activate:${version}`, async () => {
        const result = await activateAccountAIRecipeVersion(accountId, version, {
          expectedRevision: revision,
          idempotencyKey: createAIOperationKey(
            "account-recipe-activate",
            accountId
          )
        });
        this.applyAccountRevision(accountId, result.meta?.revision);
        cache.feedback = `AI Recipe v${version} 已激活。`;
        await this.load(accountId);
      });
    },

    discardDraft(accountId: string): void {
      const cache = this.cache(accountId);
      cache.editorOpen = false;
      cache.dirty = false;
      cache.draft = emptyRecipeDraft();
    },

    closeEditor(accountId: string): void {
      this.discardDraft(accountId);
    },

    async saveUnsaved(accountId: string): Promise<void> {
      const cache = this.cache(accountId);
      if (cache.dirty && !await this.saveDraft(accountId)) {
        throw new Error(cache.error?.message ?? "账号 AI Recipe 保存失败。");
      }
    },

    clearFeedback(accountId: string): void {
      const cache = this.cache(accountId);
      cache.feedback = null;
      cache.error = null;
      this.recomputeState(accountId);
    },

    applyAccountRevision(
      accountId: string,
      revision: number | undefined
    ): void {
      const cache = this.cache(accountId);
      if (
        !cache.recipe
        || revision === undefined
        || !Number.isInteger(revision)
        || revision < 1
      ) {
        return;
      }
      cache.recipe = {
        ...cache.recipe,
        revision
      };
    },

    async runMutation(
      accountId: string,
      busyKey: string,
      operation: () => Promise<void>
    ): Promise<boolean> {
      const cache = this.cache(accountId);
      cache.busyKey = busyKey;
      cache.error = null;
      this.recomputeState(accountId);
      try {
        await operation();
        return true;
      } catch (error) {
        this.fail(accountId, error, "账号 AI Recipe 操作失败。");
        return false;
      } finally {
        if (cache.busyKey === busyKey) cache.busyKey = null;
        this.recomputeState(accountId);
      }
    },

    fail(accountId: string, error: unknown, fallback: string): void {
      logAIConfigError(fallback, error);
      const cache = this.cache(accountId);
      cache.error = toAIConfigUiError(error, fallback);
      cache.state = pageStateFromError(cache.error);
    }
  }
});
