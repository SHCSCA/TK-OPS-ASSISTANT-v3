import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RuntimeRequestError,
  createWorkspaceTimeline,
  applyMagicCutSuggestion,
  dismissMagicCutSuggestion,
  fetchLatestMagicCutSuggestion,
  fetchTimelinePreview,
  fetchWorkspaceTimeline,
  insertWorkspaceAssetClip,
  runWorkspaceAICommand,
  updateWorkspaceTimeline
} from "@/app/runtime-client";

import { createRouteAwareFetch, errorJsonResponse, okJsonResponse } from "./runtime-helpers";

describe("M05 AI 剪辑工作台 Runtime client 契约", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("使用稳定 /api/workspace 路径、方法和请求体", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const fetchMock = createRouteAwareFetch((path, method, init) => {
      calls.push({
        path,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : undefined
      });

      if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
        return okJsonResponse({
          timeline: null,
          message: "当前项目还没有时间线草稿。"
        });
      }

      if (path === "/api/workspace/projects/project-1/timeline" && method === "POST") {
        return okJsonResponse({
          timeline: workspaceTimeline("timeline-1"),
          message: "已创建时间线草稿。"
        }, 201);
      }

      if (path === "/api/workspace/timelines/timeline-1" && method === "PATCH") {
        return okJsonResponse({
          timeline: workspaceTimeline("timeline-1", "短视频成片草稿"),
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

      if (path === "/api/workspace/timelines/timeline-1/clips/insert-asset" && method === "POST") {
        return okJsonResponse({
          timeline: workspaceTimeline("timeline-1", "短视频成片草稿"),
          saveState: {
            saved: true,
            updatedAt: now(),
            source: "clip_insert_asset",
            message: "已确认保存资产入轨结果。"
          },
          message: "资产已加入时间线。"
        });
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const emptyResult = await fetchWorkspaceTimeline("project-1");
    const createdResult = await createWorkspaceTimeline("project-1", {
      name: "AI 剪辑草稿"
    });
    const updatedResult = await updateWorkspaceTimeline("timeline-1", {
      name: "短视频成片草稿",
      durationSeconds: 12,
      tracks: [
        {
          id: "track-video",
          kind: "video",
          name: "主画面",
          orderIndex: 0,
          locked: false,
          muted: false,
          clips: []
        }
      ]
    });
    const commandResult = await runWorkspaceAICommand("project-1", {
      timelineId: "timeline-1",
      capabilityId: "magic_cut",
      parameters: {
        instruction: "删除长停顿"
      }
    });
    const insertResult = await insertWorkspaceAssetClip("timeline-1", {
      assetId: "asset-video-1",
      targetTrackId: "track-video",
      startMs: 4200
    });

    expect(emptyResult.timeline).toBeNull();
    expect(createdResult.timeline?.id).toBe("timeline-1");
    expect(updatedResult.timeline?.name).toBe("短视频成片草稿");
    expect(commandResult.status).toBe("blocked");
    expect(insertResult.saveState?.source).toBe("clip_insert_asset");
    expect(calls).toEqual([
      { path: "/api/workspace/projects/project-1/timeline", method: "GET", body: undefined },
      {
        path: "/api/workspace/projects/project-1/timeline",
        method: "POST",
        body: { name: "AI 剪辑草稿" }
      },
      {
        path: "/api/workspace/timelines/timeline-1",
        method: "PATCH",
        body: {
          name: "短视频成片草稿",
          durationSeconds: 12,
          tracks: [
            {
              id: "track-video",
              kind: "video",
              name: "主画面",
              orderIndex: 0,
              locked: false,
              muted: false,
              clips: []
            }
          ]
        }
      },
      {
        path: "/api/workspace/projects/project-1/ai-commands",
        method: "POST",
        body: {
          timelineId: "timeline-1",
          capabilityId: "magic_cut",
          parameters: {
            instruction: "删除长停顿"
          }
        }
      },
      {
        path: "/api/workspace/timelines/timeline-1/clips/insert-asset",
        method: "POST",
        body: {
          assetId: "asset-video-1",
          targetTrackId: "track-video",
          startMs: 4200
        }
      }
    ]);
  });

  it("时间线预览可按选中片段请求对应媒体", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    const fetchMock = createRouteAwareFetch((path, method) => {
      calls.push({
        path,
        method
      });

      if (path === "/api/workspace/timelines/timeline-1/preview?clipId=clip-second-media" && method === "GET") {
        return okJsonResponse({
          timelineId: "timeline-1",
          status: "ready",
          message: "真实媒体预览已准备",
          previewUrl: null,
          previewMode: "manifest",
          media: null,
          error: null
        });
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchTimelinePreview("timeline-1", { clipId: "clip-second-media" });

    expect(calls).toEqual([
      {
        method: "GET",
        path: "/api/workspace/timelines/timeline-1/preview?clipId=clip-second-media"
      }
    ]);
  });

  it("智能粗剪建议接口使用 Runtime adapter 和审阅门禁路径", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const fetchMock = createRouteAwareFetch((path, method, init) => {
      calls.push({
        path,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : undefined
      });

      if (
        path === "/api/workspace/projects/project-1/magic-cut-suggestions/latest?timelineId=timeline-1" &&
        method === "GET"
      ) {
        return okJsonResponse(magicCutSuggestion());
      }

      if (path === "/api/workspace/magic-cut-suggestions/suggestion-1/apply" && method === "POST") {
        return okJsonResponse({
          suggestion: {
            ...magicCutSuggestion(),
            status: "applied",
            appliedAt: now()
          },
          timeline: workspaceTimeline("timeline-1"),
          appliedCount: 1,
          failedCount: 0,
          message: "已应用 1 条智能粗剪建议。"
        });
      }

      if (path === "/api/workspace/magic-cut-suggestions/suggestion-1/dismiss" && method === "POST") {
        return okJsonResponse({
          suggestion: {
            ...magicCutSuggestion(),
            status: "dismissed",
            operations: []
          },
          message: "已忽略本次智能粗剪建议，时间线未修改。"
        });
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const latest = await fetchLatestMagicCutSuggestion("project-1", "timeline-1");
    const applied = await applyMagicCutSuggestion("suggestion-1", {
      operationIds: ["operation-trim-1"],
      confirmTimelineVersionToken: "sha256:timeline-token"
    });
    const dismissed = await dismissMagicCutSuggestion("suggestion-1");

    expect(latest?.id).toBe("suggestion-1");
    expect(applied.appliedCount).toBe(1);
    expect(dismissed.message).toBe("已忽略本次智能粗剪建议，时间线未修改。");
    expect(calls).toEqual([
      {
        path: "/api/workspace/projects/project-1/magic-cut-suggestions/latest?timelineId=timeline-1",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/workspace/magic-cut-suggestions/suggestion-1/apply",
        method: "POST",
        body: {
          operationIds: ["operation-trim-1"],
          confirmTimelineVersionToken: "sha256:timeline-token"
        }
      },
      {
        path: "/api/workspace/magic-cut-suggestions/suggestion-1/dismiss",
        method: "POST",
        body: undefined
      }
    ]);
  });

  it("把 Runtime 错误信封转换为可见中文错误", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch(() =>
        errorJsonResponse(400, "时间线轨道类型不受支持，请刷新后重试。")
      )
    );

    await expect(fetchWorkspaceTimeline("project-1")).rejects.toMatchObject({
      name: "RuntimeRequestError",
      message: "时间线轨道类型不受支持，请刷新后重试。",
      status: 400
    } satisfies Partial<RuntimeRequestError>);
  });
});

function now() {
  return "2026-04-17T10:00:00Z";
}

function workspaceTimeline(id = "timeline-1", name = "AI 剪辑草稿") {
  return {
    id,
    projectId: "project-1",
    name,
    status: "draft",
    durationSeconds: 0,
    source: "manual",
    tracks: [],
    createdAt: now(),
    updatedAt: now()
  };
}

function magicCutSuggestion() {
  return {
    id: "suggestion-1",
    projectId: "project-1",
    timelineId: "timeline-1",
    timelineVersionToken: "sha256:timeline-token",
    status: "pending_review",
    summary: "建议压缩开场停顿。",
    operations: [
      {
        id: "operation-trim-1",
        action: "trim",
        clipId: "clip-video-1",
        trackId: "track-video",
        targetTrackId: null,
        originalStartMs: 0,
        originalDurationMs: 4200,
        suggestedStartMs: 0,
        suggestedDurationMs: 3000,
        splitAtMs: null,
        reason: "开场停顿过长。",
        risk: null
      }
    ],
    createdAt: now(),
    updatedAt: now(),
    appliedAt: null
  };
}
