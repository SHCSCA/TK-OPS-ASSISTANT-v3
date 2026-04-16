import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

  it("加载项目脚本和字幕版本后展示字幕校对台", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const wrapper = mountSubtitlePageWithProject();
    await flushPromises();

    expect(wrapper.text()).toContain("M08 字幕对齐中心");
    expect(wrapper.text()).toContain("字幕校对台");
    expect(wrapper.text()).toContain("第一段脚本");
    expect(wrapper.text()).toContain("生成字幕草稿");
    expect(wrapper.text()).not.toMatch(/鐠у嫶楠噟閻㈢喐鍨殀妫板嫯/);
  });

  it("生成后展示 Provider 阻断状态且不弹出 alert", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const wrapper = mountSubtitlePageWithProject();
    await flushPromises();

    await wrapper.get('[data-testid="subtitle-generate-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("尚未配置可用字幕对齐 Provider");
    expect(wrapper.text()).toContain("待配置 Provider");
    expect(window.alert).not.toHaveBeenCalled();
  });

  it("没有当前项目时展示中文引导态并禁用生成入口", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const wrapper = mount(SubtitleAlignmentCenterPage, {
      global: {
        plugins: [createPinia()]
      }
    });
    await flushPromises();

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
  return createRouteAwareFetch((path, method) => {
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
    throw new Error(`Unhandled request: ${method} ${path}`);
  });
}

function scriptDocument() {
  return {
    projectId: "project-1",
    currentVersion: {
      revision: 1,
      source: "manual",
      content: "第一段脚本\n\n第二段脚本",
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

function subtitleTrack(id = "subtitle-1") {
  return {
    id,
    projectId: "project-1",
    timelineId: null,
    source: "script",
    language: "zh-CN",
    style: {
      preset: "creator-default",
      fontSize: 32,
      position: "bottom",
      textColor: "#FFFFFF",
      background: "rgba(0,0,0,0.62)"
    },
    segments: [
      {
        segmentIndex: 0,
        text: "第一段脚本",
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
