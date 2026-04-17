import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RuntimeRequestError,
  createWorkspaceTimeline,
  fetchWorkspaceTimeline,
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

    expect(emptyResult.timeline).toBeNull();
    expect(createdResult.timeline?.id).toBe("timeline-1");
    expect(updatedResult.timeline?.name).toBe("短视频成片草稿");
    expect(commandResult.status).toBe("blocked");
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
