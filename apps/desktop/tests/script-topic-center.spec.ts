import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

describe("Script topic center", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads the current project script and saves a new revision through the script store", async () => {
    const projectContext = {
      projectId: "project-001",
      projectName: "Summer Launch",
      status: "active"
    };
    const scriptDocument = {
      projectId: "project-001",
      currentVersion: {
        revision: 1,
        source: "manual",
        content: "Old hook\nOld body",
        provider: null,
        model: null,
        aiJobId: null,
        createdAt: "2026-04-11T10:20:00Z"
      },
      versions: [
        {
          revision: 1,
          source: "manual",
          content: "Old hook\nOld body",
          provider: null,
          model: null,
          aiJobId: null,
          createdAt: "2026-04-11T10:20:00Z"
        }
      ],
      recentJobs: []
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
      if (path === "/api/dashboard/context") {
        return okJsonResponse(projectContext);
      }
      if (path === "/api/dashboard/summary") {
        return okJsonResponse({
          recentProjects: [
            {
              id: "project-001",
              name: "Summer Launch",
              description: "Creator flow",
              status: "active",
              currentScriptVersion: 1,
              currentStoryboardVersion: 0,
              createdAt: "2026-04-11T10:00:00Z",
              updatedAt: "2026-04-11T10:20:00Z",
              lastAccessedAt: "2026-04-11T10:20:00Z"
            }
          ],
          currentProject: projectContext
        });
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "GET") {
        return okJsonResponse(cloneValue(scriptDocument));
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "PUT") {
        const body = JSON.parse(String(init?.body)) as { content: string };
        scriptDocument.currentVersion = {
          revision: 2,
          source: "manual",
          content: body.content,
          provider: null,
          model: null,
          aiJobId: null,
          createdAt: "2026-04-11T10:25:00Z"
        };
        scriptDocument.versions = [scriptDocument.currentVersion, ...scriptDocument.versions];
        return okJsonResponse(cloneValue(scriptDocument));
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/scripts/topics");
    await flushPromises();

    expect(wrapper.find('[data-script-section="prompt-panel"]').exists()).toBe(true);
    expect(wrapper.find('[data-script-section="editor"]').exists()).toBe(true);
    expect(wrapper.find('[data-script-section="versions"]').exists()).toBe(true);
    expect(wrapper.find('[data-script-section="title-variants"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("策划工作台");
    expect(wrapper.text()).toContain("结构锚点");
    expect((wrapper.get('[data-field="script.content"]').element as HTMLTextAreaElement).value).toBe(
      "Old hook\nOld body"
    );

    await wrapper.get('[data-field="script.content"]').setValue("New hook\nNew body\nCTA");
    await wrapper.get('[data-action="save-script"]').trigger("click");
    await flushPromises();

    const saveCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        String(url).includes("/api/scripts/projects/project-001/document") &&
        options?.method === "PUT"
    );

    expect(saveCall).toBeTruthy();
    expect(JSON.parse(String(saveCall?.[1]?.body))).toEqual({
      content: "New hook\nNew body\nCTA"
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("修订 2");
      expect(wrapper.findAll('[data-script-version-item]')).toHaveLength(2);
      expect(wrapper.text()).toContain("当前主标题");
    });
  });
});

