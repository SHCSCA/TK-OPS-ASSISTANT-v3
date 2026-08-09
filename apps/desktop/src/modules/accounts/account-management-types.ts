import type {
  AccountCopySection,
  AccountDto,
  AccountStatus,
  AccountWizardStep
} from "@/types/runtime/accounts";

export type AccountCollectionState =
  | "idle"
  | "loading"
  | "empty"
  | "filtered-empty"
  | "ready"
  | "error";

export type AccountDetailTab =
  | "overview"
  | "identity"
  | "connection"
  | "ai_recipe"
  | "archive";

export type AccountOperationKind =
  | "create"
  | "archive"
  | "restore"
  | "copy"
  | "health"
  | "connection"
  | "ai_recipe"
  | "wizard";

export type AccountUiError = {
  message: string;
  errorCode: string | null;
  logId: string | null;
  requestId: string | null;
  retryable: boolean;
};

export type AccountOperationFeedback = {
  kind: AccountOperationKind;
  tone: "success" | "info" | "error";
  message: string;
  accountId: string | null;
  taskId: string | null;
  logId: string | null;
};

export type AccountListFilters = {
  q: string;
  status: AccountStatus | "";
};

export type AccountDraftInput = {
  name: string;
  username: string;
};

export type AccountWizardSnapshot = {
  account: AccountDto | null;
  completedSteps: AccountWizardStep[];
  activeStep: AccountWizardStep;
};

export type AccountCopyForm = {
  sourceAccountId: string;
  sections: AccountCopySection[];
};

export type AccountWizardDependency = "positioning" | "knowledge" | "ai_recipe";

export const ACCOUNT_WIZARD_STEPS: AccountWizardStep[] = [
  "identity",
  "connection",
  "positioning",
  "knowledge",
  "ai_recipe",
  "health"
];

export const ACCOUNT_COPY_SECTIONS: Array<{
  id: AccountCopySection;
  label: string;
}> = [
  { id: "positioning", label: "账号定位" },
  { id: "knowledgeRules", label: "知识规则" },
  { id: "brandKit", label: "品牌规范" },
  { id: "aiRecipe", label: "AI 配方" },
  { id: "publishDefaults", label: "发布默认值" }
];
