import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useVoiceStudioStore } from "@/stores/voice-studio";

import { createRouteAwareFetch, errorJsonResponse, okJsonResponse } from "./runtime-helpers";

describe("M07 配音中心 store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("加载脚本、音色和配音版本后进入 ready 状态", async () => {
    vi.stubGlobal("fetch", createVoiceFetch());

    const store = useVoiceStudioStore();
    await store.load("project-1");

    expect(store.status).toBe("ready");
    expect(store.viewState).toBe("blocked");
    expect(store.paragraphs.map((item) => item.text)).toEqual(["第一段脚本", "第二段脚本"]);
    expect(store.profiles[0].displayName).toBe("清晰叙述");
    expect(store.tracks).toHaveLength(1);
    expect(store.selectedProfileId).toBe("alloy-zh");
  });

  it("生成配音版本时保存 blocked 状态和中文说明", async () => {
    vi.stubGlobal("fetch", createVoiceFetch());

    const store = useVoiceStudioStore();
    await store.load("project-1");
    const result = await store.generate();

    expect(result?.track.status).toBe("blocked");
    expect(store.status).toBe("blocked");
    expect(store.viewState).toBe("blocked");
    expect(store.generationResult?.message).toContain("TTS Provider");
    expect(store.tracks[0].id).toBe("voice-2");
    expect(store.selectedTrackId).toBe("voice-2");
  });

  it("空脚本时不请求生成并进入中文错误态", async () => {
    vi.stubGlobal("fetch", createVoiceFetch({ emptyScript: true }));

    const store = useVoiceStudioStore();
    await store.load("project-1");
    const result = await store.generate();

    expect(result).toBeNull();
    expect(store.status).toBe("error");
    expect(store.viewState).toBe("empty");
    expect(store.error?.message).toContain("脚本文本为空");
  });

  it("没有可用音色时进入 disabled 视图态", async () => {
    vi.stubGlobal("fetch", createVoiceFetch({ disabledProfiles: true }));

    const store = useVoiceStudioStore();
    await store.load("project-1");

    expect(store.status).toBe("ready");
    expect(store.viewState).toBe("disabled");
    expect(store.selectedProfileId).toBeNull();
  });

  it("Runtime 失败时保留中文错误态", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
          return okJsonResponse(scriptDocument());
        }
        if (path === "/api/voice/profiles") return okJsonResponse([voiceProfile()]);
        if (path === "/api/voice/projects/project-1/tracks") return okJsonResponse([]);
        if (path === "/api/voice/projects/project-1/tracks/generate") {
          return errorJsonResponse(400, "脚本文本为空，请先在脚本与选题中心创建内容。");
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const store = useVoiceStudioStore();
    await store.load("project-1");
    await store.generate();

    expect(store.status).toBe("error");
    expect(store.viewState).toBe("error");
    expect(store.error?.message).toContain("脚本文本为空");
  });

  it("选择配音版本时拉取版本详情并覆盖本地列表数据", async () => {
    vi.stubGlobal("fetch", createVoiceFetch({ withTrackDetails: true }));

    const store = useVoiceStudioStore();
    await store.load("project-1");
    await store.selectTrack("voice-1");

    expect(store.selectedTrack?.segments).toHaveLength(2);
    expect(store.selectedTrack?.segments[1]?.text).toBe("第二段脚本");
  });

  it("删除配音版本后刷新列表并清空选中态", async () => {
    let tracks = [voiceTrack("voice-1")];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
          return okJsonResponse(scriptDocument());
        }
        if (path === "/api/voice/profiles") return okJsonResponse([voiceProfile()]);
        if (path === "/api/voice/projects/project-1/tracks") return okJsonResponse(tracks);
        if (path === "/api/voice/tracks/voice-1" && method === "DELETE") {
          tracks = [];
          return okJsonResponse(undefined);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const store = useVoiceStudioStore();
    await store.load("project-1");
    await store.deleteTrack("voice-1");

    expect(store.tracks).toEqual([]);
    expect(store.selectedTrackId).toBeNull();
  });
});

function createVoiceFetch(
  options: { disabledProfiles?: boolean; emptyScript?: boolean; withTrackDetails?: boolean } = {}
) {
  return createRouteAwareFetch((path, method) => {
    if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
      return okJsonResponse(scriptDocument(options.emptyScript ? "" : "第一段脚本\n\n第二段脚本"));
    }
    if (path === "/api/voice/profiles") {
      return okJsonResponse([voiceProfile(options.disabledProfiles ? { enabled: false } : undefined)]);
    }
    if (path === "/api/voice/projects/project-1/tracks") return okJsonResponse([voiceTrack()]);
    if (path === "/api/voice/tracks/voice-1" && method === "GET") {
      return okJsonResponse(options.withTrackDetails ? voiceTrackWithDetails("voice-1") : voiceTrack());
    }
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

function scriptDocument(content = "第一段脚本\n\n第二段脚本") {
  return {
    projectId: "project-1",
    currentVersion: {
      revision: 1,
      source: "manual",
      content,
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

function voiceProfile(overrides: Partial<{ enabled: boolean }> = {}) {
  return {
    id: "alloy-zh",
    provider: "pending_provider",
    voiceId: "alloy",
    displayName: "清晰叙述",
    locale: "zh-CN",
    tags: ["清晰", "旁白"],
    enabled: overrides.enabled ?? true
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

function voiceTrackWithDetails(id = "voice-1") {
  return {
    ...voiceTrack(id),
    segments: [
      {
        segmentIndex: 0,
        text: "第一段脚本",
        startMs: null,
        endMs: null,
        audioAssetId: null
      },
      {
        segmentIndex: 1,
        text: "第二段脚本",
        startMs: null,
        endMs: null,
        audioAssetId: null
      }
    ]
  };
}
