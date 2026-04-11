import type { RuntimeEnvelope, RuntimeHealthSnapshot } from "@/types/runtime";

const DEFAULT_RUNTIME_BASE_URL = "http://127.0.0.1:8000";

function resolveRuntimeBaseUrl(): string {
  return import.meta.env.VITE_RUNTIME_BASE_URL?.trim() || DEFAULT_RUNTIME_BASE_URL;
}

export async function fetchRuntimeHealth(): Promise<RuntimeHealthSnapshot> {
  const response = await fetch(`${resolveRuntimeBaseUrl()}/api/settings/health`, {
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`Runtime 请求失败（HTTP ${response.status}）。`);
  }

  const payload = (await response.json()) as RuntimeEnvelope;
  if (!payload.ok) {
    throw new Error(payload.error);
  }

  return payload.data;
}
