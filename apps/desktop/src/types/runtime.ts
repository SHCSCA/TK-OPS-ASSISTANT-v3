export type RuntimeHealthSnapshot = {
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
};

export type CreateProjectInput = {
  name: string;
  description: string;
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
};

export type AICapabilitySettings = {
  capabilities: AICapabilityConfig[];
  providers: AIProviderSecretStatus[];
};

export type AIProviderSecretInput = {
  apiKey: string;
  baseUrl?: string;
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

export type AssetReferenceDto = {
  id: string;
  assetId: string;
  referenceType: string;
  referenceId: string;
  createdAt: string;
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

export type { ImportedVideo, ImportedVideoStatus } from "./video";

export type RuntimeSuccessEnvelope<T> = {
  ok: true;
  data: T;
};

export type RuntimeErrorEnvelope = {
  ok: false;
  error: string;
  requestId?: string;
  details?: unknown;
};

export type RuntimeEnvelope<T> = RuntimeSuccessEnvelope<T> | RuntimeErrorEnvelope;

export type RuntimeRequestErrorShape = {
  message: string;
  requestId: string;
  status: number;
  details?: unknown;
};
