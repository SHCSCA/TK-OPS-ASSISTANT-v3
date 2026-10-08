import type { RuntimeTaskStatus } from "./tasks";

export const AI_CAPABILITY_KEYS = [
  "topic_generation",
  "script_generation",
  "script_rewrite",
  "storyboard_generation",
  "video_deconstruction",
  "speech_to_text",
  "image_generation",
  "text_to_video",
  "image_to_video",
  "tts",
  "subtitle_alignment",
  "asset_analysis",
  "embedding"
] as const;

export type AICapabilityKey = (typeof AI_CAPABILITY_KEYS)[number];

export type ProviderAdapterType =
  | "direct_api"
  | "openai_compatible"
  | "comfyui"
  | "runninghub";

export type ProviderHealthStatus =
  | "unknown"
  | "checking"
  | "ready"
  | "degraded"
  | "failed";

export type ProviderCredentialDto = {
  configured: boolean;
  maskedValue: string | null;
};

export type ProviderDto = {
  id: string;
  name: string;
  adapterType: ProviderAdapterType;
  baseUrl: string;
  credentialSummary: ProviderCredentialDto;
  enabled: boolean;
  healthStatus: ProviderHealthStatus;
  revision: number;
};

export type ProviderPageDto = {
  items: ProviderDto[];
  totalKnown: number | null;
};

export type ProviderListQuery = {
  enabled?: boolean;
  healthStatus?: ProviderHealthStatus;
  cursor?: string;
  limit?: number;
};

export type ProviderCreateInput = {
  name: string;
  adapterType: ProviderAdapterType;
  baseUrl: string;
  region?: string | null;
  timeoutMs: number;
  maxConcurrency: number;
  enabled: boolean;
};

export type ProviderPatchInput = Partial<
  Omit<ProviderCreateInput, "adapterType">
>;

export type ProviderCredentialInput = {
  credential: string;
};

export type CredentialSummaryDto = {
  configured: true;
  credentialReferenceChanged: true;
  maskedValue: string;
  updatedAt: string;
  providerRevision: number;
};

export type ProviderCheckInput = {
  force?: boolean;
};

export type ModelDiscoveryInput = {
  replaceMissing?: false;
};

export type ModelCapabilityAvailability =
  | "available"
  | "unverified"
  | "unavailable";

export type ModelCapabilityDto = {
  capabilityKey: AICapabilityKey;
  declaredSupported: boolean;
  adapterSupported: boolean;
  contractVerified: boolean;
  availability: ModelCapabilityAvailability;
  verifiedAt: string | null;
  contractRevision: number;
};

export type ModelProfileDto = {
  id: string;
  providerProfileId: string;
  modelId: string;
  displayName: string;
  enabled: boolean;
  discoverySource: "discovered" | "manual" | "migrated";
  capabilities: ModelCapabilityDto[];
  revision: number;
};

export type ModelPageDto = {
  items: ModelProfileDto[];
  totalKnown: number | null;
};

export type ModelListQuery = {
  providerId?: string;
  enabled?: boolean;
  capabilityKey?: AICapabilityKey;
  cursor?: string;
  limit?: number;
};

export type ModelCreateInput = {
  providerProfileId: string;
  modelId: string;
  displayName: string;
  enabled: boolean;
  baseLimits?: Record<string, unknown>;
};

export type ModelPatchInput = {
  displayName?: string;
  enabled?: boolean;
  baseLimits?: Record<string, unknown>;
};

export type ModelCapabilityListItemDto = ModelCapabilityDto & {
  modelProfileId: string;
  providerProfileId: string;
};

export type ModelCapabilityPageDto = {
  items: ModelCapabilityListItemDto[];
  totalKnown: number | null;
};

export type ModelCapabilityListQuery = {
  providerId?: string;
  modelProfileId?: string;
  capabilityKey?: AICapabilityKey;
  availability?: ModelCapabilityAvailability;
  cursor?: string;
  limit?: number;
};

export type CapabilityCheckInput = {
  capabilityKeys?: AICapabilityKey[];
  force?: boolean;
  mode?: "contract_only" | "real_small_call";
};

export type CapabilityRouteValidationStatus =
  | "valid"
  | "incomplete"
  | "invalid";

export type AIValidationIssueDto = {
  code: string;
  field?: string | null;
  message?: string;
  suggestedAction?: string | null;
  [key: string]: unknown;
};

export type CapabilityRouteDto = {
  id: string;
  capabilityKey: AICapabilityKey;
  primaryModelProfileId: string | null;
  fallbackModelProfileId: string | null;
  promptProfileId: string | null;
  enabled: boolean;
  validationStatus: CapabilityRouteValidationStatus;
  validationIssues: AIValidationIssueDto[];
  revision: number;
};

export type CapabilityRoutePageDto = {
  items: CapabilityRouteDto[];
  totalKnown: number | null;
};

export type CapabilityRouteListQuery = {
  capabilityKey?: AICapabilityKey;
  validationStatus?: CapabilityRouteValidationStatus;
  cursor?: string;
  limit?: number;
};

export type CapabilityRouteInput = {
  primaryModelProfileId: string | null;
  fallbackModelProfileId: string | null;
  promptProfileId: string | null;
  enabled: boolean;
};

export type VersionStatus = "draft" | "active" | "archived";

export type VersionSummaryDto = {
  version: number;
  status: VersionStatus;
  contentHash: string;
};

export type PromptProfileDto = {
  profileKey: string;
  name: string;
  capabilityKey: AICapabilityKey;
  activeVersion: number | null;
  activeVersionId: string | null;
  versions: VersionSummaryDto[];
  referenceCount: number;
  revision: number;
};

export type PromptProfilePageDto = {
  items: PromptProfileDto[];
  totalKnown: number | null;
};

export type PromptProfileListQuery = {
  capabilityKey?: AICapabilityKey;
  status?: VersionStatus;
  cursor?: string;
  limit?: number;
};

export type PromptProfileInput = {
  profileKey: string;
  name: string;
  capabilityKey: AICapabilityKey;
  systemPrompt: string;
  taskTemplate: string;
  variablesSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
  visualStylePrefix?: string;
  safetyConstraints: Record<string, unknown>;
};

export type PromptVersionInput = Omit<
  PromptProfileInput,
  "profileKey" | "capabilityKey"
> & {
  createdFromVersion: number;
};

export type PromptVersionDto = {
  id: string;
  profileKey: string;
  name: string;
  capabilityKey: AICapabilityKey;
  version: number;
  status: VersionStatus;
  systemPrompt: string;
  taskTemplate: string;
  variablesSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
  visualStylePrefix: string;
  safetyConstraints: Record<string, unknown>;
  contentHash: string;
  createdFromId: string | null;
  createdAt: string;
  activatedAt: string | null;
  revision: number;
};

export type CompositionTemplateType =
  | "slideshow"
  | "talking_head"
  | "product_showcase"
  | "mixed_media";

export type CompositionTemplateDto = {
  templateKey: string;
  name: string;
  templateType: CompositionTemplateType;
  activeVersion: number | null;
  activeVersionId: string | null;
  versions: VersionSummaryDto[];
  compatibleCapabilities: Record<string, unknown>;
  referenceCount: number;
  revision: number;
};

export type CompositionTemplatePageDto = {
  items: CompositionTemplateDto[];
  totalKnown: number | null;
};

export type CompositionTemplateListQuery = {
  templateType?: CompositionTemplateType;
  status?: VersionStatus;
  cursor?: string;
  limit?: number;
};

export type CompositionTemplateInput = {
  templateKey: string;
  name: string;
  templateType: CompositionTemplateType;
  aspectRatios: string[];
  parameterSchema: Record<string, unknown>;
  compositionSpecTemplate: Record<string, unknown>;
  compatibleCapabilities: Record<string, unknown>;
  previewAssetRef?: string | null;
};

export type CompositionTemplateVersionInput = Omit<
  CompositionTemplateInput,
  "templateKey" | "templateType"
> & {
  createdFromVersion: number;
};

export type CompositionTemplateVersionDto = {
  id: string;
  templateKey: string;
  name: string;
  templateType: CompositionTemplateType;
  version: number;
  status: VersionStatus;
  aspectRatios: string[];
  parameterSchema: Record<string, unknown>;
  compositionSpecTemplate: Record<string, unknown>;
  compatibleCapabilities: Record<string, unknown>;
  previewAssetRef: string | null;
  contentHash: string;
  createdFromId: string | null;
  createdAt: string;
  activatedAt: string | null;
  revision: number;
};

export type CompositionTemplateValidationDto = {
  templateKey: string;
  version: number;
  validationStatus: "valid" | "invalid";
  validationIssues: Array<{
    code: string;
    field: string | null;
    message: string;
  }>;
  verifiedCapabilities: AICapabilityKey[];
  checkedAt: string;
};

export type DiagnosticsDto = {
  runtime: Record<string, unknown>;
  database: Record<string, unknown>;
  directories: Record<string, unknown>;
  mediaTools: Record<string, unknown>;
  sidecar: Record<string, unknown>;
  checkedAt: string;
};

export type DiagnosticsSection =
  | "runtime"
  | "database"
  | "directories"
  | "mediaTools"
  | "sidecar";

export type SafeLogExcerptDto = {
  logId: string;
  severity: "info" | "warning" | "error";
  summary: string;
  errorCode: string | null;
  stage: string | null;
  occurredAt: string;
  suggestedActions: string[];
  requestId: string | null;
  operationId: string | null;
};

export type AISystemTaskSummary = {
  taskId: string;
  status: RuntimeTaskStatus;
  progress: number;
  cancellable: boolean;
  errorCode: string | null;
  logId: string | null;
};
