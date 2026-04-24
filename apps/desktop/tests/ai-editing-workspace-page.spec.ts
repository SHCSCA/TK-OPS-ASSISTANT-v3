import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import App from "../src/App.vue";
import { createAppRouter } from "../src/app/router";
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
    expect(calls.some((call) => call.path === "/api/workspace/projects/project-1/timeline")).toBe(
      true
    );
    expect(wrapper.text()).toContain("核心创作中枢");
    expect(wrapper.text()).toContain("片段来源");
    expect(wrapper.text()).toContain("预览区");
    expect(wrapper.text()).toContain("AI 工具栏");
    expect(wrapper.text()).toContain("当前项目还没有时间线草稿");
    expect(wrapper.text()).not.toContain("BGM_");

    await wrapper.get('[data-testid="workspace-create-draft-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("主画面");
    expect(wrapper.text()).toContain("AI 工具栏");
    expect(wrapper.text()).toContain("运行能力待接入");
    expect(wrapper.text()).toContain("检查器");
    expect(calls).toContainEqual({
      path: "/api/workspace/projects/project-1/timeline",
      method: "POST",
      body: { name: "主时间线" }
    });

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
