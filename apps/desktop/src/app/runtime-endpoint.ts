const DEFAULT_RUNTIME_BASE_URL = "http://127.0.0.1:8000";

export function resolveRuntimeBaseUrl(): string {
  return import.meta.env.VITE_RUNTIME_BASE_URL?.trim() || DEFAULT_RUNTIME_BASE_URL;
}

export function buildRuntimeWebSocketUrl(): string {
  const url = new URL(resolveRuntimeBaseUrl());
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/api/ws";
  url.search = "";
  url.hash = "";
  return url.toString();
}
