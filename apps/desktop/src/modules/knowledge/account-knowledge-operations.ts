import {
  activateAccountPositioningVersion,
  createAccountKnowledgeSource,
  createAccountPositioningVersion,
  removeAccountKnowledgeSource,
  startAccountKnowledgeIndex,
  updateAccountKnowledgeRules
} from "@/app/runtime-client/account-knowledge";
import type {
  KnowledgeDto,
  KnowledgeSourceInput,
  PositioningVersionDto
} from "@/types/runtime/account-knowledge";
import type { TaskAcceptedDto } from "@/types/runtime/tasks";

import { parseRules } from "./account-knowledge-cache";
import { createKnowledgeOperationKey } from "./account-knowledge-helpers";
import {
  toPositioningInput,
  type AccountKnowledgeCache
} from "./account-knowledge-types";

export async function createPositioningOperation(
  accountId: string,
  cache: AccountKnowledgeCache
): Promise<PositioningVersionDto> {
  if (!cache.positioning) throw new Error("账号定位尚未加载。");
  const input = toPositioningInput(cache.positioningDraft);
  if (
    !input.audience.description
    || !input.tone.description
    || !input.contentPillars.length
  ) {
    throw new Error("目标受众、内容支柱和表达风格不能为空。");
  }
  const result = await createAccountPositioningVersion(accountId, input, {
    expectedRevision: cache.positioning.revision,
    idempotencyKey: createKnowledgeOperationKey("positioning-create", accountId)
  });
  return result.data;
}

export async function activatePositioningOperation(
  accountId: string,
  cache: AccountKnowledgeCache,
  version: number
): Promise<void> {
  if (!cache.positioning) throw new Error("账号定位尚未加载。");
  await activateAccountPositioningVersion(accountId, version, {
    expectedRevision: cache.positioning.revision,
    idempotencyKey: createKnowledgeOperationKey("positioning-activate", accountId)
  });
}

export async function saveRulesOperation(
  accountId: string,
  cache: AccountKnowledgeCache
): Promise<KnowledgeDto> {
  if (!cache.knowledge) throw new Error("账号知识库尚未加载。");
  const result = await updateAccountKnowledgeRules(
    accountId,
    parseRules(cache.rulesDraft),
    { expectedRevision: cache.knowledge.revision }
  );
  return result.data;
}

export async function addSourceOperation(
  accountId: string,
  input: KnowledgeSourceInput
): Promise<void> {
  if (input.sourceMode === "file") {
    throw new Error("受控文件桥将在 P0-F 接入，当前不能提交本地路径。");
  }
  await createAccountKnowledgeSource(accountId, input, {
    idempotencyKey: createKnowledgeOperationKey("knowledge-source", accountId)
  });
}

export async function removeSourceOperation(
  accountId: string,
  cache: AccountKnowledgeCache,
  sourceId: string
): Promise<void> {
  if (!cache.knowledge) throw new Error("账号知识库尚未加载。");
  await removeAccountKnowledgeSource(accountId, sourceId, {
    expectedRevision: cache.knowledge.revision,
    idempotencyKey: createKnowledgeOperationKey("knowledge-remove", accountId)
  });
}

export async function startIndexOperation(
  accountId: string,
  sourceIds?: string[]
): Promise<TaskAcceptedDto> {
  const result = await startAccountKnowledgeIndex(
    accountId,
    sourceIds?.length ? { sourceIds } : {},
    { idempotencyKey: createKnowledgeOperationKey("knowledge-index", accountId) }
  );
  return result.data;
}

export function sourceInputFromCache(
  cache: AccountKnowledgeCache
): KnowledgeSourceInput {
  const draft = cache.sourceDraft;
  if (!draft.title.trim()) throw new Error("来源标题不能为空。");
  if (draft.mode === "text") {
    if (!draft.text.trim()) throw new Error("文本内容不能为空。");
    return {
      kind: "text",
      sourceMode: "text",
      title: draft.title.trim(),
      text: draft.text.trim()
    };
  }
  if (draft.mode === "url") {
    if (!draft.url.trim()) throw new Error("来源网址不能为空。");
    return {
      kind: "reference",
      sourceMode: "url",
      title: draft.title.trim(),
      url: draft.url.trim()
    };
  }
  throw new Error("受控文件桥将在 P0-F 接入，当前不能提交本地路径。");
}
