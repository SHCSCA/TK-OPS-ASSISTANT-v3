import type {
  CapabilityCheckInput,
  CapabilityRouteDto,
  CapabilityRouteInput,
  CapabilityRouteListQuery,
  CapabilityRoutePageDto,
  CompositionTemplateDto,
  CompositionTemplateInput,
  CompositionTemplateListQuery,
  CompositionTemplatePageDto,
  CompositionTemplateValidationDto,
  CompositionTemplateVersionDto,
  CompositionTemplateVersionInput,
  CredentialSummaryDto,
  DiagnosticsDto,
  DiagnosticsSection,
  ModelCapabilityDto,
  ModelCapabilityListQuery,
  ModelCapabilityPageDto,
  ModelCreateInput,
  ModelDiscoveryInput,
  ModelListQuery,
  ModelPageDto,
  ModelPatchInput,
  ModelProfileDto,
  PromptProfileDto,
  PromptProfileInput,
  PromptProfileListQuery,
  PromptProfilePageDto,
  PromptVersionDto,
  PromptVersionInput,
  ProviderCheckInput,
  ProviderCreateInput,
  ProviderCredentialInput,
  ProviderDto,
  ProviderListQuery,
  ProviderPageDto,
  ProviderPatchInput,
  SafeLogExcerptDto
} from "@/types/runtime/ai-system";
import type { RuntimeClientResult } from "@/types/runtime/common";
import type { TaskAcceptedDto } from "@/types/runtime/tasks";

import {
  assertStableResourceId,
  requestRuntimeV1,
  type RuntimeCallOptions,
  type RuntimeIdempotentOptions,
  type RuntimeRequestOptions,
  type RuntimeRevisionIdempotentOptions,
  type RuntimeRevisionOptions
} from "./core";
import {
  assertCapabilityKey,
  assertPositiveInteger,
  invalidResponse,
  modelPath,
  promptPath,
  providerPath,
  routePath,
  templatePath,
  validateCapability,
  validateCompositionTemplate,
  validateCompositionTemplateVersion as validateCompositionTemplateVersionDto,
  validateCredentialSummary,
  validateModel,
  validatePromptProfile,
  validatePromptVersion,
  validateProvider,
  validateRoute,
  validateSystemTaskAccepted,
  versionPath,
  withQuery
} from "./ai-system-contracts";

type AIOptions = RuntimeCallOptions
  & Partial<RuntimeIdempotentOptions>
  & Partial<RuntimeRevisionOptions>;

export function listProviderProfiles(
  query: ProviderListQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ProviderPageDto>> {
  return requestRuntimeV1(withQuery("/api/v1/system/providers", query), {
    ...options,
    validateData: (data) => data.items.forEach(validateProvider)
  });
}

export function createProviderProfile(
  input: ProviderCreateInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<ProviderDto>> {
  return mutate("/api/v1/system/providers", "POST", input, options, validateProvider);
}

export function getProviderProfile(
  providerId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ProviderDto>> {
  return requestRuntimeV1(providerPath(providerId), {
    ...options,
    validateData: validateProvider
  });
}

export function patchProviderProfile(
  providerId: string,
  input: ProviderPatchInput,
  options: RuntimeRevisionOptions
): Promise<RuntimeClientResult<ProviderDto>> {
  return mutate(providerPath(providerId), "PATCH", input, options, validateProvider);
}

export function updateProviderCredential(
  providerId: string,
  input: ProviderCredentialInput,
  options: RuntimeRevisionOptions
): Promise<RuntimeClientResult<CredentialSummaryDto>> {
  return mutate(
    `${providerPath(providerId)}/credential`,
    "PUT",
    input,
    options,
    validateCredentialSummary
  );
}

export function startProviderCheck(
  providerId: string,
  input: ProviderCheckInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<TaskAcceptedDto>> {
  return mutate(
    `${providerPath(providerId)}/checks`,
    "POST",
    input,
    options,
    validateSystemTaskAccepted
  );
}

export function startProviderModelDiscovery(
  providerId: string,
  input: ModelDiscoveryInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<TaskAcceptedDto>> {
  return mutate(
    `${providerPath(providerId)}/model-discovery`,
    "POST",
    input,
    options,
    validateSystemTaskAccepted
  );
}

export function listModelProfiles(
  query: ModelListQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ModelPageDto>> {
  return requestRuntimeV1(withQuery("/api/v1/system/models", query), {
    ...options,
    validateData: (data) => data.items.forEach(validateModel)
  });
}

export function createModelProfile(
  input: ModelCreateInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<ModelProfileDto>> {
  return mutate("/api/v1/system/models", "POST", input, options, validateModel);
}

export function getModelProfile(
  modelProfileId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ModelProfileDto>> {
  return requestRuntimeV1(modelPath(modelProfileId), {
    ...options,
    validateData: validateModel
  });
}

export function patchModelProfile(
  modelProfileId: string,
  input: ModelPatchInput,
  options: RuntimeRevisionOptions
): Promise<RuntimeClientResult<ModelProfileDto>> {
  return mutate(modelPath(modelProfileId), "PATCH", input, options, validateModel);
}

export function listModelCapabilities(
  query: ModelCapabilityListQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ModelCapabilityPageDto>> {
  return requestRuntimeV1(
    withQuery("/api/v1/system/model-capabilities", query),
    {
      ...options,
      validateData: (data) => data.items.forEach((item) => {
        assertStableResourceId(item.modelProfileId, "modelProfileId");
        assertStableResourceId(item.providerProfileId, "providerProfileId");
        validateCapability(item);
      })
    }
  );
}

export function getModelCapabilities(
  modelProfileId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<ModelCapabilityDto[]>> {
  return requestRuntimeV1(`${modelPath(modelProfileId)}/capabilities`, {
    ...options,
    validateData: (data) => data.forEach(validateCapability)
  });
}

export function startModelCapabilityCheck(
  modelProfileId: string,
  input: CapabilityCheckInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<TaskAcceptedDto>> {
  return mutate(
    `${modelPath(modelProfileId)}/capability-checks`,
    "POST",
    input,
    options,
    validateSystemTaskAccepted
  );
}

export function listCapabilityRoutes(
  query: CapabilityRouteListQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<CapabilityRoutePageDto>> {
  return requestRuntimeV1(
    withQuery("/api/v1/system/capability-routes", query),
    {
      ...options,
      validateData: (data) => data.items.forEach(validateRoute)
    }
  );
}

export function updateCapabilityRoute(
  capabilityKey: string,
  input: CapabilityRouteInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<CapabilityRouteDto>> {
  return mutate(routePath(capabilityKey), "PUT", input, options, validateRoute);
}

export function validateCapabilityRoute(
  capabilityKey: string,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<CapabilityRouteDto>> {
  return mutate(
    `${routePath(capabilityKey)}/validate`,
    "POST",
    undefined,
    options,
    validateRoute
  );
}

export function listPromptProfiles(
  query: PromptProfileListQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<PromptProfilePageDto>> {
  return requestRuntimeV1(
    withQuery("/api/v1/system/prompt-profiles", query),
    {
      ...options,
      validateData: (data) => data.items.forEach(validatePromptProfile)
    }
  );
}

export function createPromptProfile(
  input: PromptProfileInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<PromptProfileDto>> {
  return mutate(
    "/api/v1/system/prompt-profiles",
    "POST",
    input,
    options,
    validatePromptProfile
  );
}

export function getPromptProfile(
  profileKey: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<PromptProfileDto>> {
  return requestRuntimeV1(promptPath(profileKey), {
    ...options,
    validateData: validatePromptProfile
  });
}

export function getPromptVersion(
  profileKey: string,
  version: number,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<PromptVersionDto>> {
  return requestRuntimeV1(`${promptPath(profileKey)}/versions/${versionPath(version)}`, {
    ...options,
    validateData: validatePromptVersion
  });
}

export function createPromptVersion(
  profileKey: string,
  input: PromptVersionInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<PromptVersionDto>> {
  return mutate(
    `${promptPath(profileKey)}/versions`,
    "POST",
    input,
    options,
    validatePromptVersion
  );
}

export function activatePromptVersion(
  profileKey: string,
  version: number,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<PromptProfileDto>> {
  return mutate(
    `${promptPath(profileKey)}/versions/${versionPath(version)}/activate`,
    "POST",
    undefined,
    options,
    validatePromptProfile
  );
}

export function listCompositionTemplates(
  query: CompositionTemplateListQuery = {},
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<CompositionTemplatePageDto>> {
  return requestRuntimeV1(
    withQuery("/api/v1/system/composition-templates", query),
    {
      ...options,
      validateData: (data) => data.items.forEach(validateCompositionTemplate)
    }
  );
}

export function createCompositionTemplate(
  input: CompositionTemplateInput,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<CompositionTemplateDto>> {
  return mutate(
    "/api/v1/system/composition-templates",
    "POST",
    input,
    options,
    validateCompositionTemplate
  );
}

export function getCompositionTemplate(
  templateKey: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<CompositionTemplateDto>> {
  return requestRuntimeV1(templatePath(templateKey), {
    ...options,
    validateData: validateCompositionTemplate
  });
}

export function getCompositionTemplateVersion(
  templateKey: string,
  version: number,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<CompositionTemplateVersionDto>> {
  return requestRuntimeV1(
    `${templatePath(templateKey)}/versions/${versionPath(version)}`,
    { ...options, validateData: validateCompositionTemplateVersionDto }
  );
}

export function createCompositionTemplateVersion(
  templateKey: string,
  input: CompositionTemplateVersionInput,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<CompositionTemplateVersionDto>> {
  return mutate(
    `${templatePath(templateKey)}/versions`,
    "POST",
    input,
    options,
    validateCompositionTemplateVersionDto
  );
}

export function validateCompositionTemplateVersion(
  templateKey: string,
  version: number,
  options: RuntimeIdempotentOptions
): Promise<RuntimeClientResult<CompositionTemplateValidationDto>> {
  return mutate(
    `${templatePath(templateKey)}/versions/${versionPath(version)}/validate`,
    "POST",
    undefined,
    options,
    (data) => {
      assertStableResourceId(data.templateKey, "templateKey");
      assertPositiveInteger(data.version, "version");
    }
  );
}

export function activateCompositionTemplateVersion(
  templateKey: string,
  version: number,
  options: RuntimeRevisionIdempotentOptions
): Promise<RuntimeClientResult<CompositionTemplateDto>> {
  return mutate(
    `${templatePath(templateKey)}/versions/${versionPath(version)}/activate`,
    "POST",
    undefined,
    options,
    validateCompositionTemplate
  );
}

export function getSystemDiagnostics(
  sections: DiagnosticsSection[] = [],
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<DiagnosticsDto>> {
  return requestRuntimeV1(
    withQuery("/api/v1/system/diagnostics", {
      sections: sections.length ? sections.join(",") : undefined
    }),
    options
  );
}

export function getSafeLogExcerpt(
  logId: string,
  options: RuntimeCallOptions = {}
): Promise<RuntimeClientResult<SafeLogExcerptDto>> {
  assertStableResourceId(logId, "log_id");
  return requestRuntimeV1(
    `/api/v1/system/logs/${encodeURIComponent(logId)}`,
    {
      ...options,
      validateData: (data) => {
        if (data.logId !== logId) {
          throw invalidResponse("Runtime 返回了其他日志的诊断摘要。");
        }
      }
    }
  );
}

function mutate<T>(
  path: string,
  method: "POST" | "PUT" | "PATCH",
  body: unknown,
  options: AIOptions,
  validateData: (data: T) => void
): Promise<RuntimeClientResult<T>> {
  const request: RuntimeRequestOptions<T> = {
    ...options,
    method,
    validateData
  };
  if (body !== undefined) request.body = body;
  return requestRuntimeV1<T>(path, request);
}
