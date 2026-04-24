import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

import SubtitleAlignmentCenterPage from "@/pages/subtitles/SubtitleAlignmentCenterPage.vue";
import { useProjectStore } from "@/stores/project";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("M08 字幕对齐中心页面", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(window, "alert").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("加载脚本和字幕版本后显示阻断草稿语义", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const wrapper = mountSubtitlePageWithProject();
    await flushPromises();

    expect(wrapper.text()).toContain("M08 字幕对齐中心");
    expect(wrapper.text()).toContain("已保存阻断草稿，但没有生成真实时间码。");
    expect(wrapper.text()).toContain("版本：阻断草稿");
    expect(wrapper.text()).toContain("阻断草稿");
    expect(wrapper.text()).toContain("第一段脚本！");
    expect(wrapper.text()).not.toMatch(/假时间码|成功结果/);
  });

  it("生成后继续保留 blocked 草稿语义，并且不弹出 alert", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const wrapper = mountSubtitlePageWithProject();
    await flushPromises();

    await wrapper.get('[data-testid="subtitle-generate-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("没有可用字幕对齐 Provider");
    expect(wrapper.text()).toContain("重新保存阻断草稿");
    expect(wrapper.text()).toContain("真实时间码");
    expect(window.alert).not.toHaveBeenCalled();
  });

  it("没有当前项目时禁用生成入口并保留阻断导语", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const wrapper = mount(SubtitleAlignmentCenterPage, {
      global: {
        plugins: [createPinia()]
      }
    });
    await flushPromises();

    expect(wrapper.text()).toContain("生成入口已锁定");
    expect(wrapper.text()).toContain("请先选择项目");
    expect(wrapper.get('[data-testid="subtitle-generate-button"]').attributes("disabled")).toBeDefined();
  });
});

function mountSubtitlePageWithProject() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const projectStore = useProjectStore();
  projectStore.currentProject = {
    projectId: "project-1",
    projectName: "短视频字幕项目",
    status: "active"
  };

  return mount(SubtitleAlignmentCenterPage, {
    global: {
      plugins: [pinia]
    }
  });
}

function createSubtitleFetch() {
  return createRouteAwareFetch((path, method, init) => {
    if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
      return okJsonResponse(scriptDocument());
    }
    if (path === "/api/subtitles/projects/project-1/tracks") {
      return okJsonResponse([subtitleTrack()]);
    }
    if (path === "/api/subtitles/projects/project-1/tracks/generate") {
      return okJsonResponse({
        track: subtitleTrack("subtitle-2"),
        task: null,
        message: "尚未配置可用字幕对齐 Provider，已保存字幕草稿。"
      });
    }
    if (path === "/api/subtitles/tracks/subtitle-1" && method === "PATCH") {
      const body = JSON.parse(String(init?.body));
      return okJsonResponse(subtitleTrack("subtitle-1", body.segments[0].text, body.style.fontSize));
    }
    throw new Error(`Unhandled request: ${method} ${path}`);
  });
}

function scriptDocument() {
  return {
    projectId: "project-1",
    currentVersion: {
      revision: 1,
      source: "manual",
      content: "第一段脚本！\n第二段脚本！",
      provider: null,
      model: null,
      aiJobId: null,
      createdAt: now()
    },
    versions: [],
    recentJobs: []
  };
}

function now() {
  return "2026-04-16T10:00:00Z";
}

function subtitleTrack(id = "subtitle-1", text = "第一段脚本！", fontSize = 32) {
  return {
    id,
    projectId: "project-1",
    timelineId: null,
    source: "script",
    language: "zh-CN",
    style: {
      preset: "creator-default",
      fontSize,
      position: "bottom",
      textColor: "#FFFFFF",
      background: "rgba(0,0,0,0.62)"
    },
    segments: [
      {
        segmentIndex: 0,
        text,
        startMs: null,
        endMs: null,
        confidence: null,
        locked: false
      }
    ],
    status: "blocked",
    createdAt: now()
  };
}
