import type {
  AICapabilityConfig,
  AICapabilitySupportMatrix,
  AIModelCatalogItem,
  AIProviderCatalogItem,
  AIProviderHealth
} from "@/types/runtime";

export type SettingsSectionId =
  | "provider"
  | "capability"
  | "prompt"
  | "voice"
  | "subtitle"
  | "directory"
  | "cache"
  | "logging"
  | "diagnostics";

export interface ProviderCardState extends AIProviderCatalogItem {
  health?: AIProviderHealth | null;
  models?: AIModelCatalogItem[];
  loadingModels?: boolean;
}

export interface CapabilityBindingRow extends AICapabilityConfig {
  label: string;
  status: "ready" | "warning" | "error" | "neutral";
}

export type ProviderCategory = "all" | "commercial" | "local" | "aggregator" | "media";

export interface PromptEditorState {
  capabilityId: string;
  label: string;
  agentRole: string;
  systemPrompt: string;
  userPromptTemplate: string;
  variables: string[];
  expanded: boolean;
}

export interface VoiceProfileFormState {
  voiceId: string;
  displayName: string;
  locale: string;
  tags: string;
}

/** 重导出供组件使用 */
export type { AICapabilitySupportMatrix, AIModelCatalogItem, AIProviderCatalogItem, AIProviderHealth };
