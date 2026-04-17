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
