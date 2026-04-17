import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("M05 AI 剪辑工作台页面", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("通过 /workspace/editing 加载真实时间线空态并创建草稿", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    let timelineState: ReturnType<typeof workspaceTimeline> | null = null;
    const fetchMock = createRouteAwareFetch((path, method, init) => {
      calls.push({
        path,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : undefined
      });

      if (path === "/api/license/status") return okJsonResponse(runtimeFixtures.activeLicense);
      if (path === "/api/settings/health") return okJsonResponse(runtimeFixtures.health);
      if (path === "/api/settings/config") return okJsonResponse(runtimeFixtures.initializedConfig);
      if (path === "/api/settings/diagnostics") {
        return okJsonResponse(runtimeFixtures.initializedDiagnostics);
      }
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
      if (path === "/api/workspace/projects/project-1/timeline" && method === "POST") {
        timelineState = workspaceTimeline();
        return okJsonResponse({
          timeline: timelineState,
          message: "已创建时间线草稿。"
        }, 201);
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

    const { wrapper, router } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/workspace/editing");
    expect(calls.some((call) => call.path === "/api/workspace/projects/project-1/timeline")).toBe(
      true
    );
    expect(wrapper.text()).toContain("当前项目还没有时间线草稿");
    expect(wrapper.text()).not.toContain("BGM_");

    await wrapper.get('[data-testid="workspace-create-draft-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("主画面");
    expect(calls).toContainEqual({
      path: "/api/workspace/projects/project-1/timeline",
      method: "POST",
      body: { name: "主时间线" }
    });

    await wrapper.get('[data-testid="workspace-magic-cut-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("AI 剪辑命令尚未接入 Provider");
  });
});

function now() {
  return "2026-04-17T10:00:00Z";
}

function workspaceTimeline() {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds: 12,
    source: "manual",
    tracks: [
      {
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
            status: "ready"
          }
        ]
      }
    ],
    createdAt: now(),
    updatedAt: now()
  };
}
