import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import { createAppRouter } from "@/app/router";
import StoryboardPlanningCenterPage from "@/pages/storyboards/StoryboardPlanningCenterPage.vue";
import { useProjectStore } from "@/stores/project";

import {
  createRouteAwareFetch,
  okJsonResponse
} from "./runtime-helpers";

vi.mock(
  "@/stores/task-bus",
  () => ({
    useTaskBusStore: () => ({
      subscribeToType: () => () => undefined
    })
  }),
  { virtual: true }
);

vi.mock(
  "@/stores/asset-library",
  () => ({
    useAssetLibraryStore: () => ({
      hydrate: async () => undefined
    })
  }),
  { virtual: true }
);

function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

describe("Storyboard planning center", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("generates storyboard scenes for the current project and renders the returned cards", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const projectStore = useProjectStore();
    projectStore.currentProject = {
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
    const router = createAppRouter(pinia, createMemoryHistory());
    await router.push("/storyboards/planning");
    await router.isReady();

    const wrapper = mount(StoryboardPlanningCenterPage, {
      global: {
        plugins: [pinia, router]
      }
    });
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
