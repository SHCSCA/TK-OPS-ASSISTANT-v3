import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import { createAppRouter } from "@/app/router";
import StoryboardPlanningCenterPage from "@/pages/storyboards/StoryboardPlanningCenterPage.vue";
import { useProjectStore } from "@/stores/project";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

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

function prepareProject() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const projectStore = useProjectStore();
  projectStore.currentProject = {
    projectId: "project-001",
    projectName: "Spring Iced Coffee",
    status: "active"
  };
  return pinia;
}

describe("Storyboard planning center", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("generates storyboard scenes and renders the markdown preview from runtime data", async () => {
    const pinia = prepareProject();
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
            content: "# Spring Iced Coffee\n\n| 时间 | 画面 |\n| --- | --- |\n| 0-2s | 冰霸杯特写 |",
            provider: null,
            model: null,
            aiJobId: null,
            createdAt: "2026-04-11T10:32:00Z"
          },
          versions: [],
          recentJobs: [
            {
              id: "job-blocked",
              capabilityId: "storyboard_generation",
              provider: "deepseek",
              model: "deepseek-v4-flash",
              status: "blocked",
              error: "分镜 Provider 未返回镜头列表。",
              durationMs: 12,
              createdAt: "2026-04-25T09:46:00Z",
              completedAt: "2026-04-25T09:46:01Z"
            }
          ]
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
              title: "镜头1 0-3秒",
              shotLabel: "镜头1",
              time: "0-3秒",
              shotSize: "近景/特写",
              visualContent: "手持冰霸杯特写，阳光下展示杯身和冰块反光",
              action: "手握杯子缓慢转动",
              cameraAngle: "微距俯拍",
              cameraMovement: "轻微推进",
              voiceover: "This is my spring addiction.",
              subtitle: "This is my spring addiction.",
              audio: "轻快钢琴曲和冰块声",
              transition: "快切",
              shootingNote: "保持自然窗光，突出透明质感",
              summary: "手持冰霸杯特写，阳光下展示杯身和冰块反光",
              visualPrompt: "9:16 竖屏，真实自然窗光，透明冰霸杯微距特写"
            },
            {
              sceneId: "scene-2",
              title: "镜头2 3-6秒",
              shotLabel: "镜头2",
              time: "3-6秒",
              shotSize: "特写",
              visualContent: "冰块倒入杯中，慢动作展示落杯瞬间",
              action: "手倒冰块",
              cameraAngle: "固定近景",
              cameraMovement: "慢动作",
              voiceover: "Ice that stays cold for hours.",
              subtitle: "Ice that stays cold for hours.",
              audio: "冰块哗啦声",
              transition: "节拍快切",
              shootingNote: "使用大颗粒真冰块",
              summary: "冰块倒入杯中，慢动作展示落杯瞬间",
              visualPrompt: "9:16 竖屏，冰块落入透明杯，慢动作，真实 TikTok 风格"
            }
          ],
          provider: "deepseek",
          model: "deepseek-chat",
          aiJobId: "job-001",
          createdAt: "2026-04-11T10:35:00Z"
        };
        storyboardDocument.versions = [storyboardDocument.currentVersion];
        storyboardDocument.recentJobs = [
          {
            id: "job-001",
            capabilityId: "storyboard_generation",
            provider: "deepseek",
            model: "deepseek-chat",
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

    expect(wrapper.find('[data-storyboard-section="script-reference"]').exists()).toBe(true);
    expect(wrapper.find('[data-storyboard-section="scene-board"]').exists()).toBe(true);
    expect(wrapper.find('[data-storyboard-section="version-summary"]').exists()).toBe(false);

    await wrapper.get('[data-action="generate-storyboard"]').trigger("click");
    await flushPromises();

    await vi.waitFor(() => {
      expect(wrapper.findAll("[data-scene-card]")).toHaveLength(0);
      expect(wrapper.find("[data-storyboard-preview-mode]").exists()).toBe(true);
      expect(wrapper.find("[data-storyboard-preview-mode] table").exists()).toBe(true);
      expect(wrapper.text()).toContain("镜头1");
      expect(wrapper.text()).toContain("手持冰霸杯特写");
      expect(wrapper.text()).toContain("deepseek-chat");
    });
  });

  it("shows the adopted script as markdown preview without structure anchors", async () => {
    const pinia = prepareProject();
    const fetchMock = createRouteAwareFetch((path, method) => {
      if (path === "/api/storyboards/projects/project-001/document" && method === "GET") {
        return okJsonResponse({
          projectId: "project-001",
          basedOnScriptRevision: 2,
          currentVersion: null,
          versions: [],
          recentJobs: []
        });
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "GET") {
        return okJsonResponse({
          projectId: "project-001",
          currentVersion: {
            revision: 2,
            source: "ai_rewrite",
            content: [
              "# 春日咖啡冷饮短视频脚本",
              "",
              "| 时间 | 画面描述 | 镜头/机位 | 字幕/台词 |",
              "| --- | --- | --- | --- |",
              "| 0-1s | 冰块落入玻璃杯 | 俯拍微距 | 一秒入春 |"
            ].join("\n"),
            provider: "deepseek",
            model: "deepseek-chat",
            aiJobId: "job-001",
            createdAt: "2026-04-25T09:45:00Z"
          },
          versions: [],
          recentJobs: []
        });
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

    await vi.waitFor(() => {
      expect(wrapper.find('[data-script-reference-mode="outline"]').exists()).toBe(false);
      expect(wrapper.get("[data-storyboard-script-preview]").text()).toContain("春日咖啡冷饮短视频脚本");
      expect(wrapper.find("[data-storyboard-script-preview] table").exists()).toBe(true);
      expect(wrapper.get("[data-storyboard-script-preview]").text()).toContain("冰块落入玻璃杯");
    });
  });

  it("switches list, outline and preview modes from the same storyboard version", async () => {
    const pinia = prepareProject();
    let savedPayload: Record<string, unknown> | null = null;
    const fetchMock = createRouteAwareFetch((path, method, init) => {
      if (path === "/api/storyboards/projects/project-001/document" && method === "GET") {
        return okJsonResponse({
          projectId: "project-001",
          basedOnScriptRevision: 3,
          currentVersion: {
            revision: 1,
            basedOnScriptRevision: 3,
            source: "ai_generate",
            scenes: [
              {
                sceneId: "scene-1",
                title: "镜头1 0-3秒",
                shotLabel: "镜头1",
                time: "0-3秒",
                shotSize: "近景/特写",
                visualContent: "手持冰霸杯特写",
                action: "缓慢转动杯身",
                cameraAngle: "微距俯拍",
                cameraMovement: "轻微推进",
                voiceover: "This is my spring addiction.",
                subtitle: "This is my spring addiction.",
                audio: "冰块声",
                transition: "快切",
                shootingNote: "突出透明质感",
                summary: "手持冰霸杯特写",
                visualPrompt: "9:16 竖屏，真实自然窗光，透明冰霸杯微距特写"
              }
            ],
            markdown: [
              "# TikTok 分镜执行方案",
              "",
              "## 1. 视频基础信息",
              "",
              "| 项目 | 内容 |",
              "|---|---|",
              "| 视频主题 | Spring Iced Coffee |",
              "",
              "## 3. 详细分镜表",
              "",
              "| 镜头 | 时间 | 景别 | 画面内容 | 人物动作 | 镜头角度 | 运镜方式 | 口播文案 | 屏幕字幕 | 音效/BGM | 转场方式 | 拍摄注意 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|",
              "| 镜头1 | 0-3秒 | 近景/特写 | 手持冰霸杯特写 | 缓慢转动杯身 | 微距俯拍 | 轻微推进 | This is my spring addiction. | This is my spring addiction. | 冰块声 | 快切 | 突出透明质感 |"
            ].join("\n"),
            provider: "deepseek",
            model: "deepseek-chat",
            aiJobId: "job-001",
            createdAt: "2026-04-25T09:45:00Z"
          },
          versions: [],
          recentJobs: []
        });
      }
      if (path === "/api/storyboards/projects/project-001/document" && method === "PUT") {
        savedPayload = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
        return okJsonResponse({
          projectId: "project-001",
          basedOnScriptRevision: 3,
          currentVersion: {
            revision: 2,
            basedOnScriptRevision: 3,
            source: "manual",
            scenes: [
              {
                sceneId: "scene-2",
                title: "手动分镜",
                summary: String(savedPayload.markdown),
                visualPrompt: String(savedPayload.markdown)
              }
            ],
            markdown: savedPayload.markdown,
            provider: null,
            model: null,
            aiJobId: null,
            createdAt: "2026-04-25T09:50:00Z"
          },
          versions: [],
          recentJobs: []
        });
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "GET") {
        return okJsonResponse({
          projectId: "project-001",
          currentVersion: {
            revision: 3,
            source: "ai_generate",
            content: "# Spring Iced Coffee",
            provider: "deepseek",
            model: "deepseek-chat",
            aiJobId: "job-001",
            createdAt: "2026-04-25T09:45:00Z"
          },
          versions: [],
          recentJobs: []
        });
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

    expect(wrapper.find("[data-storyboard-preview-mode]").exists()).toBe(true);
    expect(wrapper.find("[data-storyboard-preview-mode] table").exists()).toBe(true);
    expect(wrapper.text()).toContain("TikTok 分镜执行方案");
    expect(wrapper.text()).toContain("视频基础信息");
    expect(wrapper.text()).toContain("Spring Iced Coffee");

    await wrapper.get('[data-storyboard-view="outline"]').trigger("click");
    expect(wrapper.find("[data-storyboard-preview-mode]").exists()).toBe(true);
    expect(wrapper.text()).toContain("TikTok 分镜执行方案");
    await wrapper.get('[data-storyboard-view="preview"]').trigger("click");
    expect(wrapper.find("[data-storyboard-preview-mode]").exists()).toBe(true);

    await wrapper.get('[data-action="save-storyboard"]').trigger("click");
    await flushPromises();

    expect(savedPayload?.markdown).toContain("TikTok 分镜执行方案");
    expect(savedPayload?.scenes).toEqual(expect.any(Array));
  });

  it("falls back to loose markdown when legacy scenes came from document headings", async () => {
    const pinia = prepareProject();
    const fetchMock = createRouteAwareFetch((path, method) => {
      if (path === "/api/storyboards/projects/project-001/document" && method === "GET") {
        return okJsonResponse({
          projectId: "project-001",
          basedOnScriptRevision: 4,
          currentVersion: {
            revision: 1,
            basedOnScriptRevision: 4,
            source: "ai_generate",
            scenes: [
              {
                sceneId: "scene-1",
                title: "# TikTok短视频脚本",
                summary: "| 项目 | 内容 |\n|---|---|\n| 平台 | TikTok |",
                visualPrompt: "| 项目 | 内容 |\n|---|---|\n| 平台 | TikTok |"
              },
              ...Array.from({ length: 41 }, (_, index) => ({
                sceneId: `scene-${index + 2}`,
                title: `## 章节 ${index + 2}`,
                summary: "旧版本解析出的伪分镜",
                visualPrompt: "旧版本解析出的伪分镜"
              }))
            ],
            markdown: null,
            provider: "deepseek",
            model: "deepseek-v4-flash",
            aiJobId: "job-legacy",
            createdAt: "2026-04-25T09:45:00Z"
          },
          versions: [],
          recentJobs: []
        });
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "GET") {
        return okJsonResponse({
          projectId: "project-001",
          currentVersion: {
            revision: 4,
            source: "ai_generate",
            content: "# Spring Iced Coffee",
            provider: "deepseek",
            model: "deepseek-chat",
            aiJobId: "job-001",
            createdAt: "2026-04-25T09:45:00Z"
          },
          versions: [],
          recentJobs: []
        });
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

    expect(wrapper.text()).toContain("当前版本缺少 AI 原始 Markdown");
    expect(wrapper.text()).not.toContain("| 镜头 | 时间 | 景别 | 画面内容 |");
    await wrapper.get('[data-storyboard-view="preview"]').trigger("click");
    expect(wrapper.find("[data-storyboard-preview-mode]").exists()).toBe(true);
    expect(wrapper.text()).not.toContain("分镜 Provider 未返回镜头列表。");
  });
});
