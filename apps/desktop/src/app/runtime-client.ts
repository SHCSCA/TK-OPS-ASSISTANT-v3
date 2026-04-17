import type {
  AICapabilitySettings,
  AICapabilitySupportMatrix,
  AIModelCatalogItem,
  AIModelCatalogRefreshResult,
  AIProviderCatalogItem,
  AIProviderHealth,
  AIProviderHealthInput,
  AIProviderSecretInput,
  AIProviderSecretStatus,
  AppSettings,
  AppSettingsUpdateInput,
  CreateProjectInput,
  CurrentProjectContext,
  DashboardSummary,
  LicenseActivationInput,
  LicenseStatus,
  RuntimeDiagnostics,
  RuntimeEnvelope,
  RuntimeRequestErrorShape,
  RuntimeHealthSnapshot,
  ScriptDocument,
  StoryboardDocument,
  StoryboardScene,
  SubtitleTrackDto,
  SubtitleTrackGenerateInput,
  SubtitleTrackGenerateResultDto,
  SubtitleTrackUpdateInput,
  VoiceProfileDto,
  VoiceTrackDto,
  VoiceTrackGenerateInput,
  VoiceTrackGenerateResultDto,
  AssetDeleteResult,
  AssetDto,
  AssetImportInput,
  AssetReferenceDto,
  AssetUpdateInput,
  AccountDto,
  AccountGroupDto,
  AccountCreateInput,
  AutomationTaskCreateInput,
  AutomationTaskDto,
  AutomationTaskRunDto,
  AutomationTaskUpdateInput,
  TriggerTaskResultDto,
  DeviceWorkspaceCreateInput,
  DeviceWorkspaceDto,
  DeviceWorkspaceUpdateInput,
  HealthCheckResultDto,
  PublishPlanCreateInput,
  PublishPlanDto,
  PublishPlanUpdateInput,
  PrecheckResultDto,
  SubmitPlanResultDto,
  RenderTaskCreateInput,
  RenderTaskDto,
  RenderTaskUpdateInput,
  CancelRenderResultDto,
  ReviewSummaryDto,
  ReviewSummaryUpdateInput,
  AnalyzeProjectResultDto
} from "@/types/runtime";
import type { TaskInfo } from "@/types/task-events";
import type { ImportedVideo } from "@/types/video";

const DEFAULT_RUNTIME_BASE_URL = "http://127.0.0.1:8000";

function resolveRuntimeBaseUrl(): string {
  return import.meta.env.VITE_RUNTIME_BASE_URL?.trim() || DEFAULT_RUNTIME_BASE_URL;
}

export class RuntimeRequestError extends Error {
  details: unknown;
  requestId: string;
  status: number;

  constructor(message: string, shape: Partial<RuntimeRequestErrorShape> = {}) {
    super(message);
    this.name = "RuntimeRequestError";
    this.details = shape.details;
    this.requestId = shape.requestId ?? "";
    this.status = shape.status ?? 0;
  }
}

export async function fetchRuntimeHealth(): Promise<RuntimeHealthSnapshot> {
  return requestRuntime<RuntimeHealthSnapshot>("/api/settings/health");
}

export async function fetchRuntimeConfig(): Promise<AppSettings> {
  return requestRuntime<AppSettings>("/api/settings/config");
}

export async function updateRuntimeConfig(
  input: AppSettingsUpdateInput
): Promise<AppSettings> {
  return requestRuntime<AppSettings>("/api/settings/config", {
    body: JSON.stringify(input),
    method: "PUT"
  });
}

export async function fetchRuntimeDiagnostics(): Promise<RuntimeDiagnostics> {
  return requestRuntime<RuntimeDiagnostics>("/api/settings/diagnostics");
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  return requestRuntime<DashboardSummary>("/api/dashboard/summary");
}

export async function createDashboardProject(
  input: CreateProjectInput
): Promise<DashboardSummary["recentProjects"][number]> {
  return requestRuntime<DashboardSummary["recentProjects"][number]>("/api/dashboard/projects", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function fetchCurrentProjectContext(): Promise<CurrentProjectContext | null> {
  return requestRuntime<CurrentProjectContext | null>("/api/dashboard/context");
}

export async function updateCurrentProjectContext(
  projectId: string
): Promise<CurrentProjectContext> {
  return requestRuntime<CurrentProjectContext>("/api/dashboard/context", {
    body: JSON.stringify({ projectId }),
    method: "PUT"
  });
}

export async function fetchLicenseStatus(): Promise<LicenseStatus> {
  return requestRuntime<LicenseStatus>("/api/license/status");
}

export async function activateLicense(input: LicenseActivationInput): Promise<LicenseStatus> {
  return requestRuntime<LicenseStatus>("/api/license/activate", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function fetchAICapabilitySettings(): Promise<AICapabilitySettings> {
  return requestRuntime<AICapabilitySettings>("/api/settings/ai-capabilities");
}

export async function updateAICapabilitySettings(
  capabilities: AICapabilitySettings["capabilities"]
): Promise<AICapabilitySettings> {
  return requestRuntime<AICapabilitySettings>("/api/settings/ai-capabilities", {
    body: JSON.stringify({ capabilities }),
    method: "PUT"
  });
}

export async function updateAIProviderSecret(
  providerId: string,
  input: AIProviderSecretInput
): Promise<AIProviderSecretStatus> {
  return requestRuntime<AIProviderSecretStatus>(
    `/api/settings/ai-capabilities/providers/${providerId}/secret`,
    {
      body: JSON.stringify(input),
      method: "PUT"
    }
  );
}

export async function checkAIProviderHealth(
  providerId: string,
  input: AIProviderHealthInput = {}
): Promise<AIProviderHealth> {
  return requestRuntime<AIProviderHealth>(
    `/api/settings/ai-capabilities/providers/${providerId}/health-check`,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}

export async function fetchAIProviderCatalog(): Promise<AIProviderCatalogItem[]> {
  return requestRuntime<AIProviderCatalogItem[]>("/api/settings/ai-providers/catalog");
}

export async function fetchAIProviderModels(providerId: string): Promise<AIModelCatalogItem[]> {
  return requestRuntime<AIModelCatalogItem[]>(
    `/api/settings/ai-providers/${providerId}/models`
  );
}

export async function fetchAICapabilitySupportMatrix(): Promise<AICapabilitySupportMatrix> {
  return requestRuntime<AICapabilitySupportMatrix>(
    "/api/settings/ai-capabilities/support-matrix"
  );
}

export async function refreshAIProviderModels(
  providerId: string
): Promise<AIModelCatalogRefreshResult> {
  return requestRuntime<AIModelCatalogRefreshResult>(
    `/api/settings/ai-providers/${providerId}/models/refresh`,
    {
      method: "POST"
    }
  );
}

export async function fetchScriptDocument(projectId: string): Promise<ScriptDocument> {
  return requestRuntime<ScriptDocument>(`/api/scripts/projects/${projectId}/document`);
}

export async function saveScriptDocument(
  projectId: string,
  content: string
): Promise<ScriptDocument> {
  return requestRuntime<ScriptDocument>(`/api/scripts/projects/${projectId}/document`, {
    body: JSON.stringify({ content }),
    method: "PUT"
  });
}

export async function generateScriptDocument(
  projectId: string,
  topic: string
): Promise<ScriptDocument> {
  return requestRuntime<ScriptDocument>(`/api/scripts/projects/${projectId}/generate`, {
    body: JSON.stringify({ topic }),
    method: "POST"
  });
}

export async function rewriteScriptDocument(
  projectId: string,
  instructions: string
): Promise<ScriptDocument> {
  return requestRuntime<ScriptDocument>(`/api/scripts/projects/${projectId}/rewrite`, {
    body: JSON.stringify({ instructions }),
    method: "POST"
  });
}

export async function fetchStoryboardDocument(projectId: string): Promise<StoryboardDocument> {
  return requestRuntime<StoryboardDocument>(`/api/storyboards/projects/${projectId}/document`);
}

export async function saveStoryboardDocument(
  projectId: string,
  basedOnScriptRevision: number,
  scenes: StoryboardScene[]
): Promise<StoryboardDocument> {
  return requestRuntime<StoryboardDocument>(`/api/storyboards/projects/${projectId}/document`, {
    body: JSON.stringify({ basedOnScriptRevision, scenes }),
    method: "PUT"
  });
}

export async function generateStoryboardDocument(projectId: string): Promise<StoryboardDocument> {
  return requestRuntime<StoryboardDocument>(`/api/storyboards/projects/${projectId}/generate`, {
    method: "POST"
  });
}

// Voice studio
export async function fetchVoiceProfiles(): Promise<VoiceProfileDto[]> {
  return requestRuntime<VoiceProfileDto[]>("/api/voice/profiles");
}

export async function fetchVoiceTracks(projectId: string): Promise<VoiceTrackDto[]> {
  return requestRuntime<VoiceTrackDto[]>(`/api/voice/projects/${projectId}/tracks`);
}

export async function generateVoiceTrack(
  projectId: string,
  input: VoiceTrackGenerateInput
): Promise<VoiceTrackGenerateResultDto> {
  return requestRuntime<VoiceTrackGenerateResultDto>(
    `/api/voice/projects/${projectId}/tracks/generate`,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}

export async function fetchVoiceTrack(trackId: string): Promise<VoiceTrackDto> {
  return requestRuntime<VoiceTrackDto>(`/api/voice/tracks/${trackId}`);
}

export async function deleteVoiceTrack(trackId: string): Promise<void> {
  return requestRuntime<void>(`/api/voice/tracks/${trackId}`, {
    method: "DELETE"
  });
}

// Subtitle alignment center
export async function fetchSubtitleTracks(projectId: string): Promise<SubtitleTrackDto[]> {
  return requestRuntime<SubtitleTrackDto[]>(`/api/subtitles/projects/${projectId}/tracks`);
}

export async function generateSubtitleTrack(
  projectId: string,
  input: SubtitleTrackGenerateInput
): Promise<SubtitleTrackGenerateResultDto> {
  return requestRuntime<SubtitleTrackGenerateResultDto>(
    `/api/subtitles/projects/${projectId}/tracks/generate`,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}

export async function fetchSubtitleTrack(trackId: string): Promise<SubtitleTrackDto> {
  return requestRuntime<SubtitleTrackDto>(`/api/subtitles/tracks/${trackId}`);
}

export async function updateSubtitleTrack(
  trackId: string,
  input: SubtitleTrackUpdateInput
): Promise<SubtitleTrackDto> {
  return requestRuntime<SubtitleTrackDto>(`/api/subtitles/tracks/${trackId}`, {
    body: JSON.stringify(input),
    method: "PATCH"
  });
}

export async function deleteSubtitleTrack(trackId: string): Promise<void> {
  return requestRuntime<void>(`/api/subtitles/tracks/${trackId}`, {
    method: "DELETE"
  });
}

export async function fetchImportedVideos(projectId: string): Promise<ImportedVideo[]> {
  return requestRuntime<ImportedVideo[]>(
    `/api/video-deconstruction/projects/${projectId}/videos`
  );
}

export async function importVideo(projectId: string, filePath: string): Promise<ImportedVideo> {
  return requestRuntime<ImportedVideo>(
    `/api/video-deconstruction/projects/${projectId}/import`,
    {
      body: JSON.stringify({ filePath }),
      method: "POST"
    }
  );
}

export async function deleteImportedVideo(videoId: string): Promise<void> {
  return requestRuntime<void>(`/api/video-deconstruction/videos/${videoId}`, {
    method: "DELETE"
  });
}

// Assets
export async function fetchAssets(type?: string, q?: string): Promise<AssetDto[]> {
  const params = new URLSearchParams();
  if (type) params.append("type", type);
  if (q) params.append("q", q);
  const query = params.toString();
  return requestRuntime<AssetDto[]>(`/api/assets${query ? `?${query}` : ""}`);
}

export async function importAsset(input: AssetImportInput): Promise<AssetDto> {
  return requestRuntime<AssetDto>("/api/assets/import", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function fetchAsset(id: string): Promise<AssetDto> {
  return requestRuntime<AssetDto>(`/api/assets/${id}`);
}

export async function updateAsset(id: string, input: AssetUpdateInput): Promise<AssetDto> {
  return requestRuntime<AssetDto>(`/api/assets/${id}`, {
    body: JSON.stringify(input),
    method: "PATCH"
  });
}

export async function deleteAsset(id: string): Promise<AssetDeleteResult> {
  return requestRuntime<AssetDeleteResult>(`/api/assets/${id}`, {
    method: "DELETE"
  });
}

export async function fetchAssetReferences(id: string): Promise<AssetReferenceDto[]> {
  return requestRuntime<AssetReferenceDto[]>(`/api/assets/${id}/references`);
}

// Accounts
export async function fetchAccounts(groupId?: string, status?: string, q?: string): Promise<AccountDto[]> {
  const params = new URLSearchParams();
  if (groupId) params.append("group_id", groupId);
  if (status) params.append("status", status);
  if (q) params.append("q", q);
  const query = params.toString();
  return requestRuntime<AccountDto[]>(`/api/accounts${query ? `?${query}` : ""}`);
}

export async function createAccount(input: AccountCreateInput): Promise<AccountDto> {
  return requestRuntime<AccountDto>("/api/accounts", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function deleteAccount(id: string): Promise<void> {
  return requestRuntime<void>(`/api/accounts/${id}`, {
    method: "DELETE"
  });
}

export async function fetchAccountGroups(): Promise<AccountGroupDto[]> {
  return requestRuntime<AccountGroupDto[]>("/api/accounts/groups");
}

export async function refreshAccountStats(id: string): Promise<void> {
  return requestRuntime<void>(`/api/accounts/${id}/refresh-stats`, {
    method: "POST"
  });
}

// Automation
export async function fetchAutomationTasks(
  status?: string,
  type?: string
): Promise<AutomationTaskDto[]> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (type) params.append("type", type);
  const query = params.toString();
  return requestRuntime<AutomationTaskDto[]>(
    `/api/automation/tasks${query ? `?${query}` : ""}`
  );
}

export async function createAutomationTask(
  input: AutomationTaskCreateInput
): Promise<AutomationTaskDto> {
  return requestRuntime<AutomationTaskDto>("/api/automation/tasks", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function fetchAutomationTask(id: string): Promise<AutomationTaskDto> {
  return requestRuntime<AutomationTaskDto>(`/api/automation/tasks/${id}`);
}

export async function updateAutomationTask(
  id: string,
  input: AutomationTaskUpdateInput
): Promise<AutomationTaskDto> {
  return requestRuntime<AutomationTaskDto>(`/api/automation/tasks/${id}`, {
    body: JSON.stringify(input),
    method: "PATCH"
  });
}

export async function deleteAutomationTask(id: string): Promise<void> {
  return requestRuntime<void>(`/api/automation/tasks/${id}`, {
    method: "DELETE"
  });
}

export async function triggerAutomationTask(id: string): Promise<TriggerTaskResultDto> {
  return requestRuntime<TriggerTaskResultDto>(`/api/automation/tasks/${id}/trigger`, {
    method: "POST"
  });
}

export async function fetchAutomationTaskRuns(id: string): Promise<AutomationTaskRunDto[]> {
  return requestRuntime<AutomationTaskRunDto[]>(`/api/automation/tasks/${id}/runs`);
}

// Device workspaces
export async function fetchDeviceWorkspaces(): Promise<DeviceWorkspaceDto[]> {
  return requestRuntime<DeviceWorkspaceDto[]>("/api/devices/workspaces");
}

export async function createDeviceWorkspace(
  input: DeviceWorkspaceCreateInput
): Promise<DeviceWorkspaceDto> {
  return requestRuntime<DeviceWorkspaceDto>("/api/devices/workspaces", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function fetchDeviceWorkspace(id: string): Promise<DeviceWorkspaceDto> {
  return requestRuntime<DeviceWorkspaceDto>(`/api/devices/workspaces/${id}`);
}

export async function updateDeviceWorkspace(
  id: string,
  input: DeviceWorkspaceUpdateInput
): Promise<DeviceWorkspaceDto> {
  return requestRuntime<DeviceWorkspaceDto>(`/api/devices/workspaces/${id}`, {
    body: JSON.stringify(input),
    method: "PATCH"
  });
}

export async function deleteDeviceWorkspace(id: string): Promise<void> {
  return requestRuntime<void>(`/api/devices/workspaces/${id}`, {
    method: "DELETE"
  });
}

export async function checkDeviceWorkspaceHealth(id: string): Promise<HealthCheckResultDto> {
  return requestRuntime<HealthCheckResultDto>(`/api/devices/workspaces/${id}/health-check`, {
    method: "POST"
  });
}

// Publishing
export async function fetchPublishPlans(status?: string): Promise<PublishPlanDto[]> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  const query = params.toString();
  return requestRuntime<PublishPlanDto[]>(
    `/api/publishing/plans${query ? `?${query}` : ""}`
  );
}

export async function createPublishPlan(input: PublishPlanCreateInput): Promise<PublishPlanDto> {
  return requestRuntime<PublishPlanDto>("/api/publishing/plans", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function fetchPublishPlan(id: string): Promise<PublishPlanDto> {
  return requestRuntime<PublishPlanDto>(`/api/publishing/plans/${id}`);
}

export async function updatePublishPlan(
  id: string,
  input: PublishPlanUpdateInput
): Promise<PublishPlanDto> {
  return requestRuntime<PublishPlanDto>(`/api/publishing/plans/${id}`, {
    body: JSON.stringify(input),
    method: "PATCH"
  });
}

export async function deletePublishPlan(id: string): Promise<void> {
  return requestRuntime<void>(`/api/publishing/plans/${id}`, {
    method: "DELETE"
  });
}

export async function runPublishingPrecheck(id: string): Promise<PrecheckResultDto> {
  return requestRuntime<PrecheckResultDto>(`/api/publishing/plans/${id}/precheck`, {
    method: "POST"
  });
}

export async function submitPublishPlan(id: string): Promise<SubmitPlanResultDto> {
  return requestRuntime<SubmitPlanResultDto>(`/api/publishing/plans/${id}/submit`, {
    method: "POST"
  });
}

export async function cancelPublishPlan(id: string): Promise<PublishPlanDto> {
  return requestRuntime<PublishPlanDto>(`/api/publishing/plans/${id}/cancel`, {
    method: "POST"
  });
}

// Renders
export async function fetchRenderTasks(status?: string): Promise<RenderTaskDto[]> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  const query = params.toString();
  return requestRuntime<RenderTaskDto[]>(`/api/renders/tasks${query ? `?${query}` : ""}`);
}

export async function createRenderTask(input: RenderTaskCreateInput): Promise<RenderTaskDto> {
  return requestRuntime<RenderTaskDto>("/api/renders/tasks", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function fetchRenderTask(id: string): Promise<RenderTaskDto> {
  return requestRuntime<RenderTaskDto>(`/api/renders/tasks/${id}`);
}

export async function updateRenderTask(
  id: string,
  input: RenderTaskUpdateInput
): Promise<RenderTaskDto> {
  return requestRuntime<RenderTaskDto>(`/api/renders/tasks/${id}`, {
    body: JSON.stringify(input),
    method: "PATCH"
  });
}

export async function deleteRenderTask(id: string): Promise<void> {
  return requestRuntime<void>(`/api/renders/tasks/${id}`, {
    method: "DELETE"
  });
}

export async function cancelRenderTask(id: string): Promise<CancelRenderResultDto> {
  return requestRuntime<CancelRenderResultDto>(`/api/renders/tasks/${id}/cancel`, {
    method: "POST"
  });
}

// Review
export async function fetchReviewSummary(projectId: string): Promise<ReviewSummaryDto> {
  return requestRuntime<ReviewSummaryDto>(`/api/review/projects/${projectId}/summary`);
}

export async function analyzeReviewProject(projectId: string): Promise<AnalyzeProjectResultDto> {
  return requestRuntime<AnalyzeProjectResultDto>(`/api/review/projects/${projectId}/analyze`, {
    method: "POST"
  });
}

export async function updateReviewSummary(
  projectId: string,
  input: ReviewSummaryUpdateInput
): Promise<ReviewSummaryDto> {
  return requestRuntime<ReviewSummaryDto>(`/api/review/projects/${projectId}/summary`, {
    body: JSON.stringify(input),
    method: "PATCH"
  });
}

export async function fetchActiveTasks(): Promise<TaskInfo[]> {
  return requestRuntime<TaskInfo[]>("/api/tasks");
}

export async function fetchTaskStatus(taskId: string): Promise<TaskInfo> {
  return requestRuntime<TaskInfo>(`/api/tasks/${taskId}`);
}

export async function cancelTask(
  taskId: string
): Promise<{ task_id: string; status: string; message: string }> {
  return requestRuntime<{ task_id: string; status: string; message: string }>(
    `/api/tasks/${taskId}/cancel`,
    {
      method: "POST"
    }
  );
}

async function requestRuntime<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${resolveRuntimeBaseUrl()}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers ?? {})
    }
  });

  const payload = await readEnvelope<T>(response);

  if (!response.ok) {
    throw toRuntimeRequestError(
      payload,
      response.status,
      `Runtime request failed (HTTP ${response.status}).`
    );
  }

  if (!payload || !payload.ok) {
    throw toRuntimeRequestError(payload, response.status, "Runtime request failed.");
  }

  return payload.data;
}

async function readEnvelope<T>(response: Response): Promise<RuntimeEnvelope<T> | null> {
  try {
    return (await response.json()) as RuntimeEnvelope<T>;
  } catch {
    return null;
  }
}

function toRuntimeRequestError(
  payload: RuntimeEnvelope<unknown> | null,
  status: number,
  fallbackMessage: string
): RuntimeRequestError {
  if (payload && !payload.ok) {
    return new RuntimeRequestError(payload.error, {
      details: payload.details,
      requestId: payload.requestId,
      status
    });
  }

  return new RuntimeRequestError(fallbackMessage, { status });
}
