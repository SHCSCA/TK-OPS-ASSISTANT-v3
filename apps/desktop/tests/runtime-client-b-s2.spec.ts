import { afterEach, describe, expect, it, vi } from "vitest";

import {
  exportDiagnosticsBundle,
  fetchRuntimeLogs,
  initializeDirectories,
  runtimeSelfCheck
} from "@/app/runtime-client";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("B-S2 Runtime client 契约", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("为 bootstrap 与诊断接口发送稳定的路径、方法和查询参数", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        calls.push({ path, method });
        if (path === "/api/bootstrap/initialize-directories") {
          return okJsonResponse({
            rootDir: "G:/AI/TK-OPS/.runtime-data",
            databasePath: "G:/AI/TK-OPS/.runtime-data/runtime.db",
            status: "ok",
            directories: [],
            checkedAt: "2026-04-17T10:00:00Z"
          });
        }
        if (path === "/api/bootstrap/runtime-selfcheck") {
          return okJsonResponse({
            status: "ok",
            runtimeVersion: "0.3.3",
            checkedAt: "2026-04-17T10:00:00Z",
            items: []
          });
        }
        if (
          path ===
          "/api/settings/logs?kind=audit&since=2026-04-17T09%3A00%3A00Z&level=INFO&limit=50"
        ) {
          return okJsonResponse({
            items: [],
            nextCursor: null
          });
        }
        if (path === "/api/settings/diagnostics/export") {
          return okJsonResponse({
            bundlePath: "G:/AI/TK-OPS/.runtime-data/exports/diagnostics/tk-ops.zip",
            createdAt: "2026-04-17T10:00:00Z",
            entries: []
          });
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    await initializeDirectories();
    await runtimeSelfCheck();
    await fetchRuntimeLogs({
      kind: "audit",
      since: "2026-04-17T09:00:00Z",
      level: "INFO",
      limit: 50
    });
    await exportDiagnosticsBundle();

    expect(calls).toEqual([
      { path: "/api/bootstrap/initialize-directories", method: "POST" },
      { path: "/api/bootstrap/runtime-selfcheck", method: "POST" },
      {
        path: "/api/settings/logs?kind=audit&since=2026-04-17T09%3A00%3A00Z&level=INFO&limit=50",
        method: "GET"
      },
      { path: "/api/settings/diagnostics/export", method: "POST" }
    ]);
  });
});
