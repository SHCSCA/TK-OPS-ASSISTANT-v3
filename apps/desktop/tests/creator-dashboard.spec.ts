import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useProjectStore } from "@/stores/project";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

function errorJsonResponse(status: number, error: string, requestId = "req-dashboard") {
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

function createDeferredResponse() {
  let resolve!: (value: unknown) => void;
  const promise = new Promise((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

describe("Creator dashboard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("在总览摘要未返回时保持加载态", async () => {
    const summaryResponse = createDeferredResponse();

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
      if (path === "/api/dashboard/summary" && method === "GET") {
        return summaryResponse.promise;
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/dashboard");
    await flushPromises();

    expect(wrapper.get('[data-dashboard-state="loading"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("创作总览");
  });

  it("在缺少项目上下文时展示阻断态，并在创建项目后恢复到就绪态", async () => {
    const state = {
      summary: {
        recentProjects: [],
        currentProject: null
      } as {
        recentProjects: Array<Record<string, unknown>>;
        currentProject: Record<string, unknown> | null;
      }
    };

    const fetchMock = createRouteAwareFetch((path, method, init) => {
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
      if (path === "/api/dashboard/context" && method === "GET") {
        return okJsonResponse(state.summary.currentProject);
      }
      if (path === "/api/dashboard/summary" && method === "GET") {
        return okJsonResponse(state.summary);
      }
      if (path === "/api/dashboard/projects" && method === "POST") {
        const body = JSON.parse(String(init?.body)) as { name: string; description: string };
        const project = {
          id: "project-001",
          name: body.name,
          description: body.description,
          status: "active",
          currentScriptVersion: 0,
          currentStoryboardVersion: 0,
          createdAt: "2026-04-11T10:10:00Z",
          updatedAt: "2026-04-11T10:10:00Z",
          lastAccessedAt: "2026-04-11T10:10:00Z"
        };
        state.summary = {
          recentProjects: [project],
          currentProject: {
            projectId: "project-001",
            projectName: body.name,
            status: "active"
          }
        };
        return okJsonResponse(project);
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "GET") {
        return okJsonResponse({
          projectId: "project-001",
          currentVersion: null,
          versions: [],
          recentJobs: []
        });
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    const { wrapper, router, pinia } = await mountApp(
      "/dashboard?redirect=%2Fscripts%2Ftopics&reason=missing-project"
    );
    await flushPromises();
    await flushPromises();

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("缺少项目上下文");
      expect(wrapper.find('[data-dashboard-section="hero"]').exists()).toBe(true);
      expect(wrapper.find('[data-dashboard-section="project-entry"]').exists()).toBe(true);
      expect(wrapper.find('[data-dashboard-section="chain-rail"]').exists()).toBe(true);
      expect(wrapper.find('[data-dashboard-section="exception-queue"]').exists()).toBe(true);
      expect(wrapper.findAll('[data-project-card]')).toHaveLength(0);
    });

    const projectStore = useProjectStore(pinia);
    projectStore.currentProject = {
      projectId: "project-001",
      projectName: "Summer Launch",
      status: "active"
    };
    projectStore.recentProjects = [
      {
        id: "project-001",
        name: "Summer Launch",
        description: "Creator flow",
        status: "active",
        currentScriptVersion: 0,
        currentStoryboardVersion: 0,
        createdAt: "2026-04-11T10:10:00Z",
        updatedAt: "2026-04-11T10:10:00Z",
        lastAccessedAt: "2026-04-11T10:10:00Z"
      }
    ];
    projectStore.status = "ready";
    await router.push("/scripts/topics");
    await flushPromises();
    await flushPromises();

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("脚本与选题中心");
      expect(wrapper.text()).toContain("Summer Launch");
      expect(router.currentRoute.value.fullPath).toBe("/scripts/topics");
    });
  });

  it("在总览摘要请求失败时展示错误态", async () => {
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
      if (path === "/api/dashboard/summary" && method === "GET") {
        return errorJsonResponse(500, "总览摘要读取失败。", "req-dashboard-500");
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/dashboard");
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-dashboard-state="error"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("总览摘要读取失败。");
    expect(wrapper.text()).toContain("req-dashboard-500");
  });
});
