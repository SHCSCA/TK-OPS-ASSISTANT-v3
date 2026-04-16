import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import VoiceStudioPage from "@/pages/voice/VoiceStudioPage.vue";
import { useProjectStore } from "@/stores/project";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("M07 配音中心页面", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(window, "alert").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("加载项目脚本、音色和版本后展示声音导演台", async () => {
    vi.stubGlobal("fetch", createVoiceFetch());

    const wrapper = mountVoiceStudioWithProject();
    await flushPromises();

    expect(wrapper.text()).toContain("M07 配音中心");
    expect(wrapper.text()).toContain("声音导演台");
    expect(wrapper.text()).toContain("第一段脚本");
    expect(wrapper.text()).toContain("清晰叙述");
    expect(wrapper.text()).toContain("生成配音版本");
    expect(wrapper.text()).not.toMatch(/璧勴骇|鐢熸垚|棰勮/);
  });

  it("生成后展示 Provider 阻断状态，不弹出 alert", async () => {
    vi.stubGlobal("fetch", createVoiceFetch());

    const wrapper = mountVoiceStudioWithProject();
    await flushPromises();

    await wrapper.get('[data-testid="voice-generate-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("尚未配置可用 TTS Provider");
    expect(wrapper.text()).toContain("待配置 AI Provider");
    expect(window.alert).not.toHaveBeenCalled();
  });

  it("没有当前项目时展示中文引导态并禁用生成入口", async () => {
    vi.stubGlobal("fetch", createVoiceFetch());

    const wrapper = mount(VoiceStudioPage, {
      global: {
        plugins: [createPinia()]
      }
    });
    await flushPromises();

    expect(wrapper.text()).toContain("请先选择项目");
    expect(wrapper.get('[data-testid="voice-generate-button"]').attributes("disabled")).toBeDefined();
  });
});

function mountVoiceStudioWithProject() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const projectStore = useProjectStore();
  projectStore.currentProject = {
    projectId: "project-1",
    projectName: "短视频配音项目",
    status: "active"
  };

  return mount(VoiceStudioPage, {
    global: {
      plugins: [pinia]
    }
  });
}

function createVoiceFetch() {
  return createRouteAwareFetch((path, method) => {
    if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
      return okJsonResponse(scriptDocument());
    }
    if (path === "/api/voice/profiles") return okJsonResponse([voiceProfile()]);
    if (path === "/api/voice/projects/project-1/tracks") return okJsonResponse([voiceTrack()]);
    if (path === "/api/voice/projects/project-1/tracks/generate") {
      return okJsonResponse({
        track: voiceTrack("voice-2"),
        task: null,
        message: "尚未配置可用 TTS Provider，已保存配音版本草稿。"
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

function voiceProfile() {
  return {
    id: "alloy-zh",
    provider: "pending_provider",
    voiceId: "alloy",
    displayName: "清晰叙述",
    locale: "zh-CN",
    tags: ["清晰", "旁白"],
    enabled: true
  };
}

function voiceTrack(id = "voice-1") {
  return {
    id,
    projectId: "project-1",
    timelineId: null,
    source: "tts",
    provider: "pending_provider",
    voiceName: "清晰叙述",
    filePath: null,
    segments: [
      {
        segmentIndex: 0,
        text: "第一段脚本",
        startMs: null,
        endMs: null,
        audioAssetId: null
      }
    ],
    status: "blocked",
    createdAt: now()
  };
}
