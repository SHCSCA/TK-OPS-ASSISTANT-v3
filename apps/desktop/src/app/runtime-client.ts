import type {
  AICapabilityBindingInput,
  AICapabilitySettings,
  AICapabilitySupportMatrix,
  AIModelCatalogItem,
  AIModelCatalogRefreshResult,
  AIProviderCatalogItem,
  AIProviderHealth,
  AIProviderHealthOverview,
  AIProviderHealthInput,
  AIProviderSecretInput,
  AIProviderSecretStatus,
  AppSettings,
  AppSettingsUpdateInput,
  BootstrapDirectoryReport,
  CreateProjectInput,
  CurrentProjectContext,
  DashboardSummary,
  DiagnosticsBundleDto,
  GlobalSearchResult,
  LicenseActivationInput,
  LicenseStatus,
  LogFilter,
  LogPageDto,
  MediaDiagnostics,
  RuntimeDiagnostics,
  RuntimeEnvelope,
  RuntimeRequestErrorShape,
  RuntimeHealthSnapshot,
  RuntimeSelfCheckReport,
  ScriptDocument,
  ScriptSegmentDto,
  ScriptSegmentRewriteInput,
  ScriptTitleVariantDto,
  ScriptTitleVariantsInput,
  StoryboardDocument,
  StoryboardScene,
  StoryboardShotDto,
  StoryboardShotInput,
  StoryboardShotUpdateInput,
  StoryboardTemplateDto,
  SubtitleExportDto,
  WorkspaceAICommandInput,
  WorkspaceAICommandResultDto,
  WorkspaceClipDetailDto,
  MoveWorkspaceClipInput,
  ReplaceWorkspaceClipInput,
  TimelinePreviewDto,
  TimelinePrecheckDto,
  TrimWorkspaceClipInput,
  WorkspaceTimelineCreateInput,
  WorkspaceTimelineResultDto,
  WorkspaceTimelineUpdateInput,
  PromptTemplateDto,
  PromptTemplateInput,
  PromptTemplateUpdateInput,
  SubtitleTrackDto,
  SubtitleTrackGenerateInput,
  SubtitleTrackGenerateResultDto,
  SubtitleManualAlignInput,
  SubtitleStyleTemplateDto,
  SubtitleTrackUpdateInput,
  VoiceProfileDto,
  VoiceProfileInput,
  VoiceSegmentRegenerateInput,
  VoiceTrackDto,
  VoiceTrackGenerateInput,
  VoiceTrackGenerateResultDto,
  VoiceWaveformDto,
  AssetDeleteResult,
  AssetDto,
  AssetBatchDeleteResultDto,
  AssetBatchMoveResultDto,
  AssetGroupDto,
  AssetGroupInput,
  AssetGroupUpdateInput,
  AssetImportInput,
  AssetReferenceDto,
  AssetUpdateInput,
  AccountBindingDto,
  AccountBindingInput,
  AccountDto,
  AccountGroupDto,
  AccountCreateInput,
  ApplyVideoExtractionResultDto,
  AutomationTaskCreateInput,
  AutomationTaskDto,
  AutomationTaskRunDto,
  AutomationTaskUpdateInput,
  BrowserInstanceCreateInput,
  BrowserInstanceDto,
  BrowserInstanceWriteResultDto,
  TriggerTaskResultDto,
  DeviceWorkspaceCreateInput,
  DeviceWorkspaceLogDto,
  DeviceWorkspaceDto,
  DeviceWorkspaceUpdateInput,
  ExecutionBindingDto,
  ExportProfileCreateInput,
  ExportProfileDto,
  HealthCheckResultDto,
  PublishPlanCreateInput,
  PublishPlanDto,
  PublishReceiptDto,
  PublishPlanUpdateInput,
  PublishCalendarDto,
  PrecheckResultDto,
  SubmitPlanResultDto,
  RenderTaskCreateInput,
  RenderTaskDto,
  RenderResourceUsageDto,
  RenderTaskUpdateInput,
  CancelRenderResultDto,
  ReviewSummaryDto,
  ReviewSummaryUpdateInput,
  AnalyzeProjectResultDto,
  VideoDeconstructionResultDto,
  VideoStageDto,
  VideoSegmentDto,
  VideoStructureExtractionDto,
  VideoTranscriptDto
} from "@/types/runtime";
import type { TaskInfo } from "@/types/task-events";
import type { ImportedVideo } from "@/types/video";

const DEFAULT_RUNTIME_BASE_URL = "http://127.0.0.1:8000";

function resolveRuntimeBaseUrl(): string {
  return import.meta.env.VITE_RUNTIME_BASE_URL?.trim() || DEFAULT_RUNTIME_BASE_URL;
}

export class RuntimeRequestError extends Error {
  details: unknown;
  errorCode: string;
  requestId: string;
  status: number;

  constructor(message: string, shape: Partial<RuntimeRequestErrorShape> = {}) {
    super(message);
    this.name = "RuntimeRequestError";
    this.details = shape.details;
    this.errorCode = shape.errorCode ?? "";
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

export async function fetchRuntimeMediaDiagnostics(): Promise<MediaDiagnostics> {
  return requestRuntime<MediaDiagnostics>("/api/settings/diagnostics/media");
}

export async function initializeDirectories(): Promise<BootstrapDirectoryReport> {
  return requestRuntime<BootstrapDirectoryReport>("/api/bootstrap/initialize-directories", {
    method: "POST"
  });
}

export async function runtimeSelfCheck(): Promise<RuntimeSelfCheckReport> {
  return requestRuntime<RuntimeSelfCheckReport>("/api/bootstrap/runtime-selfcheck", {
    method: "POST"
  });
}

export async function fetchRuntimeLogs(filter: LogFilter = {}): Promise<LogPageDto> {
  const params = new URLSearchParams();
  if (filter.kind) {
    params.append("kind", filter.kind);
  }
  if (filter.since) {
    params.append("since", filter.since);
  }
  if (filter.level) {
    params.append("level", filter.level);
  }
  if (typeof filter.limit === "number") {
    params.append("limit", String(filter.limit));
  }
  const query = params.toString();
  return requestRuntime<LogPageDto>(`/api/settings/logs${query ? `?${query}` : ""}`);
}

export async function exportDiagnosticsBundle(): Promise<DiagnosticsBundleDto> {
  return requestRuntime<DiagnosticsBundleDto>("/api/settings/diagnostics/export", {
    method: "POST"
  });
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

export async function deleteDashboardProject(id: string): Promise<void> {
  return requestRuntime<void>(`/api/dashboard/projects/${id}`, { method: "DELETE" });
}

export async function fetchCurrentProjectContext(): Promise<CurrentProjectContext | null> {
  return requestRuntime<CurrentProjectContext | null>("/api/dashboard/context");
}

export async function updateCurrentProjectContext(
  projectId: string | null
): Promise<CurrentProjectContext | null> {
  return requestRuntime<CurrentProjectContext | null>("/api/dashboard/context", {
    body: JSON.stringify({ projectId }),
    method: "PUT"
  });
}

export async function searchGlobal(
  q: string,
  types?: string[],
  limit?: number
): Promise<GlobalSearchResult> {
  const params = new URLSearchParams();
  params.append("q", q);
  if (types && types.length > 0) {
    params.append("types", types.join(","));
  }
  if (typeof limit === "number") {
    params.append("limit", String(limit));
  }
  return requestRuntime<GlobalSearchResult>(`/api/search?${params.toString()}`);
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

export async function saveAICapabilitySettings(
  capabilities: AICapabilityBindingInput[]
): Promise<AICapabilitySettings> {
  return requestRuntime<AICapabilitySettings>("/api/settings/ai-capabilities", {
    body: JSON.stringify({ capabilities }),
    method: "PUT"
  });
}

export async function saveAIProviderSecret(
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

export async function fetchProviderHealth(): Promise<Record<string, AIProviderHealth>> {
  const overview = await requestRuntime<AIProviderHealthOverview>("/api/ai-providers/health");
  return Object.fromEntries(
    (overview.providers ?? []).map((item) => [
      item.provider,
      {
        provider: item.provider,
        status: item.readiness,
        message: item.errorMessage || item.label || item.readiness,
        checkedAt: item.lastCheckedAt ?? overview.refreshedAt ?? null,
        latencyMs: item.latencyMs ?? null,
        model: null
      } satisfies AIProviderHealth
    ])
  );
}

export async function fetchAIProviderCatalog(): Promise<AIProviderCatalogItem[]> {
  return requestRuntime<AIProviderCatalogItem[]>("/api/settings/ai-providers/catalog");
}

export async function fetchAIModelCatalog(providerId: string): Promise<AIModelCatalogItem[]> {
  return requestRuntime<AIModelCatalogItem[]>(
    `/api/settings/ai-providers/${providerId}/models`
  );
}

export async function fetchAIProviderModels(providerId: string): Promise<AIModelCatalogItem[]> {
  return fetchAIModelCatalog(providerId);
}

export async function upsertAIProviderModel(
  providerId: string,
  modelId: string,
  payload: import("../types/runtime").AIProviderModelUpsertInput
): Promise<import("../types/runtime").AIProviderModelWriteReceiptDto> {
  return requestRuntime<import("../types/runtime").AIProviderModelWriteReceiptDto>(
    `/api/ai-providers/${providerId}/models/${modelId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload)
    }
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

export async function generateScriptTitleVariants(
  projectId: string,
  input: ScriptTitleVariantsInput
): Promise<ScriptTitleVariantDto[]> {
  return requestRuntime<ScriptTitleVariantDto[]>(
    `/api/scripts/projects/${projectId}/title-variants`,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}

export async function listScriptVersions(projectId: string): Promise<ScriptDocument["versions"]> {
  return requestRuntime<ScriptDocument["versions"]>(`/api/scripts/projects/${projectId}/versions`);
}

export async function restoreScriptVersion(
  projectId: string,
  versionId: string
): Promise<ScriptDocument> {
  return requestRuntime<ScriptDocument>(
    `/api/scripts/projects/${projectId}/restore/${versionId}`,
    {
      method: "POST"
    }
  );
}

export async function rewriteScriptSegment(
  projectId: string,
  segmentId: string,
  input: ScriptSegmentRewriteInput
): Promise<ScriptSegmentDto> {
  return requestRuntime<ScriptSegmentDto>(
    `/api/scripts/projects/${projectId}/segments/${segmentId}/rewrite`,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}

export async function listPromptTemplates(kind?: string): Promise<PromptTemplateDto[]> {
  const params = new URLSearchParams();
  if (kind) {
    params.append("kind", kind);
  }
  const query = params.toString();
  return requestRuntime<PromptTemplateDto[]>(
    `/api/prompt-templates${query ? `?${query}` : ""}`
  );
}

export async function createPromptTemplate(
  input: PromptTemplateInput
): Promise<PromptTemplateDto> {
  return requestRuntime<PromptTemplateDto>("/api/prompt-templates", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function updatePromptTemplate(
  templateId: string,
  input: PromptTemplateUpdateInput
): Promise<PromptTemplateDto> {
  return requestRuntime<PromptTemplateDto>(`/api/prompt-templates/${templateId}`, {
    body: JSON.stringify(input),
    method: "PUT"
  });
}

export async function deletePromptTemplate(templateId: string): Promise<void> {
  return requestRuntime<void>(`/api/prompt-templates/${templateId}`, {
    method: "DELETE"
  });
}

export async function fetchStoryboardDocument(projectId: string): Promise<StoryboardDocument> {
  return requestRuntime<StoryboardDocument>(`/api/storyboards/projects/${projectId}/document`);
}

export async function saveStoryboardDocument(
  projectId: string,
  basedOnScriptRevision: number,
  scenes: StoryboardScene[],
  markdown?: string | null,
  storyboardJson?: Record<string, unknown> | null
): Promise<StoryboardDocument> {
  return requestRuntime<StoryboardDocument>(`/api/storyboards/projects/${projectId}/document`, {
    body: JSON.stringify({ basedOnScriptRevision, markdown, scenes, storyboardJson }),
    method: "PUT"
  });
}

export async function generateStoryboardDocument(projectId: string): Promise<StoryboardDocument> {
  return requestRuntime<StoryboardDocument>(`/api/storyboards/projects/${projectId}/generate`, {
    method: "POST"
  });
}

export async function createStoryboardShot(
  projectId: string,
  input: StoryboardShotInput
): Promise<StoryboardShotDto> {
  return requestRuntime<StoryboardShotDto>(`/api/storyboards/projects/${projectId}/shots`, {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function updateStoryboardShot(
  projectId: string,
  shotId: string,
  input: StoryboardShotUpdateInput
): Promise<StoryboardShotDto> {
  return requestRuntime<StoryboardShotDto>(
    `/api/storyboards/projects/${projectId}/shots/${shotId}`,
    {
      body: JSON.stringify(input),
      method: "PATCH"
    }
  );
}

export async function deleteStoryboardShot(projectId: string, shotId: string): Promise<void> {
  return requestRuntime<void>(`/api/storyboards/projects/${projectId}/shots/${shotId}`, {
    method: "DELETE"
  });
}

export async function listStoryboardTemplates(): Promise<StoryboardTemplateDto[]> {
  return requestRuntime<StoryboardTemplateDto[]>("/api/storyboards/templates");
}

export async function syncStoryboardFromScript(
  projectId: string
): Promise<StoryboardDocument> {
  return requestRuntime<StoryboardDocument>(
    `/api/storyboards/projects/${projectId}/sync-from-script`,
    {
      method: "POST"
    }
  );
}

// AI editing workspace
export async function fetchWorkspaceClip(clipId: string): Promise<WorkspaceClipDetailDto> {
  return requestRuntime<WorkspaceClipDetailDto>(`/api/workspace/clips/${clipId}`);
}

export async function moveWorkspaceClip(
  clipId: string,
  input: MoveWorkspaceClipInput
): Promise<WorkspaceTimelineResultDto> {
  return requestRuntime<WorkspaceTimelineResultDto>(`/api/workspace/clips/${clipId}/move`, {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function trimWorkspaceClip(
  clipId: string,
  input: TrimWorkspaceClipInput
): Promise<WorkspaceTimelineResultDto> {
  return requestRuntime<WorkspaceTimelineResultDto>(`/api/workspace/clips/${clipId}/trim`, {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function replaceWorkspaceClip(
  clipId: string,
  input: ReplaceWorkspaceClipInput
): Promise<WorkspaceTimelineResultDto> {
  return requestRuntime<WorkspaceTimelineResultDto>(`/api/workspace/clips/${clipId}/replace`, {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function fetchTimelinePreview(
  timelineId: string
): Promise<TimelinePreviewDto> {
  return requestRuntime<TimelinePreviewDto>(`/api/workspace/timelines/${timelineId}/preview`);
}

export async function precheckTimeline(
  timelineId: string
): Promise<TimelinePrecheckDto> {
  return requestRuntime<TimelinePrecheckDto>(`/api/workspace/timelines/${timelineId}/precheck`, {
    method: "POST"
  });
}

export async function fetchWorkspaceTimeline(
  projectId: string
): Promise<WorkspaceTimelineResultDto> {
  return requestRuntime<WorkspaceTimelineResultDto>(
    `/api/workspace/projects/${projectId}/timeline`
  );
}

export async function createWorkspaceTimeline(
  projectId: string,
  input: WorkspaceTimelineCreateInput
): Promise<WorkspaceTimelineResultDto> {
  return requestRuntime<WorkspaceTimelineResultDto>(
    `/api/workspace/projects/${projectId}/timeline`,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}

export async function updateWorkspaceTimeline(
  timelineId: string,
  input: WorkspaceTimelineUpdateInput
): Promise<WorkspaceTimelineResultDto> {
  return requestRuntime<WorkspaceTimelineResultDto>(`/api/workspace/timelines/${timelineId}`, {
    body: JSON.stringify(input),
    method: "PATCH"
  });
}

export async function runWorkspaceAICommand(
  projectId: string,
  input: WorkspaceAICommandInput
): Promise<WorkspaceAICommandResultDto> {
  return requestRuntime<WorkspaceAICommandResultDto>(
    `/api/workspace/projects/${projectId}/ai-commands`,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}

// Voice studio
export async function fetchVoiceProfiles(): Promise<VoiceProfileDto[]> {
  return requestRuntime<VoiceProfileDto[]>("/api/voice/profiles");
}

export async function createVoiceProfile(
  input: VoiceProfileInput
): Promise<VoiceProfileDto> {
  return requestRuntime<VoiceProfileDto>("/api/voice/profiles", {
    body: JSON.stringify(input),
    method: "POST"
  });
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

export async function regenerateVoiceSegment(
  trackId: string,
  segmentId: string,
  input: VoiceSegmentRegenerateInput
): Promise<TaskInfo> {
  return normalizeTaskInfo(
    await requestRuntime<TaskInfo>(
      `/api/voice/tracks/${trackId}/segments/${segmentId}/regenerate`,
      {
        body: JSON.stringify(input),
        method: "POST"
      }
    )
  );
}

export async function fetchVoiceWaveform(trackId: string): Promise<VoiceWaveformDto> {
  return requestRuntime<VoiceWaveformDto>(`/api/voice/tracks/${trackId}/waveform`);
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

export async function alignSubtitleTrack(
  trackId: string,
  input: SubtitleManualAlignInput
): Promise<SubtitleTrackDto> {
  return requestRuntime<SubtitleTrackDto>(`/api/subtitles/tracks/${trackId}/align`, {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function listSubtitleStyleTemplates(): Promise<SubtitleStyleTemplateDto[]> {
  return requestRuntime<SubtitleStyleTemplateDto[]>("/api/subtitles/style-templates");
}

export async function exportSubtitleTrack(
  trackId: string,
  format: string
): Promise<SubtitleExportDto> {
  return requestRuntime<SubtitleExportDto>(`/api/subtitles/tracks/${trackId}/export`, {
    body: JSON.stringify({ format }),
    method: "POST"
  });
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

export async function listAssetGroups(): Promise<AssetGroupDto[]> {
  return requestRuntime<AssetGroupDto[]>("/api/assets/groups");
}

export async function createAssetGroup(input: AssetGroupInput): Promise<AssetGroupDto> {
  return requestRuntime<AssetGroupDto>("/api/assets/groups", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function updateAssetGroup(
  groupId: string,
  input: AssetGroupUpdateInput
): Promise<AssetGroupDto> {
  return requestRuntime<AssetGroupDto>(`/api/assets/groups/${groupId}`, {
    body: JSON.stringify(input),
    method: "PATCH"
  });
}

export async function deleteAssetGroup(groupId: string): Promise<void> {
  return requestRuntime<void>(`/api/assets/groups/${groupId}`, {
    method: "DELETE"
  });
}

export async function batchDeleteAssets(
  assetIds: string[]
): Promise<AssetBatchDeleteResultDto> {
  return requestRuntime<AssetBatchDeleteResultDto>("/api/assets/batch-delete", {
    body: JSON.stringify({ assetIds }),
    method: "POST"
  });
}

export async function batchMoveAssetsToGroup(
  assetIds: string[],
  groupId: string
): Promise<AssetBatchMoveResultDto> {
  return requestRuntime<AssetBatchMoveResultDto>("/api/assets/batch-move-group", {
    body: JSON.stringify({ assetIds, groupId }),
    method: "POST"
  });
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

export async function setAccountBinding(
  accountId: string,
  input: AccountBindingInput
): Promise<AccountBindingDto> {
  return requestRuntime<AccountBindingDto>(`/api/accounts/${accountId}/binding`, {
    body: JSON.stringify(input),
    method: "PUT"
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

export async function pauseAutomationTask(id: string): Promise<AutomationTaskDto> {
  return requestRuntime<AutomationTaskDto>(`/api/automation/tasks/${id}/pause`, {
    method: "POST"
  });
}

export async function resumeAutomationTask(id: string): Promise<AutomationTaskDto> {
  return requestRuntime<AutomationTaskDto>(`/api/automation/tasks/${id}/resume`, {
    method: "POST"
  });
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

export async function fetchWorkspaceLogs(
  workspaceId: string,
  since?: string
): Promise<DeviceWorkspaceLogDto[]> {
  const params = new URLSearchParams();
  if (since) {
    params.append("since", since);
  }
  const query = params.toString();
  return requestRuntime<DeviceWorkspaceLogDto[]>(
    `/api/devices/workspaces/${workspaceId}/logs${query ? `?${query}` : ""}`
  );
}

export async function fetchBrowserInstances(
  workspaceId: string
): Promise<BrowserInstanceDto[]> {
  return requestRuntime<BrowserInstanceDto[]>(
    `/api/devices/workspaces/${workspaceId}/browser-instances`
  );
}

export async function createBrowserInstance(
  workspaceId: string,
  input: BrowserInstanceCreateInput
): Promise<BrowserInstanceDto> {
  return requestRuntime<BrowserInstanceDto>(
    `/api/devices/workspaces/${workspaceId}/browser-instances`,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}

export async function startBrowserInstance(
  workspaceId: string,
  instanceId: string
): Promise<BrowserInstanceWriteResultDto> {
  return requestRuntime<BrowserInstanceWriteResultDto>(
    `/api/devices/workspaces/${workspaceId}/browser-instances/${instanceId}/start`,
    {
      method: "POST"
    }
  );
}

export async function stopBrowserInstance(
  workspaceId: string,
  instanceId: string
): Promise<BrowserInstanceWriteResultDto> {
  return requestRuntime<BrowserInstanceWriteResultDto>(
    `/api/devices/workspaces/${workspaceId}/browser-instances/${instanceId}/stop`,
    {
      method: "POST"
    }
  );
}

export async function checkBrowserInstanceHealth(
  workspaceId: string,
  instanceId: string
): Promise<BrowserInstanceWriteResultDto> {
  return requestRuntime<BrowserInstanceWriteResultDto>(
    `/api/devices/workspaces/${workspaceId}/browser-instances/${instanceId}/health-check`,
    {
      method: "POST"
    }
  );
}

export async function createLegacyDeviceWorkspaceViaBrowserAlias(
  input: DeviceWorkspaceCreateInput
): Promise<DeviceWorkspaceDto> {
  return requestRuntime<DeviceWorkspaceDto>("/api/devices/browser-instances", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function removeBrowserInstance(id: string): Promise<void> {
  return requestRuntime<void>(`/api/devices/browser-instances/${id}`, {
    method: "DELETE"
  });
}

export async function fetchExecutionBindings(): Promise<ExecutionBindingDto[]> {
  return requestRuntime<ExecutionBindingDto[]>("/api/devices/bindings");
}

export async function removeExecutionBinding(id: string): Promise<void> {
  return requestRuntime<void>(`/api/devices/bindings/${id}`, {
    method: "DELETE"
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

export async function fetchPublishReceipt(id: string): Promise<PublishReceiptDto> {
  return requestRuntime<PublishReceiptDto>(`/api/publishing/plans/${id}/receipt`);
}

export async function fetchPublishingCalendar(): Promise<PublishCalendarDto> {
  return requestRuntime<PublishCalendarDto>("/api/publishing/calendar");
}

export async function fetchPublishReceipts(id: string): Promise<PublishReceiptDto[]> {
  return requestRuntime<PublishReceiptDto[]>(`/api/publishing/plans/${id}/receipts`);
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

export async function fetchExportProfiles(): Promise<ExportProfileDto[]> {
  return requestRuntime<ExportProfileDto[]>("/api/renders/profiles");
}

export async function createExportProfile(
  input: ExportProfileCreateInput
): Promise<ExportProfileDto> {
  return requestRuntime<ExportProfileDto>("/api/renders/profiles", {
    body: JSON.stringify(input),
    method: "POST"
  });
}

export async function retryRenderTask(id: string): Promise<RenderTaskDto> {
  return requestRuntime<RenderTaskDto>(`/api/renders/tasks/${id}/retry`, {
    method: "POST"
  });
}

export async function listRenderTemplates(): Promise<ExportProfileDto[]> {
  return requestRuntime<ExportProfileDto[]>("/api/renders/templates");
}

export async function fetchRenderResourceUsage(): Promise<RenderResourceUsageDto> {
  return requestRuntime<RenderResourceUsageDto>("/api/renders/resource-usage");
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

export async function applyReviewSuggestionToScript(
  suggestionId: string
): Promise<DashboardSummary["recentProjects"][number]> {
  return requestRuntime<DashboardSummary["recentProjects"][number]>(
    `/api/review/suggestions/${suggestionId}/apply-to-script`,
    {
      method: "POST"
    }
  );
}

export async function adoptReviewSuggestion(
  projectId: string,
  suggestionId: string
): Promise<DashboardSummary["recentProjects"][number]> {
  return requestRuntime<DashboardSummary["recentProjects"][number]>(
    `/api/review/projects/${projectId}/suggestions/${suggestionId}/adopt`,
    {
      method: "POST"
    }
  );
}

export async function startVideoTranscription(videoId: string): Promise<VideoTranscriptDto> {
  return requestRuntime<VideoTranscriptDto>(
    `/api/video-deconstruction/videos/${videoId}/transcribe`,
    {
      method: "POST"
    }
  );
}

export async function fetchVideoTranscript(videoId: string): Promise<VideoTranscriptDto> {
  return requestRuntime<VideoTranscriptDto>(
    `/api/video-deconstruction/videos/${videoId}/transcript`
  );
}

export async function deconstructVideo(videoId: string): Promise<VideoDeconstructionResultDto> {
  return requestRuntime<VideoDeconstructionResultDto>(
    `/api/video-deconstruction/videos/${videoId}/deconstruct`,
    {
      method: "POST"
    }
  );
}

export async function fetchVideoResult(videoId: string): Promise<VideoDeconstructionResultDto> {
  return requestRuntime<VideoDeconstructionResultDto>(
    `/api/video-deconstruction/videos/${videoId}/result`
  );
}

export async function runVideoSegmentation(videoId: string): Promise<VideoSegmentDto[]> {
  return requestRuntime<VideoSegmentDto[]>(
    `/api/video-deconstruction/videos/${videoId}/segment`,
    {
      method: "POST"
    }
  );
}

export async function fetchVideoSegments(videoId: string): Promise<VideoSegmentDto[]> {
  return requestRuntime<VideoSegmentDto[]>(
    `/api/video-deconstruction/videos/${videoId}/segments`
  );
}

export async function fetchVideoStages(videoId: string): Promise<VideoStageDto[]> {
  return requestRuntime<VideoStageDto[]>(`/api/video-deconstruction/videos/${videoId}/stages`);
}

export async function rerunVideoStage(videoId: string, stageId: string): Promise<TaskInfo> {
  return normalizeTaskInfo(
    await requestRuntime<TaskInfo>(
      `/api/video-deconstruction/videos/${videoId}/stages/${stageId}/rerun`,
      {
        method: "POST"
      }
    )
  );
}

export async function extractVideoStructure(
  videoId: string
): Promise<VideoStructureExtractionDto> {
  return requestRuntime<VideoStructureExtractionDto>(
    `/api/video-deconstruction/videos/${videoId}/extract-structure`,
    {
      method: "POST"
    }
  );
}

export async function fetchVideoStructure(
  videoId: string
): Promise<VideoStructureExtractionDto> {
  return requestRuntime<VideoStructureExtractionDto>(
    `/api/video-deconstruction/videos/${videoId}/structure`
  );
}

export async function applyVideoExtractionToProject(
  extractionId: string
): Promise<ApplyVideoExtractionResultDto> {
  return requestRuntime<ApplyVideoExtractionResultDto>(
    `/api/video-deconstruction/extractions/${extractionId}/apply-to-project`,
    {
      method: "POST"
    }
  );
}

export async function fetchActiveTasks(): Promise<TaskInfo[]> {
  const tasks = await requestRuntime<TaskInfo[]>("/api/tasks");
  return tasks.map(normalizeTaskInfo);
}

export async function fetchTaskStatus(taskId: string): Promise<TaskInfo> {
  return normalizeTaskInfo(await requestRuntime<TaskInfo>(`/api/tasks/${taskId}`));
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
    return new RuntimeRequestError(normalizeRuntimeErrorMessage(payload.error, status), {
      details: payload.details,
      errorCode: payload.error_code,
      requestId: payload.requestId,
      status
    });
  }

  return new RuntimeRequestError(fallbackMessage, { status });
}

function normalizeRuntimeErrorMessage(message: string, status: number): string {
  if (status === 422 && message === "Request validation failed") {
    return "请求参数校验失败，请检查输入后重试。";
  }
  return message;
}

function normalizeTaskInfo(task: TaskInfo): TaskInfo {
  const anyTask = task as any;
  return {
    ...task,
    id: task.id,
    task_type: task.task_type || anyTask.kind || "generic",
    project_id: task.project_id || anyTask.projectId || null,
    progress: typeof task.progress === "number" ? task.progress : (anyTask.progressPct ?? 0),
    message: task.message || anyTask.label || "任务",
    status: task.status,
    created_at: task.created_at || anyTask.createdAt || "",
    updated_at: task.updated_at || anyTask.updatedAt || ""
  };
}
