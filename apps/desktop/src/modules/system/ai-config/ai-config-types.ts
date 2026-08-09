import type {
  AICapabilityKey,
  CompositionTemplateType,
  ProviderAdapterType
} from "@/types/runtime/ai-system";

export type AIPageState =
  | "idle"
  | "loading"
  | "first_use"
  | "empty"
  | "filtered_empty"
  | "dependency_blocked"
  | "waiting_external"
  | "restricted"
  | "error"
  | "ready";

export type AISystemPrimarySection = "ai" | "runtime" | "diagnostics";
export type AICapabilitySurface = "providers" | "models" | "prompts";

export type AIConfigUiError = {
  message: string;
  errorCode: string | null;
  logId: string | null;
  requestId: string | null;
  retryable: boolean;
};

export type ProviderWizardStep =
  | "connection"
  | "credential"
  | "network"
  | "models"
  | "verify";

export type ProviderWizardDraft = {
  name: string;
  adapterType: ProviderAdapterType;
  baseUrl: string;
  credential: string;
  region: string;
  timeoutMs: number;
  maxConcurrency: number;
  modelMode: "discover" | "manual";
  modelId: string;
  modelDisplayName: string;
};

export type RouteEditorDraft = {
  primaryModelProfileId: string;
  fallbackModelProfileId: string;
  promptProfileId: string;
  enabled: boolean;
};

export type PromptEditorDraft = {
  mode: "create_profile" | "create_version";
  profileKey: string;
  capabilityKey: AICapabilityKey;
  name: string;
  systemPrompt: string;
  taskTemplate: string;
  variablesSchema: string;
  outputSchema: string;
  visualStylePrefix: string;
  safetyConstraints: string;
  createdFromVersion: number;
};

export type CompositionTemplateEditorDraft = {
  mode: "create_profile" | "create_version";
  templateKey: string;
  templateType: CompositionTemplateType;
  name: string;
  aspectRatios: string;
  parameterSchema: string;
  compositionSpecTemplate: string;
  compatibleCapabilities: string;
  previewAssetRef: string;
  createdFromVersion: number;
};

export type AIPageStateDescriptor = {
  icon: string;
  title: string;
  description: string;
};
