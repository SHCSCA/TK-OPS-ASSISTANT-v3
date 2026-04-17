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

  it("加载脚本、音色和版本后显示阻断草稿语义", async () => {
    vi.stubGlobal("fetch", createVoiceFetch());

    const wrapper = mountVoiceStudioWithProject();
    await flushPromises();

    expect(wrapper.text()).toContain("M07 配音中心");
    expect(wrapper.text()).toContain("已保存阻断草稿，但没有生成真实音频。");
    expect(wrapper.text()).toContain("版本：阻断草稿");
    expect(wrapper.text()).toContain("阻断");
    expect(wrapper.text()).toContain("娓呮櫚鍙欒堪");
    expect(wrapper.text()).not.toMatch(/假音频/);
  });

  it("生成后继续保留 blocked 草稿语义，并且不弹出 alert", async () => {
    vi.stubGlobal("fetch", createVoiceFetch());

    const wrapper = mountVoiceStudioWithProject();
    await flushPromises();

    await wrapper.get('[data-testid="voice-generate-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("没有可用 TTS Provider");
    expect(wrapper.text()).toContain("重新保存阻断草稿");
    expect(wrapper.text()).toContain("真实音频");
    expect(window.alert).not.toHaveBeenCalled();
  });

  it("没有当前项目时禁用生成入口并保留阻断导语", async () => {
    vi.stubGlobal("fetch", createVoiceFetch());

    const wrapper = mount(VoiceStudioPage, {
      global: {
        plugins: [createPinia()]
      }
    });
    await flushPromises();

    expect(wrapper.text()).toContain("生成入口已锁定");
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
      content: "绗竴娈佃剼鏈紒\n绗簩娈佃剼鏈紒",
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
    displayName: "娓呮櫚鍙欒堪",
    locale: "zh-CN",
    tags: ["娓呮櫚", "鏃佺櫧"],
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
    voiceName: "娓呮櫚鍙欒堪",
    filePath: null,
    segments: [
      {
        segmentIndex: 0,
        text: "绗竴娈佃剼鏈紒",
        startMs: null,
        endMs: null,
        audioAssetId: null
      }
    ],
    status: "blocked",
    createdAt: now()
  };
}
