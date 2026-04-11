import type {
  AppSettings,
  AppSettingsUpdateInput,
  LicenseActivationInput,
  LicenseStatus,
  RuntimeDiagnostics,
  RuntimeEnvelope,
  RuntimeRequestErrorShape,
  RuntimeHealthSnapshot
} from "@/types/runtime";

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

export async function fetchLicenseStatus(): Promise<LicenseStatus> {
  return requestRuntime<LicenseStatus>("/api/license/status");
}

export async function activateLicense(input: LicenseActivationInput): Promise<LicenseStatus> {
  return requestRuntime<LicenseStatus>("/api/license/activate", {
    body: JSON.stringify(input),
    method: "POST"
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
