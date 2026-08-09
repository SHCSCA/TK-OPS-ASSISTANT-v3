import type { AccountAIRecipeVersionDto } from "@/types/runtime/account-ai-recipe";
import {
  parseJsonObject,
  prettyJson
} from "@/modules/system/ai-config/ai-config-helpers";

import type {
  AccountAIRecipeCache,
  AccountAIRecipeDraft
} from "./account-ai-recipe-types";

export function createRecipeCache(accountId: string): AccountAIRecipeCache {
  return {
    accountId,
    recipe: null,
    versions: [],
    templates: [],
    selectedVersion: null,
    validation: null,
    draft: emptyRecipeDraft(),
    editorOpen: false,
    dirty: false,
    state: "idle",
    error: null,
    feedback: null,
    busyKey: null
  };
}

export function emptyRecipeDraft(): AccountAIRecipeDraft {
  return {
    name: "",
    routeOverrides: "{}",
    visualStyle: "{}",
    voiceProfileRef: "",
    compositionTemplateRef: "",
    costPolicy: "{}",
    fallbackPolicy: "{}"
  };
}

export function recipeDraftFromVersion(
  version: AccountAIRecipeVersionDto
): AccountAIRecipeDraft {
  return {
    name: version.name,
    routeOverrides: prettyJson(version.routeOverrides),
    visualStyle: prettyJson(version.visualStyle),
    voiceProfileRef: version.voiceProfileRef ?? "",
    compositionTemplateRef: version.compositionTemplateRef ?? "",
    costPolicy: prettyJson(version.costPolicy),
    fallbackPolicy: prettyJson(version.fallbackPolicy)
  };
}

export function recipeInputFromDraft(draft: AccountAIRecipeDraft) {
  return {
    name: draft.name.trim(),
    routeOverrides: parseJsonObject(draft.routeOverrides, "Route 覆盖"),
    visualStyle: parseJsonObject(draft.visualStyle, "视觉风格"),
    voiceProfileRef: draft.voiceProfileRef.trim() || null,
    compositionTemplateRef: draft.compositionTemplateRef.trim() || null,
    costPolicy: parseJsonObject(draft.costPolicy, "成本策略"),
    fallbackPolicy: parseJsonObject(draft.fallbackPolicy, "回退策略")
  };
}
