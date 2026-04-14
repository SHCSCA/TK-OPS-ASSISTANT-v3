import type {
  AICapabilitySettings,
  AIProviderHealth,
  AIProviderSecretInput,
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
  StoryboardScene
} from "@/types/runtime";
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
) {
  return requestRuntime(`/api/settings/ai-capabilities/providers/${providerId}/secret`, {
    body: JSON.stringify(input),
    method: "PUT"
  });
}

export async function checkAIProviderHealth(providerId: string): Promise<AIProviderHealth> {
  return requestRuntime<AIProviderHealth>(
    `/api/settings/ai-capabilities/providers/${providerId}/health-check`,
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
