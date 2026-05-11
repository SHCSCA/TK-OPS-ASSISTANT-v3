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
    expect(wrapper.text()).toContain("配音版本");
    expect(wrapper.text()).toContain("草稿");
    expect(wrapper.text()).toContain("阻断");
    expect(wrapper.text()).toContain("清晰叙述");
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

  it("生成任务提交后在页面展示生成中状态和进度", async () => {
    vi.stubGlobal("fetch", createVoiceFetch({ generatingTask: true }));

    const wrapper = mountVoiceStudioWithProject();
    await flushPromises();

    await wrapper.get('[data-testid="voice-generate-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("正在生成音轨");
    expect(wrapper.text()).toContain("配音生成任务已提交。");
    expect(wrapper.text()).toContain("0%");
    expect(wrapper.text()).toContain("生成中");
    expect(wrapper.get('[data-testid="voice-preview-stage"]').text()).toContain("配音导演台");
    expect(window.alert).not.toHaveBeenCalled();
  });

  it("音轨就绪时播放器使用 Runtime 音频流地址", async () => {
    vi.stubGlobal("fetch", createVoiceFetch({ readyAudio: true }));

    const wrapper = mountVoiceStudioWithProject();
    await flushPromises();

    const audio = wrapper.get("audio");
    expect(audio.attributes("src")).toBe(
      "http://127.0.0.1:8000/api/voice/tracks/voice-1/audio?v=2026-04-16T10%3A00%3A00Z"
    );
    expect(audio.attributes("src")).not.toContain("G:/runtime/voice/voice-1.mp3");
  });

  it("音轨就绪时支持整段和当前段落预览", async () => {
    vi.stubGlobal("fetch", createVoiceFetch({ readyAudio: true }));

    const wrapper = mountVoiceStudioWithProject();
    await flushPromises();

    const audio = wrapper.get("audio");
    Object.defineProperty(audio.element, "duration", {
      configurable: true,
      value: 22
    });
    await audio.trigger("loadedmetadata");

    expect(wrapper.text()).toContain("整段预览");
    expect(wrapper.text()).toContain("00:00 - 00:22");

    await wrapper.get('[data-testid="voice-preview-mode-segment"]').trigger("click");
    expect(wrapper.text()).toContain("当前段落预览");
    expect(wrapper.text()).toContain("第 1 段");
    audio.element.currentTime = 21;
    await audio.trigger("play");
    expect(audio.element.currentTime).toBe(0);

    await wrapper.findAll(".paragraph-item")[1].trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("第 2 段");
    expect(audio.element.currentTime).toBeGreaterThan(0);
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

function createVoiceFetch(options: { generatingTask?: boolean; readyAudio?: boolean } = {}) {
  return createRouteAwareFetch((path, method) => {
    const initialTrack = options.readyAudio
      ? voiceTrack("voice-1", { filePath: "G:/runtime/voice/voice-1.mp3", status: "ready" })
      : voiceTrack();
    if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
      return okJsonResponse(scriptDocument());
    }
    if (path === "/api/voice/profiles") return okJsonResponse([voiceProfile()]);
    if (path === "/api/voice/projects/project-1/tracks") return okJsonResponse([initialTrack]);
    if (path === "/api/voice/tracks/voice-1" && method === "GET") return okJsonResponse(initialTrack);
    if (path === "/api/voice/projects/project-1/tracks/generate") {
      if (options.generatingTask) {
        return okJsonResponse({
          track: voiceTrack("voice-2", { status: "processing" }),
          task: taskInfo("task-voice-1", {
            message: "配音生成任务已提交。",
            status: "queued",
            task_type: "ai-voice"
          }),
          message: "配音生成任务已提交。"
        });
      }
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

function taskInfo(
  id = "task-voice-1",
  overrides: Partial<{
    message: string;
    progress: number;
    status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
    task_type: string;
  }> = {}
) {
  return {
    id,
    task_type: overrides.task_type ?? "ai-voice",
    project_id: "project-1",
    projectId: "project-1",
    status: overrides.status ?? "queued",
    progress: overrides.progress ?? 0,
    message: overrides.message ?? "任务已排队",
    created_at: now(),
    updated_at: now(),
    kind: overrides.task_type ?? "ai-voice",
    ownerRef: { kind: "voice-track", id: "voice-2" },
    label: "配音生成：清晰叙述"
  };
}

function voiceProfile() {
  return {
    id: "alloy-zh",
    provider: "volcengine_tts",
    voiceId: "zh_female_vv_uranus_bigtts",
    displayName: "清晰叙述",
    locale: "zh-CN",
    tags: ["清晰", "旁白"],
    enabled: true
  };
}

function voiceTrack(
  id = "voice-1",
  overrides: Partial<{ filePath: string | null; status: string }> = {}
) {
  return {
    id,
    projectId: "project-1",
    timelineId: null,
    source: "tts",
    provider: "volcengine_tts",
    voiceName: "清晰叙述",
    filePath: overrides.filePath ?? null,
    segments: [
      {
        segmentIndex: 0,
        text: "第一段脚本！",
        startMs: null,
        endMs: null,
        audioAssetId: null
      }
    ],
    status: overrides.status ?? "blocked",
    createdAt: now(),
    updatedAt: now()
  };
}
