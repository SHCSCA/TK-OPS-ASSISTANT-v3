import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useEditingWorkspaceStore } from "@/stores/editing-workspace";

import { createRouteAwareFetch, errorJsonResponse, okJsonResponse } from "./runtime-helpers";

describe("M05 AI 剪辑工作台 store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("加载没有时间线的项目后进入 empty 状态", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ timeline: null }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");

    expect(store.status).toBe("empty");
    expect(store.timeline).toBeNull();
    expect(store.blockedMessage).toBe("当前项目还没有时间线草稿。");
  });

  it("创建时间线草稿后进入 ready 并保存真实时间线", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ timeline: null }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const created = await store.createDraft("project-1");

    expect(store.status).toBe("ready");
    expect(created?.id).toBe("timeline-1");
    expect(store.timeline?.tracks).toEqual([]);
    expect(store.blockedMessage).toBeNull();
  });

  it("保存轨道时保留时间线并回到 ready 状态", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    store.timeline!.tracks = [videoTrack()];

    const saved = await store.saveTimeline();

    expect(saved?.tracks[0].name).toBe("主画面");
    expect(store.status).toBe("ready");
    expect(store.timeline?.tracks[0].kind).toBe("video");
  });

  it("汇入工作台时间线后保存来源状态并选中首条受管轨道", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const timelineResult = await store.assembleTimeline("project-1");

    expect(timelineResult?.tracks[0].id).toBe("managed-video-storyboard");
    expect(store.status).toBe("ready");
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.saveState?.source).toBe("assembly");
    expect(store.assemblyState?.sources.map((source) => source.kind)).toEqual([
      "script",
      "storyboard",
      "voice",
      "subtitle"
    ]);
  });

  it("执行时间线预检后保存真实预检结果", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const precheck = await store.runPrecheck();

    expect(precheck?.status).toBe("ready");
    expect(store.precheck?.issues).toEqual([]);
    expect(store.status).toBe("ready");
  });

  it("AI 魔法剪被阻断时保存 blockedMessage", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const result = await store.runMagicCut("project-1");

    expect(result?.status).toBe("blocked");
    expect(store.status).toBe("blocked");
    expect(store.blockedMessage).toContain("AI 剪辑命令尚未接入 Provider");
  });

  it("Runtime 保存失败时进入 error 并保留既有草稿", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ failSave: true }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    store.timeline!.tracks = [videoTrack()];
    const saved = await store.saveTimeline();

    expect(saved).toBeNull();
    expect(store.status).toBe("error");
    expect(store.timeline?.id).toBe("timeline-1");
    expect(store.error?.message).toBe("时间线保存失败，请稍后重试。");
  });
});

function createWorkspaceFetch(options: { failSave?: boolean; timeline?: ReturnType<typeof timeline> | null } = {}) {
  return createRouteAwareFetch((path, method, init) => {
    if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
      return okJsonResponse({
        timeline: options.timeline === undefined ? timeline() : options.timeline,
        message:
          options.timeline === null
            ? "当前项目还没有时间线草稿。"
            : "已加载时间线草稿。"
      });
    }

    if (path === "/api/workspace/projects/project-1/timeline" && method === "POST") {
      return okJsonResponse({
        timeline: timeline(),
        message: "已创建时间线草稿。"
      }, 201);
    }

    if (path === "/api/workspace/timelines/timeline-1" && method === "PATCH") {
      if (options.failSave) {
        return errorJsonResponse(500, "时间线保存失败，请稍后重试。");
      }
      const body = JSON.parse(String(init?.body));
      return okJsonResponse({
        timeline: timeline("timeline-1", body.tracks),
        message: "已保存时间线草稿。"
      });
    }

    if (path === "/api/workspace/projects/project-1/timeline/assemble" && method === "POST") {
      return okJsonResponse({
        timeline: timeline("timeline-1", [managedVideoTrack()]),
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

    if (path === "/api/workspace/projects/project-1/ai-commands" && method === "POST") {
      return okJsonResponse({
        status: "blocked",
        task: null,
        message: "AI 剪辑命令尚未接入 Provider，本阶段仅保存时间线草稿。"
      });
    }

    throw new Error(`Unhandled request: ${method} ${path}`);
  });
}

function now() {
  return "2026-04-17T10:00:00Z";
}

function timeline(id = "timeline-1", tracks: unknown[] = []) {
  return {
    id,
    projectId: "project-1",
    name: "AI 剪辑草稿",
    status: "draft",
    durationSeconds: 12,
    source: "manual",
    tracks,
    createdAt: now(),
    updatedAt: now()
  };
}

function videoTrack() {
  return {
    id: "track-video",
    kind: "video",
    name: "主画面",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips: []
  };
}

function managedVideoTrack() {
  return {
    id: "managed-video-storyboard",
    kind: "video",
    name: "分镜视频轨",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips: [
      {
        id: "managed-video-storyboard-01",
        trackId: "managed-video-storyboard",
        sourceType: "storyboard",
        sourceId: "storyboard:1:S01",
        label: "S01 · 分镜画面",
        startMs: 0,
        durationMs: 5000,
        inPointMs: 0,
        outPointMs: null,
        status: "pending",
        metadata: {
          sourceKind: "storyboard",
          sourceRevision: 1,
          segmentIndex: 0,
          segmentId: "S01",
          text: "测试字幕",
          visualPrompt: "测试画面"
        }
      }
    ]
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
