import type {
  AccountAIRecipeDto,
  AccountAIRecipeValidationDto,
  AccountAIRecipeVersionDto
} from "@/types/runtime/account-ai-recipe";
import type { CompositionTemplateDto } from "@/types/runtime/ai-system";
import type {
  AIConfigUiError,
  AIPageState
} from "@/modules/system/ai-config/ai-config-types";

export type AccountAIRecipeDraft = {
  name: string;
  routeOverrides: string;
  visualStyle: string;
  voiceProfileRef: string;
  compositionTemplateRef: string;
  costPolicy: string;
  fallbackPolicy: string;
};

export type AccountAIRecipeCache = {
  accountId: string;
  recipe: AccountAIRecipeDto | null;
  versions: AccountAIRecipeVersionDto[];
  templates: CompositionTemplateDto[];
  selectedVersion: number | null;
  validation: AccountAIRecipeValidationDto | null;
  draft: AccountAIRecipeDraft;
  editorOpen: boolean;
  dirty: boolean;
  state: AIPageState;
  error: AIConfigUiError | null;
  feedback: string | null;
  busyKey: string | null;
};

export type AccountAIRecipePanelMode = "full" | "compact" | "wizard";
