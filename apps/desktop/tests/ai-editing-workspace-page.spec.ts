import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import App from "../src/App.vue";
import { createAppRouter } from "../src/app/router";
import WorkspaceTimeline from "../src/modules/workspace/WorkspaceTimeline.vue";
import { useTaskBusStore } from "../src/stores/task-bus";

describe("M05 AI 剪辑工作台页面", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("通过 /workspace/editing 加载真实时间线空态并创建草稿", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    let timelineState: ReturnType<typeof workspaceTimeline> | null = null;

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });

        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            message: "当前项目还没有时间线草稿。"
          });
        }
        if (path === "/api/assets" && method === "GET") {
          return okJsonResponse([workspaceAsset()]);
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "POST") {
          timelineState = workspaceTimeline();
          return okJsonResponse(
            {
              timeline: timelineState,
              message: "已创建时间线草稿。"
            },
            201
          );
        }
        if (path === "/api/workspace/projects/project-1/timeline/assemble" && method === "POST") {
          timelineState = workspaceTimeline([managedVideoTrack(), managedAudioTrack(), managedSubtitleTrack()]);
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "assembly",
              message: "已保存 M05 剪辑工作台受管轨道。"
            },
            assemblyState: {
              status: "ready",
              sources: [
                sourceState("script"),
                sourceState("storyboard"),
                sourceState("voice"),
                sourceState("subtitle")
              ],
              issues: []
            },
            message: "剪辑工作台时间线已从脚本、分镜、配音和字幕汇入。"
          });
        }
        if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
          return okJsonResponse({
            timelineId: "timeline-1",
            status: "ready",
            message: "时间线本地预检通过。",
            issues: []
          });
        }
        if (path === "/api/workspace/clips/managed-video-storyboard-01/move" && method === "POST") {
          expect(JSON.parse(String(init?.body))).toEqual({
            targetTrackId: "managed-video-storyboard",
            startMs: 500
          });
          timelineState = workspaceTimeline([
            managedVideoTrack([managedClip(
              "managed-video-storyboard-01",
              "managed-video-storyboard",
              "storyboard",
              "S01 · 分镜画面",
              { startMs: 500 }
            )]),
            managedAudioTrack(),
            managedSubtitleTrack()
          ]);
          return okJsonResponse({
            timeline: timelineState,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "clip_move",
              message: "已确认保存片段位置变更。"
            },
            message: "片段已移动。"
          });
        }
        if (path === "/api/workspace/clips/managed-video-storyboard-01/trim" && method === "POST") {
          expect(JSON.parse(String(init?.body))).toEqual({
            startMs: 1000,
            durationMs: 4500,
            inPointMs: 500
          });
          timelineState = workspaceTimeline([
            managedVideoTrack([managedClip(
              "managed-video-storyboard-01",
              "managed-video-storyboard",
              "storyboard",
              "S01 · 分镜画面",
              { startMs: 1000, durationMs: 4500, inPointMs: 500 }
            )]),
            managedAudioTrack(),
            managedSubtitleTrack()
          ]);
          return okJsonResponse({
            timeline: timelineState,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "clip_trim",
              message: "已确认保存片段裁剪结果。"
            },
            message: "片段已裁剪。"
          });
        }
        if (path === "/api/workspace/projects/project-1/ai-commands" && method === "POST") {
          return okJsonResponse({
            status: "blocked",
            task: null,
            message: "AI 剪辑命令尚未接入 Provider，本阶段仅保留时间线草稿。"
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, router, pinia } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/workspace/editing");
    expect(wrapper.find(".editing-workspace-page").exists()).toBe(true);
    expect(wrapper.find(".page-container").exists()).toBe(false);
    expect(calls.some((call) => call.path === "/api/workspace/projects/project-1/timeline")).toBe(
      true
    );
    expect(wrapper.text()).toContain("素材池");
    expect(wrapper.text()).toContain("播放器");
    expect(wrapper.text()).toContain("基础属性");
    expect(wrapper.text()).toContain("时间线");
    expect(wrapper.text()).toContain("当前项目还没有时间线草稿");
    expect(wrapper.text()).not.toContain("BGM_");

    await wrapper.get('[data-testid="workspace-create-draft-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("主画面");
    expect(wrapper.text()).toContain("基础工具");
    expect(wrapper.text()).toContain("基础属性");
    expect(wrapper.text()).toContain("片段信息");
    expect(wrapper.text()).toContain("时间参数");
    expect(wrapper.text()).toContain("素材来源");
    expect(wrapper.text()).toContain("AI 粗剪建议");
    expect(wrapper.text()).toContain("默认折叠");
    const aiSuggestionDetails = wrapper.get('[data-testid="workspace-ai-suggestion-details"]');
    expect((aiSuggestionDetails.element as HTMLDetailsElement).open).toBe(false);
    const timelineToolbar = wrapper.get('[data-testid="workspace-timeline-toolbar"]');
    expect(timelineToolbar.text()).toContain("选择");
    expect(timelineToolbar.text()).toContain("左移");
    expect(timelineToolbar.text()).toContain("右移");
    expect(timelineToolbar.text()).toContain("左裁");
    expect(timelineToolbar.text()).toContain("右裁");
    expect(timelineToolbar.text()).toContain("分割");
    expect(timelineToolbar.text()).toContain("删除");
    expect(timelineToolbar.text()).toContain("磁吸");
    expect(wrapper.get('[data-testid="workspace-tool-split"]').text()).toContain("分割");
    expect(wrapper.get('[data-testid="workspace-tool-select"]').classes()).toContain(
      "workspace-timeline-toolbar__button--active"
    );
    await wrapper.get(".workspace-clip").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("该片段来自资产中心素材，可在后续功能中替换或重新定位。");
    expect(calls).toContainEqual({
      path: "/api/workspace/projects/project-1/timeline",
      method: "POST",
      body: { name: "主时间线" }
    });

    await wrapper.get('[data-testid="workspace-assemble-button"]').trigger("click");
    await flushPromises();

    const previewPhone = wrapper.get('[data-testid="workspace-preview-phone"]');
    expect(previewPhone.attributes("data-ratio")).toBe("9:16");
    expect(previewPhone.text()).toContain("9:16");
    expect(wrapper.get('[data-testid="workspace-preview-transport"]').text()).toContain("00:");
    expect(wrapper.text()).toContain("分镜占位");
    expect(wrapper.text()).toContain("待处理");
    expect(wrapper.text()).not.toContain("pending");
    expect(wrapper.text()).not.toContain("draft");
    expect(wrapper.text()).not.toContain("延续字幕");
    expect(wrapper.text()).toContain("分镜视频轨");
    expect(wrapper.text()).toContain("配音轨");
    expect(wrapper.text()).toContain("字幕轨");
    expect(wrapper.text()).toContain("资产");
    expect(wrapper.text()).toContain("warm-room-lamp-vertical.mp4");
    expect(wrapper.text()).toContain("加入轨道");
    expect(wrapper.text()).toContain("受管轨道");
    expect(wrapper.text()).toContain("本地预检");
    expect(calls).toContainEqual({
      path: "/api/workspace/projects/project-1/timeline/assemble",
      method: "POST",
      body: { mode: "merge_managed", timelineName: "主时间线" }
    });

    await wrapper.get('[data-testid="workspace-precheck-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("时间线本地预检通过");

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("move-commit", {
      gesture: "move",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      startMs: 500,
      durationMs: 5000
    });
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/workspace/clips/managed-video-storyboard-01/move",
      method: "POST",
      body: { targetTrackId: "managed-video-storyboard", startMs: 500 }
    });
    expect(wrapper.text()).toContain("已确认保存片段位置变更");

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("trim-commit", {
      gesture: "trim",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      edge: "left",
      startMs: 1000,
      durationMs: 4500,
      inPointMs: 500
    });
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/workspace/clips/managed-video-storyboard-01/trim",
      method: "POST",
      body: { startMs: 1000, durationMs: 4500, inPointMs: 500 }
    });
    expect(wrapper.text()).toContain("已确认保存片段裁剪结果");

    const taskBusStore = useTaskBusStore(pinia);
    taskBusStore.handleIncomingMessage(JSON.stringify({
      schema_version: 1,
      type: "task.started",
      taskId: "task-workspace-1",
      taskType: "ai-workspace-command",
      projectId: "project-1",
      status: "running",
      progress: 25,
      message: "AI 命令 magic_cut 已进入任务队列。"
    }));
    await flushPromises();

    expect(wrapper.text()).toContain("AI 命令 magic_cut 已进入任务队列");
    expect(
      (wrapper.get('[data-testid="workspace-magic-cut-button"]').element as HTMLButtonElement)
        .disabled
    ).toBe(true);

    taskBusStore.handleIncomingMessage(JSON.stringify({
      schema_version: 1,
      type: "task.completed",
      taskId: "task-workspace-1",
      taskType: "ai-workspace-command",
      projectId: "project-1",
      status: "succeeded",
      progress: 100,
      message: "AI 命令 magic_cut 已完成。"
    }));
    await flushPromises();

    await wrapper.get('[data-testid="workspace-magic-cut-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("AI 剪辑命令尚未接入 Provider");
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

async function mountApp(path: string) {
  const pinia = createPinia();
  const router = createAppRouter(pinia, createMemoryHistory());
  router.push(path);
  await router.isReady();

  const wrapper = mount(App, {
    global: {
      plugins: [pinia, router]
    }
  });

  return { wrapper, router, pinia };
}

function activeLicense() {
  return {
    active: true,
    restrictedMode: false,
    machineCode: "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5",
    machineBound: true,
    licenseType: "perpetual",
    maskedCode: "TK-O****************0001",
    activatedAt: "2026-04-11T10:00:00Z"
  };
}

function health() {
  return {
    service: "online",
    version: "0.1.1",
    now: "2026-04-11T10:00:00Z",
    mode: "development"
  };
}

function providerHealth() {
  return {
    providers: [
      {
        provider: "openai",
        label: "OpenAI",
        readiness: "ready",
        lastCheckedAt: "2026-04-11T10:00:00Z",
        latencyMs: null,
        errorCode: null,
        errorMessage: null
      }
    ],
    refreshedAt: "2026-04-11T10:00:00Z"
  };
}

function initializedConfig() {
  return {
    revision: 2,
    runtime: {
      mode: "development",
      workspaceRoot: "G:/AI/TK-OPS-ASSISTANT-V3"
    },
    paths: {
      cacheDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/cache",
      exportDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/exports",
      logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs"
    },
    logging: {
      level: "INFO"
    },
    ai: {
      provider: "openai",
      model: "gpt-5.4",
      voice: "alloy",
      subtitleMode: "balanced"
    }
  };
}

function initializedDiagnostics() {
  return {
    databasePath: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/runtime.db",
    logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs",
    revision: 2,
    mode: "development",
    healthStatus: "online"
  };
}

function now() {
  return "2026-04-17T10:00:00Z";
}

function workspaceTimeline(tracks = [manualVideoTrack()]) {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds: 12,
    source: "manual",
    tracks,
    createdAt: now(),
    updatedAt: now()
  };
}

function workspaceAsset() {
  return {
    id: "asset-warm-room-lamp",
    name: "warm-room-lamp-vertical.mp4",
    type: "video",
    source: "asset",
    filePath: "G:/assets/warm-room-lamp-vertical.mp4",
    fileSizeBytes: 2048000,
    durationMs: 7200,
    thumbnailPath: null,
    tags: null,
    projectId: "project-1",
    metadataJson: null,
    sourceInfo: {
      source: "import",
      projectId: "project-1",
      groupId: null,
      filePath: "G:/assets/warm-room-lamp-vertical.mp4",
      metadataSummary: {}
    },
    availability: {
      status: "available",
      errorCode: null,
      errorMessage: null,
      nextAction: null
    },
    referenceSummary: {
      total: 0,
      referenceTypes: [],
      blockingDelete: false
    },
    thumbnailStatus: {
      status: "missing",
      path: null,
      generatedAt: null
    },
    createdAt: now(),
    updatedAt: now()
  };
}

function manualVideoTrack() {
  return {
    id: "track-video",
    kind: "video",
    name: "主画面",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips: [
      {
        id: "clip-video",
        trackId: "track-video",
        sourceType: "manual",
        sourceId: null,
        label: "开场镜头",
        startMs: 0,
        durationMs: 4200,
        inPointMs: 0,
        outPointMs: null,
        status: "ready",
        metadata: {
          sourceKind: "asset",
          sourceRevision: null,
          segmentIndex: null,
          segmentId: null,
          text: null,
          visualPrompt: null
        }
      }
    ]
  };
}

function managedVideoTrack(clips = [
  managedClip("managed-video-storyboard-01", "managed-video-storyboard", "storyboard", "S01 · 分镜画面")
]) {
  return {
    id: "managed-video-storyboard",
    kind: "video",
    name: "分镜视频轨",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips
  };
}

function managedAudioTrack() {
  return {
    id: "managed-audio-voice",
    kind: "audio",
    name: "配音轨",
    orderIndex: 1,
    locked: false,
    muted: false,
    clips: [
      managedClip("managed-audio-voice-01", "managed-audio-voice", "voice_track", "S01 · 配音")
    ]
  };
}

function managedSubtitleTrack() {
  return {
    id: "managed-subtitle-track",
    kind: "subtitle",
    name: "字幕轨",
    orderIndex: 2,
    locked: false,
    muted: false,
    clips: [
      managedClip("managed-subtitle-01", "managed-subtitle-track", "subtitle_track", "S01 · 字幕")
    ]
  };
}

function managedClip(
  id: string,
  trackId: string,
  sourceType: string,
  label: string,
  overrides: Partial<{
    startMs: number;
    durationMs: number;
    inPointMs: number;
    outPointMs: number | null;
    status: string;
  }> = {}
) {
  const text = sourceType === "subtitle_track" ? "（延续字幕）" : "This lamp made me cancel my dinner plan.";

  return {
    id,
    trackId,
    sourceType,
    sourceId: `${sourceType}-1`,
    label,
    startMs: 0,
    durationMs: 5000,
    inPointMs: 0,
    outPointMs: null,
    status: sourceType === "storyboard" ? "pending" : "ready",
    metadata: {
      sourceKind: sourceType === "storyboard" ? "storyboard" : sourceType,
      sourceRevision: 1,
      segmentIndex: 0,
      segmentId: "S01",
      text,
      visualPrompt: "墙灯亮起，房间从冷光转暖光。"
    },
    ...overrides
  };
}

function sourceState(kind: string) {
  return {
    kind,
    status: "ready",
    label: kind,
    revision: kind === "script" || kind === "storyboard" ? 1 : null,
    trackId: kind === "voice" || kind === "subtitle" ? `${kind}-track` : null,
    segmentCount: 1,
    message: "已读取。"
  };
}
