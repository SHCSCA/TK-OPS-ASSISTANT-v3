export type AccountStatus = "draft" | "unbound" | "ready" | "attention" | "archived";

export type AccountReadinessItemStatus =
  | "ready"
  | "attention"
  | "blocked"
  | "missing"
  | "empty"
  | "checking";

export type AccountSuggestedActionKey =
  | "open_connection"
  | "open_knowledge"
  | "open_ai_recipe"
  | "run_health_check"
  | "view_log";

export type AccountSuggestedActionDto = {
  actionKey: AccountSuggestedActionKey;
  label: string;
  routeId: string;
  section: string | null;
  taskId: string | null;
};

export type AccountReadinessItemDto = {
  status: AccountReadinessItemStatus;
  label: string;
  errorCode: string | null;
  logId: string | null;
  checkedAt: string | null;
  suggestedAction: AccountSuggestedActionDto | null;
};

export type AccountReadinessDto = {
  connection: AccountReadinessItemDto;
  knowledge: AccountReadinessItemDto;
  ai: AccountReadinessItemDto;
  overall: "ready" | "attention" | "blocked";
  checkedAt: string | null;
  suggestedAction: AccountSuggestedActionDto | null;
};

export type AccountDto = {
  id: string;
  name: string;
  username: string | null;
  platform: "tiktok";
  status: AccountStatus;
  positioningSummary: string | null;
  lastUsedAt: string | null;
  readiness: AccountReadinessDto;
  wizardCompletedAt: string | null;
  revision: number;
};

export type AccountListDto = {
  items: AccountDto[];
  totalKnown: number | null;
};

export type AccountListQuery = {
  q?: string;
  status?: AccountStatus;
  cursor?: string;
  limit?: number;
};

export type AccountCreateInput = {
  name: string;
  username?: string | null;
  platform: "tiktok";
};

export type AccountPatchInput = {
  name?: string;
  username?: string | null;
  avatarAssetRef?: string | null;
};

export type AccountWizardStep =
  | "identity"
  | "connection"
  | "positioning"
  | "knowledge"
  | "ai_recipe"
  | "health";

export type CompleteWizardInput = {
  completedSteps: AccountWizardStep[];
};

export type AccountCopySection =
  | "positioning"
  | "knowledgeRules"
  | "brandKit"
  | "aiRecipe"
  | "publishDefaults";

export type AccountCopyInput = {
  sourceAccountId: string;
  sections: AccountCopySection[];
};

export type ArchiveInput = {
  reason?: string | null;
};

export type AccountHealthCheckKey = "connection" | "knowledge" | "ai";

export type HealthCheckInput = {
  checks?: AccountHealthCheckKey[];
};

export type AccountWorkspaceInclude = "readiness" | "taskSummary" | "navigation";

export type AccountWorkspaceRouteId =
  | "account_workspace_home"
  | "account_strategy_knowledge"
  | "account_script_topic"
  | "account_storyboard_planning"
  | "account_video_deconstruction"
  | "account_batch_production"
  | "account_content_library"
  | "account_media_toolbox"
  | "account_publishing"
  | "account_review";

export type AccountNavigationDto = {
  lastRoute: string;
  availableRoutes: AccountWorkspaceRouteId[];
};

export type AccountTaskSummaryDto = {
  running: number;
  failed: number;
};

export type AccountWorkspaceContextDto = {
  account: AccountDto;
  readiness: AccountReadinessDto;
  navigation: AccountNavigationDto;
  taskSummary: AccountTaskSummaryDto;
  workspaceRevision: number;
};

export type AccountCopySkippedSectionDto = {
  section: AccountCopySection;
  reasonCode: string;
};

export type AccountConfigCopyResultDto = {
  runId: string;
  sourceAccountId: string;
  targetAccountId: string;
  requestedSections: AccountCopySection[];
  copiedSections: AccountCopySection[];
  skippedSections: AccountCopySkippedSectionDto[];
  status: "succeeded";
  targetRevision: number;
  completedAt: string;
};

export type DeviceWorkspaceSummaryDto = {
  id: string;
  name: string;
  status: string;
};

export type BrowserInstanceSummaryDto = {
  id: string;
  name: string;
  status: string;
  lastCheckedAt: string | null;
};

export type ExecutionBindingSummaryDto = {
  id: string;
  status: string;
  deviceWorkspaceId: string;
  browserInstanceId: string;
};

export type ConnectionCandidateDto = {
  environmentId: string;
  eligibilityRevision: number;
  deviceWorkspace: DeviceWorkspaceSummaryDto;
  browserInstance: BrowserInstanceSummaryDto;
  executionBinding: ExecutionBindingSummaryDto;
};

export type ConnectionCandidatesDto = {
  items: ConnectionCandidateDto[];
};

export type ConnectionCheckSummaryDto = {
  status: "unknown" | "checking" | "ready" | "attention" | "failed";
  checkedAt: string | null;
  errorCode: string | null;
  logId: string | null;
};

export type ConnectionDto = {
  accountId: string;
  authStatus: "unknown" | "required" | "valid" | "expired" | "failed";
  healthStatus: "unknown" | "checking" | "ready" | "attention" | "failed";
  deviceWorkspace: DeviceWorkspaceSummaryDto | null;
  browserInstance: BrowserInstanceSummaryDto | null;
  executionBinding: ExecutionBindingSummaryDto | null;
  lastCheck: ConnectionCheckSummaryDto | null;
  revision: number;
};

export type ConnectionBindingInput = {
  environmentId: string;
  eligibilityRevision: number;
};

export type ConnectionCheckInput = {
  checks?: ["connection"];
};
