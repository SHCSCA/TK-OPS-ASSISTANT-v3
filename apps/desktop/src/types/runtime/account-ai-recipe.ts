import type { AIValidationIssueDto } from "./ai-system";

export type AIRecipeStatus = "draft" | "active" | "archived";
export type AIRecipeValidationStatus = "unvalidated" | "valid" | "invalid";

export type AccountAIRecipeVersionSummaryDto = {
  version: number;
  status: AIRecipeStatus;
  validationStatus: AIRecipeValidationStatus;
};

export type AccountAIRecipeDto = {
  accountId: string;
  activeVersion: number | null;
  versions: AccountAIRecipeVersionSummaryDto[];
  resolvedSummary: Record<string, unknown> | null;
  revision: number;
};

export type AccountAIRecipeVersionDto = {
  id: string;
  accountId: string;
  version: number;
  status: AIRecipeStatus;
  name: string;
  routeOverrides: Record<string, unknown>;
  visualStyle: Record<string, unknown>;
  voiceProfileRef: string | null;
  compositionTemplateRef: string | null;
  costPolicy: Record<string, unknown>;
  fallbackPolicy: Record<string, unknown>;
  sourceAiConfigRevision: number;
  validationStatus: AIRecipeValidationStatus;
  validationIssues: Array<{
    code: string;
    field: string | null;
    message: string;
  }>;
  contentHash: string;
  createdAt: string;
  activatedAt: string | null;
  revision: number;
};

export type AccountAIRecipeVersionPageDto = {
  items: AccountAIRecipeVersionDto[];
  totalKnown: number | null;
};

export type AccountAIRecipeValidationDto = {
  accountId: string;
  version: number;
  validationStatus: "valid" | "invalid";
  validationIssues: Array<
    Required<Pick<AIValidationIssueDto, "code">> & {
      field: string | null;
      message: string;
      suggestedAction: string | null;
    }
  >;
  resolvedRouteSummary: Record<
    string,
    {
      modelProfileId: string;
      promptProfileId: string | null;
      source: "system" | "account_override";
    }
  >;
  sourceAiConfigRevision: number;
};

export type AccountAIRecipeVersionInput = {
  name: string;
  routeOverrides: Record<string, unknown>;
  visualStyle: Record<string, unknown>;
  voiceProfileRef?: string | null;
  compositionTemplateRef?: string | null;
  costPolicy: Record<string, unknown>;
  fallbackPolicy: Record<string, unknown>;
};

export type AccountAIRecipeVersionQuery = {
  cursor?: string;
  limit?: number;
};
