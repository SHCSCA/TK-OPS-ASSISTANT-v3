import type {
  AccountAIRecipeDto,
  AccountAIRecipeValidationDto,
  AccountAIRecipeVersionDto
} from "@/types/runtime/account-ai-recipe";
import type {
  CapabilityRouteDto,
  CompositionTemplateDto,
  CompositionTemplateVersionDto,
  ModelCapabilityListItemDto,
  ModelProfileDto,
  PromptProfileDto,
  PromptVersionDto,
  ProviderDto
} from "@/types/runtime/ai-system";
import type { AccountDto } from "@/types/runtime/accounts";
import type { RuntimeClientResult } from "@/types/runtime/common";

export function result<T>(
  data: T,
  status = 200
): RuntimeClientResult<T> {
  return {
    data,
    meta: null,
    operationId: null,
    requestId: "request-p0-e",
    status
  };
}

export function providerFixture(
  overrides: Partial<ProviderDto> = {}
): ProviderDto {
  return {
    id: "provider-1",
    name: "本机 OpenAI 兼容服务",
    adapterType: "openai_compatible",
    baseUrl: "http://127.0.0.1:11434/v1",
    credentialSummary: {
      configured: true,
      maskedValue: "sk-****7890"
    },
    enabled: true,
    healthStatus: "ready",
    revision: 3,
    ...overrides
  };
}

export function modelFixture(
  overrides: Partial<ModelProfileDto> = {}
): ModelProfileDto {
  return {
    id: "model-1",
    providerProfileId: "provider-1",
    modelId: "qwen-plus",
    displayName: "Qwen Plus",
    enabled: true,
    discoverySource: "manual",
    capabilities: [],
    revision: 2,
    ...overrides
  };
}

export function capabilityFixture(
  overrides: Partial<ModelCapabilityListItemDto> = {}
): ModelCapabilityListItemDto {
  return {
    modelProfileId: "model-1",
    providerProfileId: "provider-1",
    capabilityKey: "script_generation",
    declaredSupported: true,
    adapterSupported: true,
    contractVerified: true,
    availability: "available",
    verifiedAt: "2026-07-26T10:00:00Z",
    contractRevision: 1,
    ...overrides
  };
}

export function routeFixture(
  overrides: Partial<CapabilityRouteDto> = {}
): CapabilityRouteDto {
  return {
    id: "route-script-generation",
    capabilityKey: "script_generation",
    primaryModelProfileId: "model-1",
    fallbackModelProfileId: null,
    promptProfileId: "prompt-version-1",
    enabled: true,
    validationStatus: "valid",
    validationIssues: [],
    revision: 1,
    ...overrides
  };
}

export function promptProfileFixture(
  overrides: Partial<PromptProfileDto> = {}
): PromptProfileDto {
  return {
    profileKey: "script-default",
    name: "默认脚本 Prompt",
    capabilityKey: "script_generation",
    activeVersion: 1,
    activeVersionId: "prompt-version-1",
    versions: [{
      version: 1,
      status: "active",
      contentHash: "a".repeat(64)
    }],
    referenceCount: 1,
    revision: 2,
    ...overrides
  };
}

export function promptVersionFixture(
  overrides: Partial<PromptVersionDto> = {}
): PromptVersionDto {
  return {
    id: "prompt-version-1",
    profileKey: "script-default",
    name: "默认脚本 Prompt",
    capabilityKey: "script_generation",
    version: 1,
    status: "active",
    systemPrompt: "你是短视频脚本策划。",
    taskTemplate: "围绕 {{topic}} 生成脚本。",
    variablesSchema: { type: "object" },
    outputSchema: { type: "object" },
    visualStylePrefix: "",
    safetyConstraints: {},
    contentHash: "a".repeat(64),
    createdFromId: null,
    createdAt: "2026-07-26T10:00:00Z",
    activatedAt: "2026-07-26T10:01:00Z",
    revision: 1,
    ...overrides
  };
}

export function compositionTemplateFixture(
  overrides: Partial<CompositionTemplateDto> = {}
): CompositionTemplateDto {
  return {
    templateKey: "mixed-default",
    name: "默认混合媒体模板",
    templateType: "mixed_media",
    activeVersion: 1,
    activeVersionId: "composition-version-1",
    versions: [{
      version: 1,
      status: "active",
      contentHash: "b".repeat(64)
    }],
    compatibleCapabilities: { text_to_video: true },
    referenceCount: 1,
    revision: 2,
    ...overrides
  };
}

export function compositionVersionFixture(
  overrides: Partial<CompositionTemplateVersionDto> = {}
): CompositionTemplateVersionDto {
  return {
    id: "composition-version-1",
    templateKey: "mixed-default",
    name: "默认混合媒体模板",
    templateType: "mixed_media",
    version: 1,
    status: "active",
    aspectRatios: ["9:16"],
    parameterSchema: { type: "object" },
    compositionSpecTemplate: { scenes: [] },
    compatibleCapabilities: { text_to_video: true },
    previewAssetRef: null,
    contentHash: "b".repeat(64),
    createdFromId: null,
    createdAt: "2026-07-26T10:00:00Z",
    activatedAt: "2026-07-26T10:01:00Z",
    revision: 1,
    ...overrides
  };
}

export function recipeFixture(
  overrides: Partial<AccountAIRecipeDto> = {}
): AccountAIRecipeDto {
  return {
    accountId: "account-1",
    activeVersion: 1,
    activeVersionId: "recipe-version-1",
    versions: [{
      version: 1,
      status: "active",
      validationStatus: "valid"
    }],
    resolvedSummary: { script_generation: "model-1" },
    revision: 3,
    ...overrides
  };
}

export function recipeVersionFixture(
  overrides: Partial<AccountAIRecipeVersionDto> = {}
): AccountAIRecipeVersionDto {
  return {
    id: "recipe-version-1",
    accountId: "account-1",
    version: 1,
    status: "active",
    name: "账号默认配方",
    routeOverrides: {},
    visualStyle: { tone: "克制" },
    voiceProfileRef: null,
    compositionTemplateRef: "composition-version-1",
    costPolicy: {},
    fallbackPolicy: {},
    sourceAiConfigRevision: 5,
    validationStatus: "valid",
    validationIssues: [],
    contentHash: "c".repeat(64),
    createdAt: "2026-07-26T10:00:00Z",
    activatedAt: "2026-07-26T10:01:00Z",
    revision: 1,
    ...overrides
  };
}

export function recipeValidationFixture(
  overrides: Partial<AccountAIRecipeValidationDto> = {}
): AccountAIRecipeValidationDto {
  return {
    accountId: "account-1",
    version: 1,
    validationStatus: "valid",
    validationIssues: [],
    resolvedRouteSummary: {
      script_generation: {
        modelProfileId: "model-1",
        promptProfileId: "prompt-version-1",
        source: "system"
      }
    },
    sourceAiConfigRevision: 5,
    ...overrides
  };
}

export function accountFixture(
  overrides: Partial<AccountDto> = {}
): AccountDto {
  const missing = {
    status: "missing" as const,
    label: "未配置",
    errorCode: null,
    logId: null,
    checkedAt: null,
    suggestedAction: null
  };
  return {
    id: "account-1",
    name: "效率观察",
    username: "efficiency.lab",
    platform: "tiktok",
    status: "draft",
    positioningSummary: null,
    lastUsedAt: null,
    readiness: {
      connection: { ...missing },
      knowledge: { ...missing },
      ai: { ...missing },
      overall: "blocked",
      checkedAt: null,
      suggestedAction: null
    },
    wizardCompletedAt: null,
    revision: 3,
    ...overrides
  };
}
