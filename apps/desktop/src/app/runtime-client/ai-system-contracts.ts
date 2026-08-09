import {
  AI_CAPABILITY_KEYS,
  type CapabilityRouteDto,
  type CompositionTemplateDto,
  type CompositionTemplateVersionDto,
  type CredentialSummaryDto,
  type ModelCapabilityDto,
  type ModelProfileDto,
  type PromptProfileDto,
  type PromptVersionDto,
  type ProviderDto
} from "@/types/runtime/ai-system";
import type { TaskAcceptedDto } from "@/types/runtime/tasks";

import {
  assertStableResourceId,
  RuntimeError
} from "./core";

const capabilityKeys = new Set<string>(AI_CAPABILITY_KEYS);

export function providerPath(providerId: string): string {
  assertStableResourceId(providerId, "provider_id");
  return `/api/v1/system/providers/${encodeURIComponent(providerId)}`;
}

export function modelPath(modelProfileId: string): string {
  assertStableResourceId(modelProfileId, "model_profile_id");
  return `/api/v1/system/models/${encodeURIComponent(modelProfileId)}`;
}

export function routePath(capabilityKey: string): string {
  assertCapabilityKey(capabilityKey);
  return `/api/v1/system/capability-routes/${encodeURIComponent(capabilityKey)}`;
}

export function promptPath(profileKey: string): string {
  assertStableResourceId(profileKey, "profile_key");
  return `/api/v1/system/prompt-profiles/${encodeURIComponent(profileKey)}`;
}

export function templatePath(templateKey: string): string {
  assertStableResourceId(templateKey, "template_key");
  return `/api/v1/system/composition-templates/${encodeURIComponent(templateKey)}`;
}

export function versionPath(version: number): string {
  assertPositiveInteger(version, "version");
  return String(version);
}

export function withQuery<T extends object>(path: string, query: T): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query as Record<string, unknown>)) {
    if (
      typeof value === "string"
      || typeof value === "number"
      || typeof value === "boolean"
    ) {
      params.set(key, String(value));
    }
  }
  const serialized = params.toString();
  return serialized ? `${path}?${serialized}` : path;
}

export function validateProvider(data: ProviderDto): void {
  assertStableResourceId(data.id, "provider.id");
  assertPositiveInteger(data.revision, "provider.revision");
}

export function validateCredentialSummary(data: CredentialSummaryDto): void {
  if (!data.configured || !data.credentialRef || !data.maskedValue) {
    throw invalidResponse("Runtime 返回的凭据引用摘要无效。");
  }
  assertPositiveInteger(data.providerRevision, "providerRevision");
}

export function validateModel(data: ModelProfileDto): void {
  assertStableResourceId(data.id, "model.id");
  assertStableResourceId(data.providerProfileId, "model.providerProfileId");
  assertPositiveInteger(data.revision, "model.revision");
  data.capabilities.forEach(validateCapability);
}

export function validateCapability(data: ModelCapabilityDto): void {
  assertCapabilityKey(data.capabilityKey);
  if (!Number.isInteger(data.contractRevision) || data.contractRevision < 0) {
    throw invalidResponse("Runtime 返回的能力契约修订无效。");
  }
}

export function validateRoute(data: CapabilityRouteDto): void {
  assertStableResourceId(data.id, "route.id");
  assertCapabilityKey(data.capabilityKey);
  assertPositiveInteger(data.revision, "route.revision");
}

export function validatePromptProfile(data: PromptProfileDto): void {
  assertStableResourceId(data.profileKey, "prompt.profileKey");
  assertCapabilityKey(data.capabilityKey);
  assertPositiveInteger(data.revision, "prompt.revision");
  validateActiveVersionReference(
    data.activeVersion,
    data.activeVersionId,
    "prompt.activeVersionId"
  );
}

export function validatePromptVersion(data: PromptVersionDto): void {
  assertStableResourceId(data.id, "promptVersion.id");
  assertStableResourceId(data.profileKey, "promptVersion.profileKey");
  assertCapabilityKey(data.capabilityKey);
  assertPositiveInteger(data.version, "promptVersion.version");
}

export function validateCompositionTemplate(
  data: CompositionTemplateDto
): void {
  assertStableResourceId(data.templateKey, "compositionTemplate.templateKey");
  assertPositiveInteger(data.revision, "compositionTemplate.revision");
  validateActiveVersionReference(
    data.activeVersion,
    data.activeVersionId,
    "compositionTemplate.activeVersionId"
  );
}

export function validateCompositionTemplateVersion(
  data: CompositionTemplateVersionDto
): void {
  assertStableResourceId(data.id, "compositionTemplateVersion.id");
  assertStableResourceId(
    data.templateKey,
    "compositionTemplateVersion.templateKey"
  );
  assertPositiveInteger(data.version, "compositionTemplateVersion.version");
}

export function validateSystemTaskAccepted(data: TaskAcceptedDto): void {
  assertStableResourceId(data.taskId, "task.taskId");
  if (
    data.scope !== "system"
    || data.accountId !== null
    || data.status !== "queued"
  ) {
    throw invalidResponse("Runtime 返回的系统任务受理信息无效。");
  }
}

export function assertCapabilityKey(value: string): void {
  if (!capabilityKeys.has(value)) {
    throw invalidResponse("Runtime 返回了未注册的 AI 能力。");
  }
}

export function assertPositiveInteger(value: number, field: string): void {
  if (Number.isInteger(value) && value > 0) return;
  throw invalidResponse(`Runtime 返回的 ${field} 无效。`);
}

function validateActiveVersionReference(
  activeVersion: number | null,
  activeVersionId: string | null,
  field: string
): void {
  if (activeVersion === null && activeVersionId === null) return;
  if (activeVersion !== null && activeVersionId !== null) {
    assertPositiveInteger(activeVersion, "activeVersion");
    assertStableResourceId(activeVersionId, field);
    return;
  }
  throw invalidResponse("Runtime 返回的激活版本号与版本引用不一致。");
}

export function invalidResponse(message: string): RuntimeError {
  return new RuntimeError(message, {
    errorCode: "INTERNAL_ERROR",
    status: 500
  });
}
