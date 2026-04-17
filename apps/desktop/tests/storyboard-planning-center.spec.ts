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

describe("Storyboard planning center", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("generates storyboard scenes for the current project and renders the returned cards", async () => {
    const projectContext = {
      projectId: "project-001",
      projectName: "Summer Launch",
      status: "active"
    };
    const storyboardDocument = {
      projectId: "project-001",
      basedOnScriptRevision: 1,
      currentVersion: null,
      versions: [],
      recentJobs: []
    };

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
              updatedAt: "2026-04-11T10:30:00Z",
              lastAccessedAt: "2026-04-11T10:30:00Z"
            }
          ],
          currentProject: projectContext
        });
      }
      if (path === "/api/storyboards/projects/project-001/document" && method === "GET") {
        return okJsonResponse(cloneValue(storyboardDocument));
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "GET") {
        return okJsonResponse({
          projectId: "project-001",
          currentVersion: {
            revision: 1,
            source: "manual",
            content: "Hook 场景\nProblem 场景",
            provider: null,
            model: null,
            aiJobId: null,
            createdAt: "2026-04-11T10:32:00Z"
          },
          versions: [],
          recentJobs: []
        });
      }
      if (path === "/api/storyboards/projects/project-001/generate" && method === "POST") {
        storyboardDocument.currentVersion = {
          revision: 1,
          basedOnScriptRevision: 1,
          source: "ai_generate",
          scenes: [
            {
              sceneId: "scene-1",
              title: "Hook",
              summary: "Fast intro",
              visualPrompt: "Close-up motion"
            },
            {
              sceneId: "scene-2",
              title: "Problem",
              summary: "Show the pain point",
              visualPrompt: "Messy desk scene"
            }
          ],
          provider: "openai",
          model: "gpt-5-mini",
          aiJobId: "job-001",
          createdAt: "2026-04-11T10:35:00Z"
        };
        storyboardDocument.versions = [storyboardDocument.currentVersion];
        storyboardDocument.recentJobs = [
          {
            id: "job-001",
            capabilityId: "storyboard_generation",
            provider: "openai",
            model: "gpt-5-mini",
            status: "succeeded",
            error: null,
            durationMs: 18,
            createdAt: "2026-04-11T10:35:00Z",
            completedAt: "2026-04-11T10:35:01Z"
          }
        ];
        return okJsonResponse(cloneValue(storyboardDocument));
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/storyboards/planning");
    await flushPromises();

    expect(wrapper.find('[data-storyboard-section="script-nav"]').exists()).toBe(true);
    expect(wrapper.find('[data-storyboard-section="scene-board"]').exists()).toBe(true);
    expect(wrapper.find('[data-storyboard-section="version-summary"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("分镜工作面");
    expect(wrapper.text()).toContain("脚本段落导航");

    await wrapper.get('[data-action="generate-storyboard"]').trigger("click");
    await flushPromises();

    await vi.waitFor(() => {
      expect(wrapper.findAll('[data-scene-card]')).toHaveLength(2);
      expect((wrapper.findAll('[data-scene-card] input')[0].element as HTMLInputElement).value).toBe(
        "Hook"
      );
      expect((wrapper.findAll('[data-scene-card] input')[1].element as HTMLInputElement).value).toBe(
        "Problem"
      );
      expect(wrapper.text()).toContain("版本与生成状态");
      expect(wrapper.text()).toContain("gpt-5-mini");
    });
  });
});
