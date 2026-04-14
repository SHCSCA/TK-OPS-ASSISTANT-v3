import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("Creator dashboard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a project, updates current context, and resumes the requested route", async () => {
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
      if (path === "/api/dashboard/summary") {
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

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper, router } = await mountApp(
      "/dashboard?redirect=%2Fscripts%2Ftopics&reason=missing-project"
    );
    await flushPromises();
    await flushPromises();

    expect(wrapper.text()).toContain("把脚本、分镜、剪辑与发布收束到同一个项目");
    expect(wrapper.text()).not.toContain("鏈");
    expect(wrapper.text()).not.toContain("鍒");
    expect(wrapper.find('[data-dashboard-section="project-entry"]').exists()).toBe(true);
    expect(wrapper.find('[data-dashboard-section="recent-projects"]').exists()).toBe(true);
    expect(wrapper.find('[data-dashboard-section="chain-rail"]').exists()).toBe(true);
    expect(wrapper.find('[data-dashboard-section="system-status"]').exists()).toBe(true);

    await wrapper.get('[data-field="project.name"]').setValue("Summer Launch");
    await wrapper.get('[data-field="project.description"]').setValue("Creator flow");
    await wrapper.get('[data-action="create-project"]').trigger("click");
    await flushPromises();
    await flushPromises();

    const createCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        String(url).includes("/api/dashboard/projects") && options?.method === "POST"
    );

    expect(createCall).toBeTruthy();
    expect(JSON.parse(String(createCall?.[1]?.body))).toEqual({
      name: "Summer Launch",
      description: "Creator flow"
    });
    await vi.waitFor(() => {
      expect(router.currentRoute.value.fullPath).toBe("/scripts/topics");
    });
  });
});
