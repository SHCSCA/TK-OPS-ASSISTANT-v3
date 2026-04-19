import type { TaskInfo } from "./task-events";

export type RuntimeHealthSnapshot = {
  runtime: {
    status: string;
    port: number;
    uptimeMs: number;
    version: string;
  };
  aiProvider: {
    status: string;
    latencyMs: number | null;
    providerId: string | null;
    providerName: string | null;
    lastChecked: string | null;
  };
  renderQueue: {
    running: number;
    queued: number;
    avgWaitMs: number | null;
  };
  publishingQueue: {
    pendingToday: number;
    failedToday: number;
  };
  taskBus: {
    running: number;
    queued: number;
    blocked: number;
    failed24h: number;
  };
  license: {
    status: string;
    expiresAt: string | null;
  };
  lastSyncAt: string;
  service: string;
  version: string;
  now: string;
  mode: string;
};

export type LicenseStatus = {
  active: boolean;
  restrictedMode: boolean;
  machineCode: string;
  machineBound: boolean;
  licenseType: string;
  maskedCode: string;
  activatedAt: string | null;
};

export type LicenseActivationInput = {
  activationCode: string;
};

export type AppSettings = {
  revision: number;
  runtime: {
    mode: string;
    workspaceRoot: string;
  };
  paths: {
    cacheDir: string;
    exportDir: string;
    logDir: string;
  };
  logging: {
    level: string;
  };
  ai: {
    provider: string;
    model: string;
    voice: string;
    subtitleMode: string;
  };
};

export type AppSettingsUpdateInput = Omit<AppSettings, "revision">;

export type RuntimeDiagnostics = {
  databasePath: string;
  logDir: string;
  revision: number;
  mode: string;
  healthStatus: string;
};

export type BootstrapDirectoryReport = {
  rootDir: string;
  databasePath: string;
  status: string;
  directories: Array<{
    key: string;
    label: string;
    path: string;
    exists: boolean;
    writable: boolean;
    status: string;
    message: string | null;
  }>;
  checkedAt: string;
};

export type RuntimeSelfCheckReport = {
  status: string;
  runtimeVersion: string;
  checkedAt: string;
  items: Array<{
    key: string;
    label: string;
    status: string;
    detail: string;
    errorCode: string | null;
    checkedAt: string;
  }>;
};

export type LogFilter = {
  kind?: string;
  since?: string;
  level?: string;
  limit?: number;
};

export type RuntimeLogEntry = {
  timestamp: string;
  level: string;
  kind: string;
  requestId: string;
  message: string;
  context: Record<string, unknown>;
};

export type LogPageDto = {
  items: RuntimeLogEntry[];
  nextCursor: string | null;
};

export type DiagnosticsBundleDto = {
  bundlePath: string;
  createdAt: string;
  entries: Array<{
    name: string;
    path: string;
    sizeBytes: number;
  }>;
};

export type ProjectSummary = {
  id: string;
  name: string;
  description: string;
  status: string;
  currentScriptVersion: number;
  currentStoryboardVersion: number;
  createdAt: string;
  updatedAt: string;
  lastAccessedAt: string;
};

export type CurrentProjectContext = {
  projectId: string;
  projectName: string;
  status: string;
};

export type DashboardSummary = {
  recentProjects: ProjectSummary[];
  currentProject: CurrentProjectContext | null;
  greeting: {
    title: string;
    subtitle: string;
  };
  heroContext: {
    currentProject: {
      id: string;
      name: string;
      status: string;
      lastEditedAt: string;
    } | null;
    primaryAction: {
      label: string;
      action: string;
      targetProjectId: string | null;
    };
    pendingTasks: number;
    blockingIssues: number;
  };
  todos: Array<{
    id: string;
    title: string;
    status: string;
  }>;
  exceptions: Array<{
    id: string;
    title: string;
    level: string;
    message: string;
  }>;
  health: {
    runtimeStatus: string;
    aiProviderStatus: string;
    taskBusStatus: string;
  };
  generatedAt: string;
};

export type CreateProjectInput = {
  name: string;
  description: string;
};

export type GlobalSearchResult = {
  projects: Array<{
    id: string;
    name: string;
    subtitle: string;
    updatedAt: string;
  }>;
  scripts: Array<{
    id: string;
    projectId: string;
    title: string;
    snippet: string;
    updatedAt: string;
  }>;
  tasks: Array<{
    id: string;
    kind: string;
    label: string;
    status: string;
    updatedAt: string;
  }>;
  assets: Array<{
    id: string;
    name: string;
    type: string;
    thumbnailUrl: string | null;
    updatedAt: string;
  }>;
  accounts: Array<{
    id: string;
    name: string;
    status: string;
  }>;
  workspaces: Array<{
    id: string;
    name: string;
    status: string;
  }>;
};

export type AICapabilityId =
  | "script_generation"
  | "script_rewrite"
  | "storyboard_generation"
  | "tts_generation"
  | "subtitle_alignment"
  | "video_generation"
  | "asset_analysis";

export type AICapabilityConfig = {
  capabilityId: AICapabilityId;
  enabled: boolean;
  provider: string;
  model: string;
  agentRole: string;
  systemPrompt: string;
  userPromptTemplate: string;
};

export type AIProviderSecretStatus = {
  provider: string;
  label: string;
  configured: boolean;
  maskedSecret: string;
  baseUrl: string;
  secretSource: string;
  supportsTextGeneration: boolean;
};

export type AIProviderHealth = {
  provider: string;
  status: string;
  message: string;
  model?: string | null;
  checkedAt?: string | null;
  latencyMs?: number | null;
};

export type AICapabilitySettings = {
  capabilities: AICapabilityConfig[];
  providers: AIProviderSecretStatus[];
};

export type AIProviderSecretInput = {
  apiKey: string;
  baseUrl?: string;
};

export type AIProviderHealthInput = {
  model?: string;
};

export type AIProviderCatalogItem = {
  provider: string;
  label: string;
  kind: string;
  configured: boolean;
  baseUrl: string;
  secretSource: string;
  capabilities: string[];
  requiresBaseUrl: boolean;
  supportsModelDiscovery: boolean;
  status: string;
};

export type AIModelCatalogItem = {
  modelId: string;
  displayName: string;
  provider: string;
  capabilityTypes: string[];
  inputModalities: string[];
  outputModalities: string[];
  contextWindow: number | null;
  defaultFor: string[];
  enabled: boolean;
};

export type AICapabilityModelOption = {
  provider: string;
  modelId: string;
  displayName: string;
  capabilityTypes: string[];
};

export type AICapabilitySupportItem = {
  capabilityId: string;
  providers: string[];
  models: AICapabilityModelOption[];
};

export type AICapabilitySupportMatrix = {
  capabilities: AICapabilitySupportItem[];
};

export type AIModelCatalogRefreshResult = {
  provider: string;
  status: string;
  message: string;
};

export type TaskStatus =
  | "draft"
  | "queued"
  | "running"
  | "blocked"
  | "succeeded"
  | "failed"
  | "cancelled";

export type AIJobRecord = {
  id: string;
  capabilityId: AICapabilityId | string;
  provider: string;
  model: string;
  status: TaskStatus;
  error: string | null;
  durationMs: number | null;
  createdAt: string;
  completedAt: string | null;
};

export type ScriptVersion = {
  revision: number;
  source: string;
  content: string;
  provider: string | null;
  model: string | null;
  aiJobId: string | null;
  createdAt: string;
};

export type ScriptDocument = {
  projectId: string;
  currentVersion: ScriptVersion | null;
  versions: ScriptVersion[];
  recentJobs: AIJobRecord[];
};

export type ScriptTitleVariantDto = {
  id: string;
  title: string;
  adopted: boolean;
};

export type ScriptTitleVariantsInput = {
  topic: string;
  count: number;
};

export type ScriptSegmentRewriteInput = {
  instructions: string;
};

export type ScriptSegmentDto = {
  id: string;
  segmentId: string;
  title: string;
  content: string;
};

export type PromptTemplateInput = {
  kind: string;
  name: string;
  template: string;
};

export type PromptTemplateUpdateInput = Partial<PromptTemplateInput>;

export type PromptTemplateDto = {
  id: string;
  kind: string;
  name: string;
  template: string;
  variables: string[];
  createdAt: string;
  updatedAt: string;
};

export type StoryboardScene = {
  sceneId: string;
  title: string;
  summary: string;
  visualPrompt: string;
};

export type StoryboardVersion = {
  revision: number;
  basedOnScriptRevision: number;
  source: string;
  scenes: StoryboardScene[];
  provider: string | null;
  model: string | null;
  aiJobId: string | null;
  createdAt: string;
};

export type StoryboardDocument = {
  projectId: string;
  basedOnScriptRevision: number;
  currentVersion: StoryboardVersion | null;
  versions: StoryboardVersion[];
  recentJobs: AIJobRecord[];
};

export type StoryboardShotInput = {
  title: string;
  summary: string;
  visualPrompt: string;
};

export type StoryboardShotUpdateInput = Partial<StoryboardShotInput>;

export type StoryboardShotDto = {
  id: string;
  title: string;
  summary: string;
  visualPrompt: string;
  orderIndex: number;
};

export type StoryboardTemplateDto = {
  id: string;
  name: string;
  sceneCount: number;
};

export type WorkspaceTimelineTrackKind = "video" | "audio" | "subtitle";

export type WorkspaceTimelineClipDto = {
  id: string;
  trackId: string;
  sourceType: string;
  sourceId: string | null;
  label: string;
  startMs: number;
  durationMs: number;
  inPointMs: number;
  outPointMs: number | null;
  status: string;
};

export type WorkspaceTimelineTrackDto = {
  id: string;
  kind: WorkspaceTimelineTrackKind;
  name: string;
  orderIndex: number;
  locked: boolean;
  muted: boolean;
  clips: WorkspaceTimelineClipDto[];
};

export type WorkspaceTimelineDto = {
  id: string;
  projectId: string;
  name: string;
  status: string;
  durationSeconds: number | null;
  source: string;
  tracks: WorkspaceTimelineTrackDto[];
  createdAt: string;
  updatedAt: string;
};

export type WorkspaceTimelineResultDto = {
  timeline: WorkspaceTimelineDto | null;
  message: string;
};

export type WorkspaceClipDetailDto = WorkspaceTimelineClipDto;

export type MoveWorkspaceClipInput = {
  targetTrackId: string;
  startMs: number;
};

export type TrimWorkspaceClipInput = {
  inPointMs: number;
  durationMs: number;
};

export type ReplaceWorkspaceClipInput = {
  assetId: string;
};

export type TimelinePreviewDto = {
  status: string;
  previewUrl: string | null;
};

export type TimelinePrecheckDto = {
  status: string;
  issues: Array<Record<string, unknown>>;
};

export type WorkspaceTimelineCreateInput = {
  name?: string;
};

export type WorkspaceTimelineUpdateInput = {
  name?: string | null;
  durationSeconds?: number | null;
  tracks: WorkspaceTimelineTrackDto[];
};

export type WorkspaceAICommandInput = {
  timelineId?: string | null;
  capabilityId: string;
  parameters?: Record<string, unknown>;
};

export type WorkspaceAICommandResultDto = {
  status: "blocked";
  task: TaskInfo | null;
  message: string;
};

export type VoiceTrackStatus = "blocked" | "ready" | "error" | "generating";

export type VoiceProfileDto = {
  id: string;
  provider: string;
  voiceId: string;
  displayName: string;
  locale: string;
  tags: string[];
  enabled: boolean;
};

export type VoiceProfileInput = Omit<VoiceProfileDto, "id">;

export type VoiceTrackSegmentDto = {
  segmentIndex: number;
  text: string;
  startMs: number | null;
  endMs: number | null;
  audioAssetId: string | null;
};

export type VoiceTrackDto = {
  id: string;
  projectId: string;
  timelineId: string | null;
  source: string;
  provider: string | null;
  voiceName: string;
  filePath: string | null;
  segments: VoiceTrackSegmentDto[];
  status: VoiceTrackStatus;
  createdAt: string;
};

export type VoiceTrackGenerateInput = {
  profileId: string;
  sourceText: string;
  speed: number;
  pitch: number;
  emotion: string;
};

export type VoiceTrackGenerateResultDto = {
  track: VoiceTrackDto;
  task: TaskInfo | null;
  message: string;
};

export type VoiceSegmentRegenerateInput = {
  instructions: string;
};

export type VoiceWaveformDto = {
  trackId: string;
  samples: number[];
};

export type SubtitleTrackStatus = "blocked" | "ready" | "error" | "aligning";

export type SubtitleStyleDto = {
  preset: string;
  fontSize: number;
  position: "bottom" | "center" | "top";
  textColor: string;
  background: string;
};

export type SubtitleSegmentDto = {
  segmentIndex: number;
  text: string;
  startMs: number | null;
  endMs: number | null;
  confidence: number | null;
  locked: boolean;
};

export type SubtitleTrackDto = {
  id: string;
  projectId: string;
  timelineId: string | null;
  source: "script" | "manual" | "provider";
  language: string;
  style: SubtitleStyleDto;
  segments: SubtitleSegmentDto[];
  status: SubtitleTrackStatus;
  createdAt: string;
};

export type SubtitleTrackGenerateInput = {
  sourceText: string;
  language: string;
  stylePreset: string;
};

export type SubtitleTrackUpdateInput = {
  segments: SubtitleSegmentDto[];
  style: SubtitleStyleDto;
};

export type SubtitleTrackGenerateResultDto = {
  track: SubtitleTrackDto;
  task: TaskInfo | null;
  message: string;
};

export type SubtitleManualAlignInput = {
  segments: Array<{
    segmentIndex: number;
    startMs: number;
    endMs: number;
  }>;
};

export type SubtitleStyleTemplateDto = {
  id: string;
  name: string;
};

export type SubtitleExportDto = {
  trackId: string;
  format: string;
  filePath: string;
};

export type AssetDto = {
  id: string;
  name: string;
  type: string;
  source: string;
  filePath: string | null;
  fileSizeBytes: number | null;
  durationMs: number | null;
  thumbnailPath: string | null;
  tags: string | null;
  projectId: string | null;
  metadataJson: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AssetImportInput = {
  filePath: string;
  type: string;
  source?: string;
  projectId?: string | null;
  tags?: string | null;
  metadataJson?: string | null;
};

export type AssetUpdateInput = {
  name?: string | null;
  type?: string | null;
  source?: string | null;
  filePath?: string | null;
  fileSizeBytes?: number | null;
  durationMs?: number | null;
  thumbnailPath?: string | null;
  tags?: string | null;
  projectId?: string | null;
  metadataJson?: string | null;
};

export type AssetDeleteResult = {
  deleted: boolean;
};

export type AssetReferenceDto = {
  id: string;
  assetId: string;
  referenceType: string;
  referenceId: string;
  createdAt: string;
};

export type AssetGroupDto = {
  id: string;
  name: string;
  parentId: string | null;
};

export type AssetGroupInput = {
  name: string;
  parentId: string | null;
};

export type AssetGroupUpdateInput = Partial<AssetGroupInput>;

export type AssetBatchDeleteResultDto = {
  deletedIds: string[];
};

export type AssetBatchMoveResultDto = {
  movedIds: string[];
  groupId: string;
};

export type AccountDto = {
  id: string;
  name: string;
  platform: string;
  username: string | null;
  avatarUrl: string | null;
  status: string;
  authExpiresAt: string | null;
  followerCount: number | null;
  followingCount: number | null;
  videoCount: number | null;
  tags: string | null;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AccountGroupDto = {
  id: string;
  name: string;
  description: string | null;
  color: string | null;
  createdAt: string;
};

export type AccountCreateInput = {
  name: string;
  platform: string;
  username?: string;
  avatarUrl?: string;
  status: string;
};

export type AccountBindingInput = {
  deviceWorkspaceId: string;
  browserInstanceId?: string | null;
};

export type AccountBindingDto = {
  id: string;
  accountId: string;
  deviceWorkspaceId: string;
  browserInstanceId: string | null;
  status: string;
};

export type AutomationTaskCreateInput = {
  name: string;
  type: string;
  cron_expr?: string | null;
  config_json?: string | null;
};

export type AutomationTaskUpdateInput = {
  name?: string | null;
  type?: string | null;
  enabled?: boolean | null;
  cron_expr?: string | null;
  config_json?: string | null;
};

export type AutomationTaskDto = {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  cron_expr: string | null;
  last_run_at: string | null;
  last_run_status: string | null;
  run_count: number;
  config_json: string | null;
  created_at: string;
  updated_at: string;
};

export type AutomationTaskRunDto = {
  id: string;
  task_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  log_text: string | null;
  created_at: string;
};

export type TriggerTaskResultDto = {
  task_id: string;
  run_id: string;
  status: string;
  message: string;
};

export type DeviceWorkspaceCreateInput = {
  name: string;
  root_path: string;
};

export type DeviceWorkspaceUpdateInput = {
  name?: string | null;
  root_path?: string | null;
  status?: string | null;
};

export type DeviceWorkspaceDto = {
  id: string;
  name: string;
  root_path: string;
  status: string;
  error_count: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
};

export type HealthCheckResultDto = {
  workspace_id: string;
  status: string;
  checked_at: string;
};

export type BrowserInstanceCreateInput = {
  workspace_id: string;
  name: string;
  profile_path: string;
  browser_type: string;
};

export type BrowserInstanceDto = {
  id: string;
  workspace_id: string;
  name: string;
  profile_path: string;
  browser_type: string;
  status: string;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ExecutionBindingDto = {
  id: string;
  account_id: string;
  device_workspace_id: string;
  browser_instance_id: string | null;
  status: string;
  source: string | null;
  metadata_json: string | null;
  created_at: string;
  updated_at: string;
};

export type PublishPlanCreateInput = {
  title: string;
  account_id?: string | null;
  account_name?: string | null;
  project_id?: string | null;
  video_asset_id?: string | null;
  scheduled_at?: string | null;
};

export type PublishPlanUpdateInput = {
  title?: string | null;
  account_name?: string | null;
  status?: string | null;
  scheduled_at?: string | null;
};

export type PublishPlanDto = {
  id: string;
  title: string;
  account_id: string | null;
  account_name: string | null;
  project_id: string | null;
  video_asset_id: string | null;
  status: string;
  scheduled_at: string | null;
  submitted_at: string | null;
  published_at: string | null;
  error_message: string | null;
  precheck_result_json: string | null;
  created_at: string;
  updated_at: string;
};

export type PrecheckItemResult = {
  code: string;
  label: string;
  result: string;
  message?: string | null;
};

export type PrecheckResultDto = {
  plan_id: string;
  items: PrecheckItemResult[];
  has_errors: boolean;
  checked_at: string;
};

export type SubmitPlanResultDto = {
  plan_id: string;
  status: string;
  submitted_at: string;
  message: string;
};

export type PublishReceiptDto = {
  id: string;
  plan_id: string;
  status: string;
  external_url: string | null;
  error_message: string | null;
  completed_at: string | null;
  created_at: string;
};

export type PublishingCalendarDayDto = {
  date: string;
  plans: number;
};

export type RenderTaskCreateInput = {
  project_id?: string | null;
  project_name?: string | null;
  preset?: string;
  format?: string;
};

export type RenderTaskUpdateInput = {
  preset?: string | null;
  format?: string | null;
  status?: string | null;
  progress?: number | null;
  output_path?: string | null;
  error_message?: string | null;
};

export type RenderTaskDto = {
  id: string;
  project_id: string | null;
  project_name: string | null;
  preset: string;
  format: string;
  status: string;
  progress: number;
  output_path: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CancelRenderResultDto = {
  task_id: string;
  status: string;
  message: string;
};

export type ExportProfileCreateInput = {
  name: string;
  format?: string;
  resolution?: string;
  fps?: number;
  video_bitrate?: string;
  audio_policy?: string;
  subtitle_policy?: string;
  config_json?: string | null;
};

export type ExportProfileDto = {
  id: string;
  name: string;
  format: string;
  resolution: string;
  fps: number;
  video_bitrate: string;
  audio_policy: string;
  subtitle_policy: string;
  config_json: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type RenderTemplateDto = {
  id: string;
  name: string;
};

export type RenderResourceUsageDto = {
  cpuPct: number;
  memoryPct: number;
  gpuPct: number | null;
  diskFreeBytes: number;
};

export type ReviewSuggestion = {
  id: string;
  code: string;
  category: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  actionLabel: string;
  sourceType: string | null;
  sourceId: string | null;
  createdAt: string;
};

export type ReviewSummaryUpdateInput = {
  project_name?: string | null;
  total_views?: number | null;
  total_likes?: number | null;
  total_comments?: number | null;
  avg_watch_time_sec?: number | null;
  completion_rate?: number | null;
};

export type ReviewSummaryDto = {
  id: string;
  project_id: string;
  project_name: string | null;
  total_views: number;
  total_likes: number;
  total_comments: number;
  avg_watch_time_sec: number;
  completion_rate: number;
  suggestions: ReviewSuggestion[];
  last_analyzed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AnalyzeProjectResultDto = {
  project_id: string;
  status: string;
  message: string;
  analyzed_at: string;
};

export type VideoTranscriptDto = {
  id: string;
  videoId: string;
  language: string | null;
  text: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export type VideoSegmentDto = {
  id: string;
  videoId: string;
  segmentIndex: number;
  startMs: number;
  endMs: number;
  label: string | null;
  transcriptText: string | null;
  metadataJson: string | null;
  createdAt: string;
};

export type VideoStructureExtractionDto = {
  id: string;
  videoId: string;
  status: string;
  scriptJson: string | null;
  storyboardJson: string | null;
  createdAt: string;
  updatedAt: string;
};

export type VideoStageDto = {
  stage: string;
  status: string;
  progressPct: number;
};

export type ApplyVideoExtractionResultDto = {
  projectId: string;
  extractionId: string;
  scriptRevision: number;
  status: string;
  message: string;
};

export type { ImportedVideo, ImportedVideoStatus } from "./video";

export type RuntimeSuccessEnvelope<T> = {
  ok: true;
  data: T;
};

export type RuntimeErrorEnvelope = {
  ok: false;
  error: string;
  error_code?: string;
  requestId?: string;
  details?: unknown;
};

export type RuntimeEnvelope<T> = RuntimeSuccessEnvelope<T> | RuntimeErrorEnvelope;

export type RuntimeRequestErrorShape = {
  message: string;
  requestId: string;
  status: number;
  errorCode?: string;
  details?: unknown;
};
