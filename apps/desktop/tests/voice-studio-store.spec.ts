import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useVoiceStudioStore } from "../src/stores/voice-studio";

describe("M07 配音中心 store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
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

  it("加载 Markdown 脚本文档时只提取可配音口播文案", async () => {
    vi.stubGlobal("fetch", createVoiceFetch({ scriptContent: markdownScriptDocument() }));

    const store = useVoiceStudioStore();
    await store.load("project-1");

    expect(store.paragraphs.map((item) => item.text)).toEqual([
      "I thought this was just another plain coffee cup…",
      "You know that feeling? You see the same old cup every morning.",
      "Tap the link in my bio before they sell out."
    ]);
    expect(store.sourceText).not.toContain("TikTok短视频脚本");
    expect(store.sourceText).not.toContain("| 项目 | 内容 |");
    expect(store.sourceText).not.toContain("9:16");
  });

  it("生成配音版本时保留 blocked 状态和中文说明", async () => {
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

  it("生成任务提交后保持生成态并接收 ai-voice 进度事件", async () => {
    vi.stubGlobal("fetch", createVoiceFetch({ generatingTask: true }));

    const store = useVoiceStudioStore();
    await store.load("project-1");
    const result = await store.generate();

    expect(result?.task?.id).toBe("task-voice-1");
    expect(store.status).toBe("generating");
    expect(store.viewState).toBe("loading");
    expect(store.activeTask?.id).toBe("task-voice-1");
    expect(store.activeTask?.task_type).toBe("ai-voice");
    expect(store.activeTask?.message).toContain("配音生成任务已提交");
    expect(store.selectedTrack?.status).toBe("processing");

    store.handleTaskEvent({
      schema_version: 1,
      type: "task.progress",
      taskId: "task-voice-1",
      taskType: "ai-voice",
      projectId: "project-1",
      status: "running",
      progress: 75,
      message: "正在写入配音文件。"
    });

    expect(store.status).toBe("generating");
    expect(store.activeTask?.progress).toBe(75);
    expect(store.activeTask?.message).toBe("正在写入配音文件。");
  });

  it("忽略缺少任务标识的非配音任务事件", async () => {
    vi.stubGlobal("fetch", createVoiceFetch());

    const store = useVoiceStudioStore();
    await store.load("project-1");
    store.handleTaskEvent({
      schema_version: 1,
      type: "task.progress",
      projectId: "project-1",
      status: "running",
      progress: 50,
      message: "其他任务处理中。"
    });

    expect(store.status).toBe("ready");
    expect(store.activeTask).toBeNull();
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
        if (path === "/api/voice/tracks/voice-1" && method === "GET") {
          return okJsonResponse(voiceTrack("voice-1"));
        }
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

function createRouteAwareFetch(
  resolver: (path: string, method: string, init?: RequestInit) => unknown
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const requestUrl = new URL(String(input));
    const path = `${requestUrl.pathname}${requestUrl.search}`;
    const method = (init?.method ?? "GET").toUpperCase();
    return resolver(path, method, init);
  });
}

function okJsonResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => ({
      ok: true,
      data
    })
  };
}

function errorJsonResponse(status: number, error: string, requestId = "req-runtime") {
  return {
    ok: false,
    status,
    json: async () => ({
      ok: false,
      error,
      requestId
    })
  };
}

function createVoiceFetch(
  options: {
    disabledProfiles?: boolean;
    emptyScript?: boolean;
    generatingTask?: boolean;
    scriptContent?: string;
    withTrackDetails?: boolean;
  } = {}
) {
  return createRouteAwareFetch((path, method) => {
    if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
      return okJsonResponse(
        scriptDocument(options.emptyScript ? "" : options.scriptContent ?? "第一段脚本\n\n第二段脚本")
      );
    }
    if (path === "/api/voice/profiles") {
      return okJsonResponse([
        voiceProfile(options.disabledProfiles ? { enabled: false } : undefined)
      ]);
    }
    if (path === "/api/voice/projects/project-1/tracks") return okJsonResponse([voiceTrack()]);
    if (path === "/api/voice/tracks/voice-1" && method === "GET") {
      return okJsonResponse(
        options.withTrackDetails ? voiceTrackWithDetails("voice-1") : voiceTrack()
      );
    }
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

function markdownScriptDocument() {
  return `# TikTok短视频脚本

## 1. 脚本元信息

| 项目 | 内容 |
|---|---|
| 平台 | TikTok |
| 视频比例 | 9:16 |
| 建议时长 | 30秒 |

## 5. 分段脚本

| 段落ID | 时间 | 段落目标 | 口播文案 | 屏幕字幕 | 基础画面建议 |
|---|---|---|---|---|---|
| S01 | 0-3秒 | Hook | I thought this was just another plain coffee cup… | plain coffee cup | Hand holds a boring cup. |
| S02 | 3-7秒 | Pain point | You know that feeling? You see the same old cup every morning. | Same old cup every morning. | Person sighs softly. |
| S03 | 25-30秒 | CTA | Tap the link in my bio before they sell out. | Link in bio. | Cup on spring background. |

## 6. 口播完整稿

\`\`\`text
I thought this was just another plain coffee cup…
\`\`\``;
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

function voiceProfile(overrides: Partial<{ enabled: boolean }> = {}) {
  return {
    id: "alloy-zh",
    provider: "volcengine_tts",
    voiceId: "zh_female_vv_uranus_bigtts",
    displayName: "清晰叙述",
    locale: "zh-CN",
    tags: ["清晰", "旁白"],
    enabled: overrides.enabled ?? true
  };
}

function voiceTrack(id = "voice-1", overrides: Partial<{ status: string }> = {}) {
  return {
    id,
    projectId: "project-1",
    timelineId: null,
    source: "tts",
    provider: "volcengine_tts",
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
    status: overrides.status ?? "blocked",
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
