import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createRouteAwareFetch, mountApp, okJsonResponse, runtimeFixtures } from "./runtime-helpers";

function errorJsonResponse(status: number, error: string, requestId = "req-review") {
  return {
    ok: false,
    status,
    json: async () => ({
      ok: false,
      error,
      requestId
    })
  };
}

function reviewSummaryWithSuggestions() {
  return {
    id: "review-1",
    project_id: "project-1",
    project_name: "Demo Project",
    total_views: 1280,
    total_likes: 96,
    total_comments: 18,
    avg_watch_time_sec: 23.5,
    completion_rate: 0.68,
    suggestions: [
      {
        code: "hook-short",
        category: "script",
        title: "开场钩子再压缩",
        description: "建议把前 5 秒的开场说明再收紧。",
        priority: "high"
      },
      {
        code: "cta-move",
        category: "publish",
        title: "行动号召前移",
        description: "把结尾 CTA 提前到中段。",
        priority: "medium"
      }
    ],
    last_analyzed_at: "2026-04-15T10:00:00Z",
    created_at: "2026-04-15T10:00:00Z",
    updated_at: "2026-04-15T10:00:00Z"
  };
}

describe("ReviewOptimizationCenterPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("在没有当前项目时展示阻断态", async () => {
    const fetchMock = createRouteAwareFetch((path) => {
      if (path === "/api/license/status") {
        return okJsonResponse(runtimeFixtures.activeLicense);
      }
      if (path === "/api/settings/health") {
        return okJsonResponse(runtimeFixtures.health);
      }
      if (path === "/api/settings/config") {
        return okJsonResponse(runtimeFixtures.initializedConfig);
      }
      if (path === "/api/settings/diagnostics") {
        return okJsonResponse(runtimeFixtures.initializedDiagnostics);
      }
      if (path === "/api/dashboard/summary") {
        return okJsonResponse(runtimeFixtures.emptyDashboardSummary);
      }

      throw new Error(`Unhandled request: ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/review/optimization");
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-review-state="blocked"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("缺少项目上下文");
    expect(wrapper.text()).toContain("返回总览");
  });

  it("在复盘摘要为空时展示空态并保留分析入口", async () => {
    const fetchMock = createRouteAwareFetch((path, method) => {
      if (path === "/api/license/status") {
        return okJsonResponse(runtimeFixtures.activeLicense);
      }
      if (path === "/api/settings/health") {
        return okJsonResponse(runtimeFixtures.health);
      }
      if (path === "/api/settings/config") {
        return okJsonResponse(runtimeFixtures.initializedConfig);
      }
      if (path === "/api/settings/diagnostics") {
        return okJsonResponse(runtimeFixtures.initializedDiagnostics);
      }
      if (path === "/api/dashboard/summary") {
        return okJsonResponse({
          recentProjects: [],
          currentProject: {
            projectId: "project-1",
            projectName: "Demo Project",
            status: "active"
          }
        });
      }
      if (path === "/api/review/projects/project-1/summary" && method === "GET") {
        return okJsonResponse({
          id: "review-1",
          project_id: "project-1",
          project_name: "Demo Project",
          total_views: 0,
          total_likes: 0,
          total_comments: 0,
          avg_watch_time_sec: 0,
          completion_rate: 0,
          suggestions: [],
          last_analyzed_at: null,
          created_at: "2026-04-15T10:00:00Z",
          updated_at: "2026-04-15T10:00:00Z"
        });
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/review/optimization");
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-review-state="empty"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("暂时没有复盘结论");
    expect(wrapper.get('[data-action="analyze-review"]').exists()).toBe(true);
  });

  it("在复盘摘要包含指标与建议时展示就绪态", async () => {
    const fetchMock = createRouteAwareFetch((path, method) => {
      if (path === "/api/license/status") {
        return okJsonResponse(runtimeFixtures.activeLicense);
      }
      if (path === "/api/settings/health") {
        return okJsonResponse(runtimeFixtures.health);
      }
      if (path === "/api/settings/config") {
        return okJsonResponse(runtimeFixtures.initializedConfig);
      }
      if (path === "/api/settings/diagnostics") {
        return okJsonResponse(runtimeFixtures.initializedDiagnostics);
      }
      if (path === "/api/dashboard/summary") {
        return okJsonResponse({
          recentProjects: [],
          currentProject: {
            projectId: "project-1",
            projectName: "Demo Project",
            status: "active"
          }
        });
      }
      if (path === "/api/review/projects/project-1/summary" && method === "GET") {
        return okJsonResponse(reviewSummaryWithSuggestions());
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/review/optimization");
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-review-state="ready"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("Demo Project");
    expect(wrapper.findAll('[data-review-suggestion]')).toHaveLength(2);
    expect(wrapper.text()).toContain("1,280");
    expect(wrapper.text()).toContain("68.0%");
  });

  it("在复盘摘要读取失败时展示错误态", async () => {
    const fetchMock = createRouteAwareFetch((path, method) => {
      if (path === "/api/license/status") {
        return okJsonResponse(runtimeFixtures.activeLicense);
      }
      if (path === "/api/settings/health") {
        return okJsonResponse(runtimeFixtures.health);
      }
      if (path === "/api/settings/config") {
        return okJsonResponse(runtimeFixtures.initializedConfig);
      }
      if (path === "/api/settings/diagnostics") {
        return okJsonResponse(runtimeFixtures.initializedDiagnostics);
      }
      if (path === "/api/dashboard/summary") {
        return okJsonResponse({
          recentProjects: [],
          currentProject: {
            projectId: "project-1",
            projectName: "Demo Project",
            status: "active"
          }
        });
      }
      if (path === "/api/review/projects/project-1/summary" && method === "GET") {
        return errorJsonResponse(500, "复盘摘要读取失败。", "req-review-500");
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/review/optimization");
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-review-state="error"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("复盘摘要读取失败。");
  });
});
