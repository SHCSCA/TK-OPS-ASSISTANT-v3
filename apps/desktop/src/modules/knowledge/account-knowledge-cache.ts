import type { KnowledgeRulesInput } from "@/types/runtime/account-knowledge";
import type { RuntimeTaskDto } from "@/types/runtime/tasks";

import { parseRulesJson, stableJson } from "./account-knowledge-helpers";
import {
  emptyKnowledgeSourceDraft,
  emptyPositioningDraft,
  type AccountKnowledgeCache,
  type KnowledgeRulesDraft
} from "./account-knowledge-types";

export function createAccountKnowledgeCache(
  accountId: string
): AccountKnowledgeCache {
  const rules = toRulesDraft({
    inclusionRules: {},
    exclusionRules: {},
    citationPolicy: {}
  });
  return {
    accountId,
    pageState: "idle",
    sourceState: "empty",
    positioning: null,
    knowledge: null,
    brandKit: null,
    sources: [],
    sourceTotalKnown: null,
    sourceFilters: { kind: "", status: "" },
    positioningDraft: emptyPositioningDraft(),
    positioningEditorOpen: false,
    positioningEditorMode: { kind: "create" },
    positioningDirty: false,
    positioningDetailOpen: false,
    positioningDetailVersion: null,
    positioningDetailState: "idle",
    positioningDetail: null,
    positioningDetailError: null,
    rulesDraft: { ...rules },
    rulesBaseline: { ...rules },
    rulesDirty: false,
    sourceDraft: emptyKnowledgeSourceDraft(),
    sourceEditorOpen: false,
    sourceDirty: false,
    indexTask: null,
    indexTaskId: null,
    error: null,
    feedback: null,
    busyKey: null
  };
}

export function toRulesDraft(
  rules: KnowledgeRulesInput
): KnowledgeRulesDraft {
  return {
    inclusionRules: stableJson(rules.inclusionRules),
    exclusionRules: stableJson(rules.exclusionRules),
    citationPolicy: stableJson(rules.citationPolicy)
  };
}

export function setRulesBaseline(
  cache: AccountKnowledgeCache,
  rules: KnowledgeRulesDraft
): void {
  cache.rulesBaseline = { ...rules };
  cache.rulesDraft = { ...rules };
  cache.rulesDirty = false;
}

export function sameRules(
  left: KnowledgeRulesDraft,
  right: KnowledgeRulesDraft
): boolean {
  return Object.keys(left).every((key) =>
    left[key as keyof KnowledgeRulesDraft]
    === right[key as keyof KnowledgeRulesDraft]
  );
}

export function parseRules(
  draft: KnowledgeRulesDraft
): KnowledgeRulesInput {
  return {
    inclusionRules: parseRulesJson(draft.inclusionRules, "纳入规则"),
    exclusionRules: parseRulesJson(draft.exclusionRules, "排除规则"),
    citationPolicy: parseRulesJson(draft.citationPolicy, "引用策略")
  };
}

export function knowledgeSourceCount(cache: AccountKnowledgeCache): number {
  return Object.values(cache.knowledge?.sourceCounts ?? {})
    .reduce((total, value) => total + value, 0);
}

export function applyIndexTaskState(
  cache: AccountKnowledgeCache,
  task: RuntimeTaskDto,
  requestId: string | null
): void {
  cache.indexTask = task;
  if (task.status === "failed") {
    cache.error = {
      message: "知识索引任务失败，请修复来源后重新提交。",
      errorCode: task.errorCode,
      logId: task.logId,
      requestId,
      retryable: true
    };
  } else if (task.status === "completed") {
    cache.feedback = task.completionKind === "cancelled"
      ? "知识索引任务已取消。"
      : "知识索引任务已完成。";
  }
}
