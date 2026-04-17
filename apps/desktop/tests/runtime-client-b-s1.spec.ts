import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RuntimeRequestError,
  fetchRuntimeHealth,
  searchGlobal,
  updateCurrentProjectContext
} from "@/app/runtime-client";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("B-S1 foundation Runtime client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("读取扩展 health、支持清空项目上下文，并调用全局搜索", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });

        if (path === "/api/settings/health") {
          return okJsonResponse({
            runtime: {
              status: "online",
              port: 8000,
              uptimeMs: 1200,
              version: "0.3.3"
            },
            aiProvider: {
              status: "configured",
              latencyMs: null,
              providerId: "openai",
              providerName: "OpenAI",
              lastChecked: null
            },
            renderQueue: {
              running: 0,
              queued: 0,
              avgWaitMs: null
            },
            publishingQueue: {
              pendingToday: 0,
              failedToday: 0
            },
            taskBus: {
              running: 1,
              queued: 2,
              blocked: 0,
              failed24h: 0
            },
            license: {
              status: "missing",
              expiresAt: null
            },
            lastSyncAt: "2026-04-17T12:00:00Z",
            service: "online",
            version: "0.3.3",
            now: "2026-04-17T12:00:00Z",
            mode: "development"
          });
        }

        if (path === "/api/dashboard/context" && method === "PUT") {
          return okJsonResponse(null);
        }

        if (path === "/api/search?q=Alpha&types=projects%2Cassets&limit=8") {
          return okJsonResponse({
            projects: [
              {
                id: "project-1",
                name: "Alpha 项目",
                subtitle: "Alpha 描述",
                updatedAt: "2026-04-17T12:00:00Z"
              }
            ],
            scripts: [],
            tasks: [],
            assets: [
              {
                id: "asset-1",
                name: "Alpha 资产",
                type: "image",
                thumbnailUrl: null,
                updatedAt: "2026-04-17T12:00:00Z"
              }
            ],
            accounts: [],
            workspaces: []
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const health = await fetchRuntimeHealth();
    const cleared = await updateCurrentProjectContext(null);
    const result = await searchGlobal("Alpha", ["projects", "assets"], 8);

    expect(health.runtime.port).toBe(8000);
    expect(health.taskBus.queued).toBe(2);
    expect(cleared).toBeNull();
    expect(result.projects[0]?.name).toBe("Alpha 项目");
    expect(result.assets[0]?.type).toBe("image");
    expect(calls).toEqual([
      { path: "/api/settings/health", method: "GET", body: undefined },
      {
        path: "/api/dashboard/context",
        method: "PUT",
        body: { projectId: null }
      },
      {
        path: "/api/search?q=Alpha&types=projects%2Cassets&limit=8",
        method: "GET",
        body: undefined
      }
    ]);
  });

  it("保留 error_code 到 RuntimeRequestError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 409,
        json: async () => ({
          ok: false,
          error: "任务不可取消",
          error_code: "task.conflict",
          requestId: "req-b-s1"
        })
      }))
    );

    await expect(searchGlobal("blocked")).rejects.toMatchObject({
      name: "RuntimeRequestError",
      message: "任务不可取消",
      errorCode: "task.conflict",
      requestId: "req-b-s1",
      status: 409
    } satisfies Partial<RuntimeRequestError>);
  });
});
